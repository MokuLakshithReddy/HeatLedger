from datetime import datetime, timezone, timedelta
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

        start_time = started_at or utc_now()
        if ensure_utc(start_time) > utc_now() + timedelta(minutes=5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Break start time cannot be in the future.",
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Break has already ended",
            )

        end_time = ended_at or utc_now()
        if ensure_utc(end_time) > utc_now() + timedelta(minutes=5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Break end time cannot be in the future.",
            )

        if ensure_utc(end_time) < ensure_utc(break_event.started_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Break end time cannot precede start time",
            )

        break_event.ended_at = end_time
        if worker_notes:
            break_event.worker_notes = worker_notes

        delta = int((ensure_utc(end_time) - ensure_utc(break_event.started_at)).total_seconds() / 60)
        break_event.duration_minutes = max(0, delta)

        # Resume shift to ACTIVE state if not closed
        shift = db.query(Shift).filter(Shift.id == break_event.shift_id).first()
        if shift and shift.status == "PAUSED":
            shift.status = "ACTIVE"
            # Recalculate shift break minutes
            all_breaks = db.query(BreakEvent).filter(BreakEvent.shift_id == shift.id).all()
            shift.total_break_minutes = sum(b.duration_minutes for b in all_breaks if b.duration_minutes)

        db.commit()
        db.refresh(break_event)
        return break_event

    @staticmethod
    def manual_correction(
        db: Session,
        break_id: str,
        worker_id: str,
        reason: str,
        adjusted_duration_minutes: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> BreakEvent:
        if not reason or not reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid explanation reason is mandatory for any retrospective break correction.",
            )

        b = db.query(BreakEvent).filter(BreakEvent.id == break_id, BreakEvent.worker_id == worker_id).first()
        if not b:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Break not found")

        orig_dur = b.duration_minutes
        if adjusted_duration_minutes is not None:
            if adjusted_duration_minutes < 0:
                raise HTTPException(status_code=400, detail="Duration cannot be negative.")
            b.duration_minutes = adjusted_duration_minutes

        if notes:
            b.worker_notes = notes

        b.is_manually_corrected = True
        b.correction_reason = reason.strip()
        b.original_duration_minutes = orig_dur
        b.corrected_at = utc_now()

        # Recalculate shift break totals
        shift = db.query(Shift).filter(Shift.id == b.shift_id).first()
        if shift:
            all_breaks = db.query(BreakEvent).filter(BreakEvent.shift_id == shift.id).all()
            shift.total_break_minutes = sum(x.duration_minutes for x in all_breaks)
            if shift.ended_at:
                elapsed = int((ensure_utc(shift.ended_at) - ensure_utc(shift.started_at)).total_seconds() / 60)
                shift.total_working_minutes = max(0, elapsed - shift.total_break_minutes)

        db.commit()
        db.refresh(b)
        return b
