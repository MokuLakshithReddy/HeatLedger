from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
import math
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import Shift, LocationSample, WeatherObservation, ExposureInterval, utc_now
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy
from backend.app.providers.weather.service import weather_service

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
    MAX_MATCH_DISTANCE_KM = 35.0 # Max allowable distance to weather observation
    MAX_TEMPORAL_OFFSET_MINUTES = 90 # Max allowable time difference

    @staticmethod
    async def compute_shift_exposure(
        db: Session,
        shift_id: str,
        worker_id: str,
    ) -> List[ExposureInterval]:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        
        end_time = shift.ended_at or utc_now()
        start_time = shift.started_at
        
        # Check if locations are available
        locations = (
            db.query(LocationSample)
            .filter(LocationSample.shift_id == shift_id)
            .order_by(LocationSample.recorded_at.asc())
            .all()
        )
        
        # Get baseline coordinates (either average of samples, or Hyderabad center)
        if locations:
            center_lat = sum(l.latitude for l in locations) / len(locations)
            center_lon = sum(l.longitude for l in locations) / len(locations)
            has_fine_gps = True
        else:
            center_lat = 17.3850 # Hyderabad center
            center_lon = 78.4867
            has_fine_gps = False

        # Retrieve observations across shift window
        observations = await weather_service.get_observations_for_range(
            center_lat, center_lon, start_time, end_time, db=db
        )

        if not observations:
            return []

        # Clear existing exposure intervals for idempotent re-runs
        db.query(ExposureInterval).filter(ExposureInterval.shift_id == shift_id).delete()

        intervals = []
        # Create hourly intervals
        current = start_time
        while current < end_time:
            interval_end = min(current + timedelta(hours=1), end_time)
            
            # Find closest observation in time
            best_obs = None
            best_diff = 1e9
            for obs in observations:
                diff = abs((obs.observed_at - current).total_seconds())
                if diff < best_diff:
                    best_diff = diff
                    best_obs = obs

            if best_obs:
                offset_mins = int(best_diff / 60)
                dist_km = haversine_distance_km(center_lat, center_lon, best_obs.latitude, best_obs.longitude)
                
                # Determine quality grade based on spatio-temporal precision
                if has_fine_gps and dist_km <= 15.0 and offset_mins <= 30:
                    quality = "HIGH"
                elif dist_km <= 35.0 and offset_mins <= 90:
                    quality = "MEDIUM"
                else:
                    quality = "ESTIMATED"

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
                    quality_grade=quality,
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
