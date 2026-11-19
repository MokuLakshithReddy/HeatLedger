from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import Shift, LocationSample, utc_now
from backend.app.core.datetime_utils import ensure_utc
from backend.app.services.consent_service import ConsentService
from backend.app.schemas.location import LocationSampleCreate

class LocationService:
    @staticmethod
    def record_sample(
        db: Session,
        shift_id: str,
        worker_id: str,
        sample_in: LocationSampleCreate,
    ) -> LocationSample:
        # 1. Verify shift exists and belongs to worker
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

        # 2. Verify shift is actively ongoing
        if shift.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Location samples can only be recorded during an ACTIVE shift (current state: {shift.status})",
            )

        # 3. Verify location tracking is explicitly enabled for this shift
        if not shift.location_tracking_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Location tracking is disabled for this shift: Worker must explicitly consent and enable tracking (or has revoked location tracking consent).",
            )

        # 4. Verify worker has an active, unrevoked consent record for location tracking
        has_active_consent = ConsentService.is_consent_active(
            db, worker_id, "LOCATION_TRACKING_DURING_SHIFT"
        )
        if not has_active_consent:
            # Revocation safety check: if consent was revoked mid-shift, disable shift tracking immediately
            shift.location_tracking_enabled = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Location recording rejected: Worker has revoked location tracking consent.",
            )

        recorded_time = sample_in.recorded_at or utc_now()

        # Reject unreasonable or invalid timestamps (e.g. before shift started)
        if ensure_utc(recorded_time) < ensure_utc(shift.started_at):
            recorded_time = shift.started_at

        # Flag sample validity based on accuracy threshold (e.g. accuracy > 500m is flagged low quality)
        is_valid = sample_in.accuracy_meters <= 500.0

        sample = LocationSample(
            shift_id=shift_id,
            worker_id=worker_id,
            latitude=sample_in.latitude,
            longitude=sample_in.longitude,
            accuracy_meters=sample_in.accuracy_meters,
            altitude_meters=sample_in.altitude_meters,
            speed_mps=sample_in.speed_mps,
            recorded_at=recorded_time,
            is_valid=is_valid,
        )
        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample

    @staticmethod
    def record_batch(
        db: Session,
        shift_id: str,
        worker_id: str,
        samples: List[LocationSampleCreate],
    ) -> List[LocationSample]:
        recorded = []
        for s in samples:
            try:
                item = LocationService.record_sample(db, shift_id, worker_id, s)
                recorded.append(item)
            except HTTPException:
                continue
        return recorded

    @staticmethod
    def get_shift_samples(
        db: Session,
        shift_id: str,
        worker_id: str,
        limit: int = 500,
    ) -> List[LocationSample]:
        # Enforce worker ownership
        shift = db.query(Shift).filter(Shift.id == shift_id, Shift.worker_id == worker_id).first()
        if not shift:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift not found")

        return (
            db.query(LocationSample)
            .filter(LocationSample.shift_id == shift_id)
            .order_by(LocationSample.recorded_at.asc())
            .limit(limit)
            .all()
        )
