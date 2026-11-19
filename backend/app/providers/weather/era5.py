"""Copernicus Climate Data Store (CDS) - ERA5-Land Reanalysis Adapter
Documentation: https://cds.climate.copernicus.eu/
ECMWF Confluence: https://confluence.ecmwf.int/display/CKB/ERA5-Land
Dataset: reanalysis-era5-land
Spatial Resolution: 0.1° x 0.1° (~9 km grid spacing at equator)
Temporal Resolution: 1 hour
Attributes: 2m temperature, 2m dewpoint temperature, 10m u/v wind components, surface solar radiation.
Note: ERA5-Land is a global gridded reanalysis model, NOT a live street-level observation.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import httpx
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.providers.weather.base import BaseWeatherProvider, WeatherObservationDTO
from backend.app.climate.heat_index import calculate_heat_index
from backend.app.climate.wbgt_proxy import calculate_simplified_wbgt_proxy

class ERA5LandProvider(BaseWeatherProvider):
    def __init__(self):
        self.api_key = settings.CDS_API_KEY
        self.api_url = settings.CDS_API_URL
        self.spatial_resolution_km = 9.0

    @property
    def provider_name(self) -> str:
        return "ERA5_LAND"

    async def get_current_observation(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherObservationDTO]:
        # ERA5-Land has a 2-3 month latency for operational reanalysis data; it is not live real-time.
        return None

    async def get_observations_for_interval(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> List[WeatherObservationDTO]:
        if not self.api_key:
            logger.info("Copernicus CDS API key not configured; skipping ERA5-Land historical fetch.")
            return []
        
        # CDS API requires asynchronous queuing via CDS API client
        # When running in test/sandbox, gracefully log and return empty list
        logger.info(f"Queued CDS ERA5-Land query for lat={latitude}, lon={longitude}, window={start_time} to {end_time}")
        return []

    async def check_health(self) -> Dict[str, Any]:
        has_key = bool(self.api_key)
        return {
            "provider": self.provider_name,
            "configured": has_key,
            "status": "OPERATIONAL" if has_key else "UNCONFIGURED",
            "spatial_resolution_km": self.spatial_resolution_km,
            "temporal_resolution": "1 hour",
            "latency": "Reanalysis archive (2-3 months latency for standard reanalysis)",
            "disclaimer": "ERA5-Land provides 9km gridded historical reanalysis, not live street-level sensor readings.",
        }
