from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class EvidenceTimelineEventResponse(BaseModel):
    id: str
    event_category: str # WORKER_ACTION, LOCATION_OBSERVATION, WEATHER_OBSERVATION, etc.
    timestamp: datetime
    title: str
    description: str
    provenance_source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    anomaly_flag: Optional[str] = None

class EvidenceTimelineResponse(BaseModel):
    worker_id: str
    period_start: datetime
    period_end: datetime
    events_count: int
    events: List[EvidenceTimelineEventResponse]
    flags_detected: List[str] = Field(default_factory=list)
    limitations_disclaimer: str
