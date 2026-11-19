from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class BreakStartRequest(BaseModel):
    break_type: str = Field(default="REST", description="REST, HYDRATION, MEAL, SHELTER, OTHER")
    worker_notes: Optional[str] = None
    started_at: Optional[datetime] = None

class BreakEndRequest(BaseModel):
    ended_at: Optional[datetime] = None
    worker_notes: Optional[str] = None

class BreakCorrectionRequest(BaseModel):
    break_type: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    correction_reason: str = Field(min_length=5)

class BreakResponse(BaseSchema):
    id: str
    shift_id: str
    worker_id: str
    break_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: int
    worker_notes: Optional[str] = None
    is_worker_declared: bool
    created_at: datetime
