from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class LocationSampleCreate(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    accuracy_meters: float = Field(ge=0.0)
    altitude_meters: Optional[float] = None
    speed_mps: Optional[float] = None
    recorded_at: Optional[datetime] = None

class LocationSampleBatch(BaseModel):
    samples: List[LocationSampleCreate]

class LocationSampleResponse(BaseSchema):
    id: str
    shift_id: str
    latitude: float
    longitude: float
    accuracy_meters: float
    altitude_meters: Optional[float] = None
    speed_mps: Optional[float] = None
    recorded_at: datetime
    is_valid: bool
