from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, model_validator, computed_field
from backend.app.schemas.common import BaseSchema

class ShareGrantCreate(BaseModel):
    organisation_id: Optional[str] = None
    recipient_org_id: Optional[str] = None
    report_id: str
    purpose: str = Field(default="Casework and welfare grant support", min_length=5, description="Specific purpose for sharing, e.g. 'Welfare grant application review'")
    duration_days: Optional[int] = Field(default=None, ge=1, le=180)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=180)

    @model_validator(mode="after")
    def resolve_aliases(self):
        if not self.organisation_id:
            self.organisation_id = self.recipient_org_id
        if not self.organisation_id:
            raise ValueError("organisation_id or recipient_org_id is required")
        if self.duration_days is None:
            self.duration_days = self.expires_in_days or 30
        return self

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

    @computed_field
    @property
    def is_active(self) -> bool:
        if self.is_revoked:
            return False
        now = datetime.now(timezone.utc)
        exp = self.expires_at if self.expires_at.tzinfo else self.expires_at.replace(tzinfo=timezone.utc)
        return exp > now

class ShareRevokeRequest(BaseModel):
    reason: Optional[str] = None
