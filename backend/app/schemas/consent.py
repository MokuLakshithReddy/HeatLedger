from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class ConsentCreate(BaseModel):
    purpose: str = Field(description="e.g. LOCATION_TRACKING_DURING_SHIFT, EARNINGS_DOCUMENT_EXTRACTION, etc.")
    consent_text_version: str = Field(default="1.0")
    is_granted: bool
    user_agent_summary: Optional[str] = None

class ConsentRevoke(BaseModel):
    purpose: str

class ConsentResponse(BaseSchema):
    id: str
    user_id: str
    purpose: str
    consent_text_version: str
    is_granted: bool
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
