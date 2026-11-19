from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from backend.app.schemas.common import BaseSchema

class OrganisationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)
    contact_email: EmailStr
    description: Optional[str] = None
    org_type: str = Field(default="union")

class OrganisationResponse(BaseSchema):
    id: str
    name: str
    slug: str
    contact_email: str
    description: Optional[str] = None
    org_type: str
    is_approved: bool
    created_at: datetime

class CaseCreate(BaseModel):
    report_id: str
    title: str = Field(min_length=3, max_length=255)
    priority: str = Field(default="MEDIUM") # LOW, MEDIUM, HIGH, URGENT

class CaseResponse(BaseSchema):
    id: str
    organisation_id: str
    report_id: str
    case_number: str
    title: str
    status: str
    priority: str
    worker_pseudonym: str
    created_at: datetime
    updated_at: datetime

class CaseNoteCreate(BaseModel):
    note_content: str = Field(min_length=2)

class CaseNoteResponse(BaseSchema):
    id: str
    case_id: str
    author_user_id: str
    note_content: str
    created_at: datetime

class AggregateCohortAnalytics(BaseModel):
    cohort_name: str
    total_workers_in_cohort: int
    meets_k_anonymity_threshold: bool
    k_threshold: int
    average_heat_exposure_hours: Optional[float] = None
    average_shift_duration_hours: Optional[float] = None
    total_cases_filed: int = 0
    common_high_heat_time_bands: List[str] = Field(default_factory=list)
    anonymity_notice: str
