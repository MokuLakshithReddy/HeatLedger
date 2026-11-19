from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import ConsentRecord, User, WorkerProfile, Shift, utc_now

VALID_PURPOSES = {
    "LOCATION_TRACKING_DURING_SHIFT",
    "EARNINGS_DOCUMENT_EXTRACTION",
    "ANONYMIZED_CLIMATE_RESEARCH",
    "ORGANISATION_REPORT_SHARING",
}

class ConsentService:
    @staticmethod
    def get_user_consents(db: Session, user_id: str) -> List[ConsentRecord]:
        return db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).all()

    @staticmethod
    def is_consent_active(db: Session, user_id: str, purpose: str) -> bool:
        if purpose not in VALID_PURPOSES:
            return False
        record = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.is_granted == True,
            )
            .order_by(ConsentRecord.created_at.desc())
            .first()
        )
        return record is not None and record.revoked_at is None

    @staticmethod
    def grant_consent(
        db: Session,
        user_id: str,
        purpose: str,
        consent_text_version: str = "1.0",
        user_agent: Optional[str] = None,
        ip_hash: Optional[str] = None,
    ) -> ConsentRecord:
        if purpose not in VALID_PURPOSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid consent purpose: {purpose}. Valid purposes: {list(VALID_PURPOSES)}",
            )
        
        now = utc_now()
        consent = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            consent_text_version=consent_text_version,
            is_granted=True,
            granted_at=now,
            revoked_at=None,
            ip_address_hash=ip_hash,
            user_agent_summary=user_agent[:255] if user_agent else None,
        )
        db.add(consent)

        # Update worker profile flag if purpose is location
        if purpose == "LOCATION_TRACKING_DURING_SHIFT":
            wp = db.query(WorkerProfile).filter(WorkerProfile.user_id == user_id).first()
            if wp:
                wp.consented_location_tracking = True

        db.commit()
        db.refresh(consent)
        return consent

    @staticmethod
    def revoke_consent(
        db: Session,
        user_id: str,
        purpose: str,
    ) -> ConsentRecord:
        now = utc_now()
        existing = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == purpose,
                ConsentRecord.is_granted == True,
            )
            .all()
        )
        for rec in existing:
            rec.is_granted = False
            rec.revoked_at = now

        # Create explicit revoked audit record
        revocation_record = ConsentRecord(
            user_id=user_id,
            purpose=purpose,
            consent_text_version="1.0",
            is_granted=False,
            revoked_at=now,
        )
        db.add(revocation_record)

        # If location consent is revoked, immediately disable location tracking on any active shift
        if purpose == "LOCATION_TRACKING_DURING_SHIFT":
            wp = db.query(WorkerProfile).filter(WorkerProfile.user_id == user_id).first()
            if wp:
                wp.consented_location_tracking = False

            active_shifts = (
                db.query(Shift)
                .filter(Shift.worker_id == user_id, Shift.status.in_(["ACTIVE", "PAUSED"]))
                .all()
            )
            for shift in active_shifts:
                shift.location_tracking_enabled = False

        db.commit()
        db.refresh(revocation_record)
        return revocation_record
