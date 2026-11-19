from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import math
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import Shift, BreakEvent, LocationSample, WeatherObservation, ExposureInterval, utc_now
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy
from backend.app.providers.weather.service import weather_service
from backend.app.core.datetime_utils import ensure_utc

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

class ExposureCalculationEngine:
    # CLIM-04: Strict spatial and temporal validation thresholds
    MAX_MATCH_DISTANCE_KM = 25.0  # Max allowable distance from weather station / grid point
    MAX_TEMPORAL_OFFSET_MINUTES = 60 # Max allowable observation time offset

    @staticmethod
    async def compute_shift_exposure(
        db: Session,
        shift_id: str,
        worker_id: str,
    ) -> List[ExposureInterval]:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        
        end_time = ensure_utc(shift.ended_at) if shift.ended_at else utc_now()
        start_time = ensure_utc(shift.started_at)
        
        # 1. Fetch location samples for this shift
        locations = (
            db.query(LocationSample)
            .filter(LocationSample.shift_id == shift_id)
            .order_by(LocationSample.recorded_at.asc())
            .all()
        )

        # 2. Fetch declared breaks for this shift (CLIM-05: separate working exposure from rest periods)
        breaks = (
            db.query(BreakEvent)
            .filter(BreakEvent.shift_id == shift_id)
            .all()
        )

        # Reference coordinates for querying regional weather cache
        if locations:
            ref_lat = locations[0].latitude
            ref_lon = locations[0].longitude
        else:
            # When worker explicitly declined GPS or has no GPS, regional queries use Hyderabad regional coordinates
            # but exposure records will NOT fabricate fine location evidence.
            ref_lat = 17.3850
            ref_lon = 78.4867

        observations = await weather_service.get_observations_for_range(
            ref_lat, ref_lon, start_time, end_time, db=db
        )

        if not observations:
            return []

        # Clear existing exposure intervals for idempotent re-runs
        db.query(ExposureInterval).filter(ExposureInterval.shift_id == shift_id).delete()

        intervals: List[ExposureInterval] = []
        current = start_time

        while current < end_time:
            interval_end = min(current + timedelta(hours=1), end_time)
            interval_duration_mins = (interval_end - current).total_seconds() / 60.0

            # CLIM-05: Calculate overlap with declared breaks in this specific interval
            break_mins_in_interval = 0.0
            for b in breaks:
                b_start = ensure_utc(b.started_at)
                b_end = ensure_utc(b.ended_at) if b.ended_at else interval_end
                overlap_start = max(current, b_start)
                overlap_end = min(interval_end, b_end)
                if overlap_end > overlap_start:
                    break_mins_in_interval += (overlap_end - overlap_start).total_seconds() / 60.0

            break_mins_in_interval = min(interval_duration_mins, break_mins_in_interval)
            active_work_mins = max(0.0, interval_duration_mins - break_mins_in_interval)

            # CLIM-03: Time-specific location matching for this interval
            interval_locs = [
                l for l in locations
                if current - timedelta(minutes=15) <= ensure_utc(l.recorded_at) <= interval_end + timedelta(minutes=15)
            ]

            has_precise_gps = len(interval_locs) > 0
            if has_precise_gps:
                interval_lat = sum(l.latitude for l in interval_locs) / len(interval_locs)
                interval_lon = sum(l.longitude for l in interval_locs) / len(interval_locs)
            else:
                interval_lat = None
                interval_lon = None

            # Find closest observation in time
            best_obs = None
            best_diff = 1e9
            for obs in observations:
                obs_utc = ensure_utc(obs.observed_at)
                diff = abs((obs_utc - current).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_obs = obs

            if best_obs:
                offset_mins = int(best_diff / 60)

                # CLIM-04: Strict validation thresholds
                if offset_mins > ExposureCalculationEngine.MAX_TEMPORAL_OFFSET_MINUTES:
                    # Observation is too stale; do not generate valid-looking exposure interval
                    current = interval_end
                    continue

                dist_km = None
                if has_precise_gps and interval_lat is not None and interval_lon is not None:
                    dist_km = haversine_distance_km(interval_lat, interval_lon, best_obs.latitude, best_obs.longitude)
                    if dist_km > ExposureCalculationEngine.MAX_MATCH_DISTANCE_KM:
                        # Exceeds spatial threshold; reject for fine exposure interval
                        quality = "REJECTED_DISTANCE_EXCEEDED"
                    elif dist_km <= 15.0 and offset_mins <= 30:
                        quality = "HIGH"
                    else:
                        quality = "MEDIUM"
                else:
                    # GPS was not recorded for this interval (opt-out or indoor); preserve honest unlocated state
                    quality = "ESTIMATED_COARSE_NO_GPS"

                hi_c, risk_cat = calculate_heat_index(best_obs.temperature_celsius, best_obs.relative_humidity_pct)
                wbgt_c = calculate_simplified_wbgt_proxy(
                    best_obs.temperature_celsius,
                    best_obs.relative_humidity_pct,
                    best_obs.wind_speed_mps,
                )

                # Find source observation ID in DB if persisted
                source_db_record = (
                    db.query(WeatherObservation)
                    .filter(
                        WeatherObservation.provider_name == best_obs.provider_name,
                        WeatherObservation.source_identifier == best_obs.source_identifier,
                        WeatherObservation.observed_at == best_obs.observed_at,
                    )
                    .first()
                )

                # If interval was predominantly a rest break, label risk accordingly
                is_break_interval = break_mins_in_interval > (interval_duration_mins * 0.5)

                exp = ExposureInterval(
                    shift_id=shift_id,
                    worker_id=worker_id,
                    start_time=current,
                    end_time=interval_end,
                    mean_temperature_celsius=best_obs.temperature_celsius,
                    mean_relative_humidity_pct=best_obs.relative_humidity_pct,
                    heat_index_celsius=hi_c,
                    risk_category=risk_cat,
                    wbgt_proxy_celsius=wbgt_c,
                    source_observation_id=source_db_record.id if source_db_record else None,
                    distance_to_source_km=dist_km,
                    temporal_offset_minutes=offset_mins,
                    quality_grade="REST_PERIOD" if is_break_interval else quality,
                )
                db.add(exp)
                intervals.append(exp)

            current = interval_end

        db.commit()
        for i in intervals:
            db.refresh(i)
        return intervals

    @staticmethod
    def get_shift_exposure_intervals(db: Session, shift_id: str, worker_id: str) -> List[ExposureInterval]:
        return (
            db.query(ExposureInterval)
            .filter(ExposureInterval.shift_id == shift_id, ExposureInterval.worker_id == worker_id)
            .order_by(ExposureInterval.start_time.asc())
            .all()
        )
