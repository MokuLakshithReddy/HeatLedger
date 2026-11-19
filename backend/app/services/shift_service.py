from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import Shift, BreakEvent, utc_now
from backend.app.core.datetime_utils import ensure_utc
from backend.app.services.consent_service import ConsentService

class ShiftService:
    @staticmethod
    def get_active_shift(db: Session, worker_id: str) -> Optional[Shift]:
        return (
            db.query(Shift)
            .filter(
                Shift.worker_id == worker_id,
                Shift.status.in_(["ACTIVE", "PAUSED"]),
            )
            .first()
        )

    @staticmethod
    def start_shift(
        db: Session,
        worker_id: str,
        location_tracking_requested: bool = False,
        started_at: Optional[datetime] = None,
    ) -> Shift:
        # Check for overlapping active shifts
        existing = ShiftService.get_active_shift(db, worker_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An active shift (ID: {existing.id}) is already in progress. You must end it before starting a new shift.",
            )

        # Verify location tracking permission
        can_track_location = False
        if location_tracking_requested:
            has_consent = ConsentService.is_consent_active(
                db, worker_id, "LOCATION_TRACKING_DURING_SHIFT"
            )
            if has_consent:
                can_track_location = True
            else:
                # Fall back gracefully to false, transparently documented
                can_track_location = False

        start_time = started_at or utc_now()
        shift = Shift(
            worker_id=worker_id,
            status="ACTIVE",
            started_at=start_time,
            ended_at=None,
            total_working_minutes=0,
            total_break_minutes=0,
            location_tracking_enabled=can_track_location,
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def pause_shift(db: Session, shift_id: str, worker_id: str) -> Shift:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        if shift.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shift cannot be paused from state: {shift.status}",
            )
        shift.status = "PAUSED"
        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def resume_shift(db: Session, shift_id: str, worker_id: str) -> Shift:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        if shift.status != "PAUSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shift cannot be resumed from state: {shift.status}",
            )
        # End any open breaks
        open_breaks = (
            db.query(BreakEvent)
            .filter(
                BreakEvent.shift_id == shift_id,
                BreakEvent.ended_at.is_(None),
            )
            .all()
        )
        now = utc_now()
        for b in open_breaks:
            b.ended_at = now
            delta = int((b.ended_at - b.started_at).total_seconds() / 60)
            b.duration_minutes = max(0, delta)

        shift.status = "ACTIVE"
        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def end_shift(
        db: Session,
        shift_id: str,
        worker_id: str,
        ended_at: Optional[datetime] = None,
    ) -> Shift:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        if shift.status in ["COMPLETED", "CANCELLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Shift is already closed with status: {shift.status}",
            )

        end_time = ended_at or utc_now()
        if ensure_utc(end_time) < ensure_utc(shift.started_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shift end time cannot precede shift start time",
            )

        # Close any open breaks
        open_breaks = (
            db.query(BreakEvent)
            .filter(
                BreakEvent.shift_id == shift_id,
                BreakEvent.ended_at.is_(None),
            )
            .all()
        )
        for b in open_breaks:
            b.ended_at = end_time
            delta = int((ensure_utc(b.ended_at) - ensure_utc(b.started_at)).total_seconds() / 60)
            b.duration_minutes = max(0, delta)

        # Calculate total break minutes
        all_breaks = db.query(BreakEvent).filter(BreakEvent.shift_id == shift_id).all()
        total_break_min = sum(b.duration_minutes for b in all_breaks)

        # Calculate total elapsed minutes and active working minutes
        total_elapsed_min = int((ensure_utc(end_time) - ensure_utc(shift.started_at)).total_seconds() / 60)
        total_working_min = max(0, total_elapsed_min - total_break_min)

        shift.ended_at = end_time
        shift.total_break_minutes = total_break_min
        shift.total_working_minutes = total_working_min
        shift.status = "COMPLETED"
        shift.location_tracking_enabled = False # Immediately disable tracking

        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def correct_shift(
        db: Session,
        shift_id: str,
        worker_id: str,
        started_at: Optional[datetime],
        ended_at: Optional[datetime],
        reason: str,
    ) -> Shift:
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")
        
        if not reason or len(reason.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Manual correction requires an audited reason (minimum 5 characters).",
            )

        if started_at:
            shift.started_at = started_at
        if ended_at:
            shift.ended_at = ended_at

        if shift.ended_at and ensure_utc(shift.ended_at) < ensure_utc(shift.started_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Shift end time cannot precede shift start time",
            )

        # Recompute totals if ended
        if shift.ended_at:
            all_breaks = db.query(BreakEvent).filter(BreakEvent.shift_id == shift_id).all()
            total_break_min = sum(b.duration_minutes for b in all_breaks)
            total_elapsed_min = int((ensure_utc(shift.ended_at) - ensure_utc(shift.started_at)).total_seconds() / 60)
            shift.total_break_minutes = total_break_min
            shift.total_working_minutes = max(0, total_elapsed_min - total_break_min)

        shift.manual_correction_reason = f"[{utc_now().isoformat()}] {reason}"
        db.commit()
        db.refresh(shift)
        return shift
