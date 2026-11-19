from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.database import get_db
from backend.app.models.entities import EarningsUpload, EarningEntry
from backend.app.schemas.earnings import (
    EarningsUploadResponse,
    EarningEntryResponse,
    EarningEntryConfirmRequest,
)
from backend.app.earnings.pipeline import EarningsPipeline
from backend.app.api.deps import get_current_worker, log_audit

router = APIRouter(prefix="/earnings", tags=["Earnings"])

@router.post("/uploads", response_model=EarningsUploadResponse)
async def upload_earnings_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    upload, entry = await EarningsPipeline.process_upload(db, current_worker.id, file)
    log_audit(
        db, current_worker.id, "EARNINGS_UPLOADED", "EarningsUpload", upload.id,
        {"filename": upload.original_filename, "sha256": upload.sha256_hash}, request
    )
    return upload

@router.get("/uploads", response_model=List[EarningsUploadResponse])
def list_my_earnings_uploads(
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return (
        db.query(EarningsUpload)
        .filter(EarningsUpload.worker_id == current_worker.id)
        .order_by(EarningsUpload.uploaded_at.desc())
        .all()
    )

@router.get("/uploads/{upload_id}", response_model=EarningsUploadResponse)
def get_upload_details(
    upload_id: str,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    upload = (
        db.query(EarningsUpload)
        .filter(EarningsUpload.id == upload_id, EarningsUpload.worker_id == current_worker.id)
        .first()
    )
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")
    return upload

@router.get("/entries", response_model=List[EarningEntryResponse])
def list_my_earning_entries(
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return (
        db.query(EarningEntry)
        .filter(EarningEntry.worker_id == current_worker.id)
        .order_by(EarningEntry.statement_period_start.desc())
        .all()
    )

@router.post("/entries/{entry_id}/confirm", response_model=EarningEntryResponse)
def confirm_or_adjust_earning_entry(
    entry_id: str,
    confirm_req: EarningEntryConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    entry = EarningsPipeline.confirm_earning_entry(
        db, entry_id, current_worker.id, confirm_req
    )
    log_audit(
        db, current_worker.id, "EARNINGS_CONFIRMED", "EarningEntry", entry.id,
        {"net_amount": entry.net_amount, "is_confirmed": entry.is_confirmed_by_worker}, request
    )
    return entry
