from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class ShareGrantCreate(BaseModel):
    organisation_id: str
    report_id: str
    purpose: str = Field(min_length=5, description="Specific purpose for sharing, e.g. 'Welfare grant application review'")
    duration_days: int = Field(default=30, ge=1, le=180)

class ShareGrantResponse(BaseSchema):
    id: str
    worker_id: str
    organisation_id: str
    report_id: str
    purpose: str
    expires_at: datetime
    is_revoked: bool
    revoked_at: Optional[datetime] = None
    granted_at: datetime
    access_count: int

class ShareRevokeRequest(BaseModel):
    reason: Optional[str] = None
