from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class WeatherObservationDTO(BaseModel):
    provider_name: str
    source_identifier: str
    latitude: float
    longitude: float
    spatial_resolution_km: Optional[float] = None
    observed_at: datetime
    temperature_celsius: float
    relative_humidity_pct: float
    heat_index_celsius: Optional[float] = None
    wbgt_estimated_celsius: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    solar_radiation_wm2: Optional[float] = None
    data_type: str = "DIRECT_STATION_OBSERVATION" # DIRECT_STATION_OBSERVATION, GRIDDED_REANALYSIS, DEMO_FIXTURE
    confidence_score: float = 1.0
    data_freshness_status: str # REALTIME, HOURLY, HISTORICAL_REANALYSIS, DEMO_SAMPLE
    validation_status: str # VALIDATED, PROVISIONAL, FALLBACK
    raw_payload: Optional[Dict[str, Any]] = None

class BaseWeatherProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def get_current_observation(
        self, latitude: float, longitude: float
    ) -> Optional[WeatherObservationDTO]:
        pass

    @abstractmethod
    async def get_observations_for_interval(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> List[WeatherObservationDTO]:
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        pass
