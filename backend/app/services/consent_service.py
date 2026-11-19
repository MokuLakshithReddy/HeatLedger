from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import ConsentRecord, User, WorkerProfile, Shift, utc_now

PURPOSE_MAP: Dict[str, str] = {
    "LOCATION_TRACKING": "LOCATION_TRACKING_DURING_SHIFT",
    "LOCATION_TRACKING_DURING_SHIFT": "LOCATION_TRACKING_DURING_SHIFT",
    "EARNINGS_PROCESSING": "EARNINGS_DOCUMENT_EXTRACTION",
    "EARNINGS_DOCUMENT_EXTRACTION": "EARNINGS_DOCUMENT_EXTRACTION",
    "ORGANISATION_SHARING": "ORGANISATION_REPORT_SHARING",
    "ORGANISATION_REPORT_SHARING": "ORGANISATION_REPORT_SHARING",
    "ANONYMIZED_RESEARCH": "ANONYMIZED_CLIMATE_RESEARCH",
    "ANONYMIZED_CLIMATE_RESEARCH": "ANONYMIZED_CLIMATE_RESEARCH",
}

VALID_PURPOSES = set(PURPOSE_MAP.values())

def normalize_purpose(raw_purpose: str) -> str:
    key = raw_purpose.strip().upper().replace(" ", "_")
    if key in PURPOSE_MAP:
        return PURPOSE_MAP[key]
    return key

class ConsentService:
    @staticmethod
    def get_user_consents(db: Session, user_id: str) -> List[ConsentRecord]:
        return db.query(ConsentRecord).filter(ConsentRecord.user_id == user_id).order_by(ConsentRecord.created_at.desc()).all()

    @staticmethod
    def is_consent_active(db: Session, user_id: str, purpose: str) -> bool:
        norm_purpose = normalize_purpose(purpose)
        if norm_purpose not in VALID_PURPOSES:
            return False
        # Latest record determines authoritative active status
        record = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == norm_purpose,
            )
            .order_by(ConsentRecord.created_at.desc())
            .first()
        )
        return record is not None and record.is_granted and record.revoked_at is None

    @staticmethod
    def is_consent_granted(db: Session, user_id: str, purpose: str) -> bool:
        return ConsentService.is_consent_active(db, user_id, purpose)

    @staticmethod
    def grant_consent(
        db: Session,
        user_id: str,
        purpose: str,
        consent_text_version: str = "1.0",
        user_agent: Optional[str] = None,
        ip_hash: Optional[str] = None,
    ) -> ConsentRecord:
        norm_purpose = normalize_purpose(purpose)
        if norm_purpose not in VALID_PURPOSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid consent purpose: {purpose}. Valid purposes: {sorted(list(VALID_PURPOSES))}",
            )
        
        now = utc_now()
        consent = ConsentRecord(
            user_id=user_id,
            purpose=norm_purpose,
            consent_text_version=consent_text_version,
            is_granted=True,
            granted_at=now,
            revoked_at=None,
            ip_address_hash=ip_hash,
            user_agent_summary=user_agent[:255] if user_agent else None,
        )
        db.add(consent)

        # Update worker profile flag if purpose is location
        if norm_purpose == "LOCATION_TRACKING_DURING_SHIFT":
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
        norm_purpose = normalize_purpose(purpose)
        now = utc_now()
        existing = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.purpose == norm_purpose,
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
            purpose=norm_purpose,
            consent_text_version="1.0",
            is_granted=False,
            revoked_at=now,
        )
        db.add(revocation_record)

        # If location consent is revoked, immediately disable location tracking on any active shift
        if norm_purpose == "LOCATION_TRACKING_DURING_SHIFT":
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
