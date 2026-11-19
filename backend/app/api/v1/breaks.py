from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.database import get_db
from backend.app.schemas.breaks import BreakStartRequest, BreakEndRequest, BreakResponse
from backend.app.services.break_service import BreakService
from backend.app.api.deps import get_current_worker, log_audit

router = APIRouter(tags=["Breaks"])

@router.post("/shifts/{shift_id}/breaks", response_model=BreakResponse)
def start_break(
    shift_id: str,
    req: BreakStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    break_event = BreakService.start_break(
        db,
        shift_id,
        current_worker.id,
        break_type=req.break_type,
        worker_notes=req.worker_notes,
        started_at=req.started_at,
    )
    log_audit(db, current_worker.id, "BREAK_STARTED", "BreakEvent", break_event.id, {"type": break_event.break_type}, request)
    return break_event

@router.get("/shifts/{shift_id}/breaks", response_model=List[BreakResponse])
def get_shift_breaks(
    shift_id: str,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return BreakService.get_shift_breaks(db, shift_id, current_worker.id)

@router.post("/breaks/{break_id}/end", response_model=BreakResponse)
def end_break(
    break_id: str,
    req: BreakEndRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    break_event = BreakService.end_break(
        db,
        break_id,
        current_worker.id,
        ended_at=req.ended_at,
        worker_notes=req.worker_notes,
    )
    log_audit(db, current_worker.id, "BREAK_ENDED", "BreakEvent", break_event.id, {"duration_mins": break_event.duration_minutes}, request)
    return break_event
