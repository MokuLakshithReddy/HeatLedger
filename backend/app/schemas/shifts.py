from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class ShiftStartRequest(BaseModel):
    location_tracking_enabled: bool = False
    started_at: Optional[datetime] = None # Defaults to utc_now

class ShiftEndRequest(BaseModel):
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None

class ShiftCorrectionRequest(BaseModel):
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    manual_correction_reason: str = Field(min_length=5, description="Audited explanation for manual shift adjustment")

class ShiftResponse(BaseSchema):
    id: str
    worker_id: str
    status: str # ACTIVE, PAUSED, COMPLETED, CANCELLED
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_working_minutes: int
    total_break_minutes: int
    location_tracking_enabled: bool
    manual_correction_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ShiftSummary(BaseSchema):
    active_shift: Optional[ShiftResponse] = None
    today_working_minutes: int = 0
    today_break_minutes: int = 0
    total_shifts_count: int = 0
