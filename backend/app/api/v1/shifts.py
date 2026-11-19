from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from backend.app.core.database import get_db
from backend.app.models.entities import Shift, BreakEvent, utc_now
from backend.app.schemas.shifts import (
    ShiftStartRequest,
    ShiftEndRequest,
    ShiftCorrectionRequest,
    ShiftResponse,
    ShiftSummary,
)
from backend.app.services.shift_service import ShiftService
from backend.app.api.deps import get_current_worker, log_audit

router = APIRouter(prefix="/shifts", tags=["Shifts"])

@router.get("/active", response_model=ShiftSummary)
def get_active_shift_and_summary(
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    active = ShiftService.get_active_shift(db, current_worker.id)
    
    # Calculate today's working and break minutes (in UTC / IST window)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_shifts = (
        db.query(Shift)
        .filter(Shift.worker_id == current_worker.id, Shift.started_at >= today_start)
        .all()
    )
    
    today_work = sum(s.total_working_minutes for s in today_shifts)
    today_break = sum(s.total_break_minutes for s in today_shifts)
    total_count = db.query(Shift).filter(Shift.worker_id == current_worker.id).count()

    return ShiftSummary(
        active_shift=active,
        today_working_minutes=today_work,
        today_break_minutes=today_break,
        total_shifts_count=total_count,
    )

@router.post("/start", response_model=ShiftResponse)
def start_shift(
    req: ShiftStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    shift = ShiftService.start_shift(
        db,
        current_worker.id,
        location_tracking_requested=req.location_tracking_enabled,
        started_at=req.started_at,
    )
    log_audit(
        db, current_worker.id, "SHIFT_STARTED", "Shift", shift.id,
        {"location_tracking": shift.location_tracking_enabled}, request
    )
    return shift

@router.post("/{shift_id}/pause", response_model=ShiftResponse)
def pause_shift(
    shift_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    shift = ShiftService.pause_shift(db, shift_id, current_worker.id)
    log_audit(db, current_worker.id, "SHIFT_PAUSED", "Shift", shift.id, None, request)
    return shift

@router.post("/{shift_id}/resume", response_model=ShiftResponse)
def resume_shift(
    shift_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    shift = ShiftService.resume_shift(db, shift_id, current_worker.id)
    log_audit(db, current_worker.id, "SHIFT_RESUMED", "Shift", shift.id, None, request)
    return shift

@router.post("/{shift_id}/end", response_model=ShiftResponse)
def end_shift(
    shift_id: str,
    req: ShiftEndRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    shift = ShiftService.end_shift(db, shift_id, current_worker.id, ended_at=req.ended_at)
    log_audit(
        db, current_worker.id, "SHIFT_ENDED", "Shift", shift.id,
        {"working_minutes": shift.total_working_minutes, "break_minutes": shift.total_break_minutes},
        request
    )
    return shift

@router.post("/{shift_id}/correct", response_model=ShiftResponse)
def correct_shift(
    shift_id: str,
    req: ShiftCorrectionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    shift = ShiftService.correct_shift(
        db,
        shift_id,
        current_worker.id,
        started_at=req.started_at,
        ended_at=req.ended_at,
        reason=req.manual_correction_reason,
    )
    log_audit(db, current_worker.id, "SHIFT_CORRECTED", "Shift", shift.id, {"reason": req.manual_correction_reason}, request)
    return shift

@router.get("", response_model=List[ShiftResponse])
def list_my_shifts(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return (
        db.query(Shift)
        .filter(Shift.worker_id == current_worker.id)
        .order_by(Shift.started_at.desc())
        .limit(limit)
        .all()
    )

@router.get("/{shift_id}", response_model=ShiftResponse)
def get_shift_details(
    shift_id: str,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == current_worker.id).first()
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
    return shift
