from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import Shift, BreakEvent, utc_now
from backend.app.core.datetime_utils import ensure_utc

VALID_BREAK_TYPES = {"REST", "HYDRATION", "MEAL", "SHELTER", "OTHER"}

class BreakService:
    @staticmethod
    def start_break(
        db: Session,
        shift_id: str,
        worker_id: str,
        break_type: str = "REST",
        worker_notes: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> BreakEvent:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        if shift.status in ["COMPLETED", "CANCELLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot start a break on a completed shift",
            )

        # Check if already has an open break
        open_break = (
            db.query(BreakEvent)
            .filter(BreakEvent.shift_id == shift_id, BreakEvent.ended_at.is_(None))
            .first()
        )
        if open_break:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An ongoing break is already in progress for this shift.",
            )

        if break_type not in VALID_BREAK_TYPES:
            break_type = "OTHER"

        start_time = started_at or utc_now()
        break_event = BreakEvent(
            shift_id=shift_id,
            worker_id=worker_id,
            break_type=break_type,
            started_at=start_time,
            ended_at=None,
            duration_minutes=0,
            worker_notes=worker_notes,
            is_worker_declared=True,
        )
        db.add(break_event)
        
        # Shift enters PAUSED state during break
        shift.status = "PAUSED"
        db.commit()
        db.refresh(break_event)
        return break_event

    @staticmethod
    def end_break(
        db: Session,
        break_id: str,
        worker_id: str,
        ended_at: Optional[datetime] = None,
        worker_notes: Optional[str] = None,
    ) -> BreakEvent:
        break_event = (
            db.query(BreakEvent)
            .filter(BreakEvent.id == break_id, BreakEvent.worker_id == worker_id)
            .first()
        )
        if not break_event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Break record not found")
        if break_event.ended_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Break is already concluded")

        end_time = ended_at or utc_now()
        if ensure_utc(end_time) < ensure_utc(break_event.started_at):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Break end time cannot precede start time")

        duration = int((ensure_utc(end_time) - ensure_utc(break_event.started_at)).total_seconds() / 60)
        break_event.ended_at = end_time
        break_event.duration_minutes = max(0, duration)
        if worker_notes:
            break_event.worker_notes = worker_notes

        # Resume shift to ACTIVE if shift still ongoing
        shift = db.query(Shift).filter(Shift.id == break_event.shift_id).first()
        if shift and shift.status == "PAUSED":
            shift.status = "ACTIVE"

        db.commit()
        db.refresh(break_event)
        return break_event

    @staticmethod
    def get_shift_breaks(db: Session, shift_id: str, worker_id: str) -> List[BreakEvent]:
        # Enforce worker ownership check
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        return (
            db.query(BreakEvent)
            .filter(BreakEvent.shift_id == shift_id)
            .order_by(BreakEvent.started_at.asc())
            .all()
        )
