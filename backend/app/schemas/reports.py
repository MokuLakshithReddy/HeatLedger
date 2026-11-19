from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class EvidenceReportCreate(BaseModel):
    period_start: datetime
    period_end: datetime
    include_location_summary: bool = True
    include_earnings_summary: bool = True

class EvidenceReportResponse(BaseSchema):
    id: str
    worker_id: str
    report_number: str
    period_start: datetime
    period_end: datetime
    total_shifts: int
    total_hours_worked: float
    total_extreme_heat_hours: float
    net_earnings_recorded: float
    integrity_sha256: str
    pdf_download_url: Optional[str] = None
    limitations_disclaimer: str
    generation_version: str
    created_at: datetime
