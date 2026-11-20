from datetime import datetime, timezone
import math
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.entities import WeatherObservation, utc_now
from backend.app.providers.weather.base import BaseWeatherProvider, WeatherObservationDTO
from backend.app.providers.weather.imd import IMDWeatherProvider
from backend.app.providers.weather.era5 import ERA5LandProvider
from backend.app.providers.weather.fixtures import HyderabadDemoProvider

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

class WeatherProviderService:
    def __init__(self):
        self.imd_provider = IMDWeatherProvider()
        self.era5_provider = ERA5LandProvider()
        self.demo_provider = HyderabadDemoProvider()

    async def get_current_observation(
        self, latitude: float, longitude: float, db: Optional[Session] = None
    ) -> WeatherObservationDTO:
        # 1. Try official IMD API if configured
        if settings.IMD_API_KEY:
            try:
                obs = await self.imd_provider.get_current_observation(latitude, longitude)
                if obs:
                    if db:
                        self._persist_observation(db, obs)
                    return obs
            except Exception as e:
                logger.warning(f"IMD fetch failed, proceeding to fallback: {e}")

        # 2. In production or when DEMO_MODE is disabled, do not substitute synthetic observations
        if settings.ENVIRONMENT == "production" or not settings.DEMO_MODE:
            logger.warning("Live meteorological observations unavailable from official provider in production; refusing synthetic demo fallback.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Official meteorological observations currently unavailable for this coordinate. Synthetic data fallback is disabled in production.",
            )

        # 3. Development / Demo environment: return clearly labeled Hyderabad demonstration fixture
        demo_obs = await self.demo_provider.get_current_observation(latitude, longitude)
        if db:
            self._persist_observation(db, demo_obs)
        return demo_obs

    async def get_observations_for_range(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        db: Optional[Session] = None,
    ) -> List[WeatherObservationDTO]:
        # Check if we already have observations in DB within 25km radius
        if db:
            is_prod = settings.ENVIRONMENT == "production" or not settings.DEMO_MODE
            query = (
                db.query(WeatherObservation)
                .filter(
                    WeatherObservation.observed_at >= start_time,
                    WeatherObservation.observed_at <= end_time,
                )
                .order_by(WeatherObservation.observed_at.asc())
            )
            if is_prod:
                query = query.filter(~WeatherObservation.provider_name.ilike("%DEMO%"))
            all_existing = query.all()
            
            # Filter by spatial proximity (25 km threshold)
            existing = [
                obs for obs in all_existing
                if haversine_distance_km(latitude, longitude, obs.latitude, obs.longitude) <= 25.0
            ]
            if existing and len(existing) >= 2:
                return [
                    WeatherObservationDTO(
                        provider_name=e.provider_name,
                        source_identifier=e.source_identifier,
                        latitude=e.latitude,
                        longitude=e.longitude,
                        spatial_resolution_km=e.spatial_resolution_km,
                        observed_at=e.observed_at,
                        temperature_celsius=e.temperature_celsius,
                        relative_humidity_pct=e.relative_humidity_pct,
                        heat_index_celsius=e.heat_index_celsius,
                        wbgt_estimated_celsius=e.wbgt_estimated_celsius,
                        wind_speed_mps=e.wind_speed_mps,
                        solar_radiation_wm2=e.solar_radiation_wm2,
                        confidence_score=e.confidence_score,
                        data_freshness_status=e.data_freshness_status,
                        validation_status=e.validation_status,
                        raw_payload=e.raw_data_payload,
                    )
                    for e in existing
                ]

        # Otherwise fetch from official meteorological providers (IMD AWS network or ERA5 reanalysis)
        if settings.IMD_API_KEY:
            try:
                imd_results = await self.imd_provider.get_observations_for_interval(
                    latitude, longitude, start_time, end_time
                )
                if imd_results:
                    if db:
                        for r in imd_results:
                            self._persist_observation(db, r)
                    return imd_results
            except Exception as e:
                logger.warning(f"IMD interval retrieval failed: {e}")

        if settings.CDS_API_KEY:
            try:
                era5_results = await self.era5_provider.get_observations_for_interval(
                    latitude, longitude, start_time, end_time
                )
                if era5_results:
                    if db:
                        for r in era5_results:
                            self._persist_observation(db, r)
                    return era5_results
            except Exception as e:
                logger.warning(f"ERA5 retrieval failed: {e}")

        if settings.ENVIRONMENT == "production" or not settings.DEMO_MODE:
            logger.warning("Historical meteorological observations unavailable in production; DEMO data rejected.")
            return []

        results = await self.demo_provider.get_observations_for_interval(
            latitude, longitude, start_time, end_time
        )
        if db:
            for r in results:
                self._persist_observation(db, r)
        return results

    def _persist_observation(self, db: Session, dto: WeatherObservationDTO) -> WeatherObservation:
        model = WeatherObservation(
            provider_name=dto.provider_name,
            source_identifier=dto.source_identifier,
            latitude=dto.latitude,
            longitude=dto.longitude,
            spatial_resolution_km=dto.spatial_resolution_km,
            observed_at=dto.observed_at,
            ingested_at=utc_now(),
            temperature_celsius=dto.temperature_celsius,
            relative_humidity_pct=dto.relative_humidity_pct,
            heat_index_celsius=dto.heat_index_celsius,
            wbgt_estimated_celsius=dto.wbgt_estimated_celsius,
            wind_speed_mps=dto.wind_speed_mps,
            solar_radiation_wm2=dto.solar_radiation_wm2,
            confidence_score=dto.confidence_score,
            data_freshness_status=dto.data_freshness_status,
            validation_status=dto.validation_status,
            raw_data_payload=dto.raw_payload,
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        return model

    async def get_all_providers_status(self) -> List[Dict[str, Any]]:
        imd_stat = await self.imd_provider.check_health()
        era5_stat = await self.era5_provider.check_health()
        demo_stat = await self.demo_provider.check_health()
        return [imd_stat, era5_stat, demo_stat]

weather_service = WeatherProviderService()
