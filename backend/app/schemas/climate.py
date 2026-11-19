from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class WeatherObservationResponse(BaseSchema):
    id: str
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
    confidence_score: float
    data_freshness_status: str
    validation_status: str

class ExposureIntervalResponse(BaseSchema):
    id: str
    shift_id: str
    start_time: datetime
    end_time: datetime
    mean_temperature_celsius: float
    mean_relative_humidity_pct: float
    heat_index_celsius: float
    risk_category: str
    wbgt_proxy_celsius: Optional[float] = None
    quality_grade: str
    distance_to_source_km: Optional[float] = None
    temporal_offset_minutes: Optional[int] = None

class ProviderStatus(BaseModel):
    provider_name: str
    status: str # OPERATIONAL, DEGRADED, UNAVAILABLE, DEMO
    is_live: bool
    last_fetch_at: Optional[datetime] = None
    attribution_text: str
    spatial_resolution_km: Optional[float] = None
    disclaimer: str
