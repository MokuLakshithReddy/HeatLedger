from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.schemas.common import BaseSchema

class EarningsUploadResponse(BaseSchema):
    id: str
    worker_id: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    sha256_hash: str
    upload_status: str
    processing_error: Optional[str] = None
    uploaded_at: datetime

class EarningEntryResponse(BaseSchema):
    id: str
    upload_id: str
    worker_id: str
    platform_name: str
    statement_period_start: Optional[datetime] = None
    statement_period_end: Optional[datetime] = None
    base_earnings: float
    order_payments: float
    incentives: float
    bonuses: float
    deductions: float
    penalties: float
    taxes: float
    net_amount: float
    payment_date: Optional[datetime] = None
    extraction_confidence: float
    is_confirmed_by_worker: bool
    worker_confirmed_at: Optional[datetime] = None
    worker_adjusted_notes: Optional[str] = None

class EarningEntryConfirmRequest(BaseModel):
    is_confirmed: bool = True
    adjusted_base_earnings: Optional[float] = None
    adjusted_incentives: Optional[float] = None
    adjusted_deductions: Optional[float] = None
    adjusted_net_amount: Optional[float] = None
    worker_adjusted_notes: Optional[str] = None

class ExtractionStructuredResult(BaseModel):
    platform_name: str
    statement_period_start: Optional[str] = None # YYYY-MM-DD or None if not detected
    statement_period_end: Optional[str] = None   # YYYY-MM-DD or None if not detected
    base_earnings: float = 0.0
    order_payments: float = 0.0
    incentives: float = 0.0
    bonuses: float = 0.0
    deductions: float = 0.0
    penalties: float = 0.0
    taxes: float = 0.0
    net_amount: float = 0.0
    payment_date: Optional[str] = None
    confidence_score: float = 1.0
    source_attribution_notes: Optional[str] = None
