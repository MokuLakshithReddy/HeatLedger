from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.core.database import get_db
from backend.app.models.entities import User, WorkerProfile, ConsentRecord, Shift, BreakEvent, EarningEntry, EvidenceReport, utc_now
from backend.app.schemas.auth import UserResponse, UserPreferencesUpdate
from backend.app.schemas.consent import ConsentCreate, ConsentResponse, ConsentRevoke
from backend.app.services.consent_service import ConsentService
from backend.app.api.deps import get_current_user, log_audit, hash_ip

router = APIRouter(prefix="/profiles", tags=["Profiles & Consents"])

@router.get("/me", response_model=UserResponse)
def get_current_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me/preferences", response_model=UserResponse)
def update_preferences(
    pref_in: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if pref_in.preferred_language:
        if pref_in.preferred_language not in ["en", "te", "hi"]:
            raise HTTPException(status_code=400, detail="Supported languages: 'en', 'te', 'hi'")
        current_user.preferred_language = pref_in.preferred_language
    if pref_in.full_name is not None:
        current_user.full_name = pref_in.full_name
    current_user.updated_at = utc_now()
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me/consents", response_model=List[ConsentResponse])
def get_my_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ConsentService.get_user_consents(db, current_user.id)

@router.post("/me/consents", response_model=ConsentResponse)
def grant_or_update_consent(
    consent_in: ConsentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ip_hash = hash_ip(request.client.host) if request.client else None
    user_agent = request.headers.get("user-agent", "HeatLedger Client")
    
    if consent_in.is_granted:
        record = ConsentService.grant_consent(
            db,
            current_user.id,
            consent_in.purpose,
            consent_in.consent_text_version,
            user_agent,
            ip_hash,
        )
        log_audit(db, current_user.id, "CONSENT_GRANTED", "ConsentRecord", record.id, {"purpose": record.purpose}, request)
    else:
        record = ConsentService.revoke_consent(db, current_user.id, consent_in.purpose)
        log_audit(db, current_user.id, "CONSENT_REVOKED", "ConsentRecord", record.id, {"purpose": record.purpose}, request)
    return record

@router.post("/me/consents/revoke", response_model=ConsentResponse)
def revoke_consent(
    revoke_in: ConsentRevoke,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = ConsentService.revoke_consent(db, current_user.id, revoke_in.purpose)
    log_audit(db, current_user.id, "CONSENT_REVOKED", "ConsentRecord", record.id, {"purpose": revoke_in.purpose}, request)
    return record

@router.get("/me/export")
def export_my_data(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Section 15: Full portable personal data export under Indian DPDP Act."""
    shifts = db.query(Shift).filter(Shift.worker_id == current_user.id).all()
    breaks = db.query(BreakEvent).filter(BreakEvent.worker_id == current_user.id).all()
    earnings = db.query(EarningEntry).filter(EarningEntry.worker_id == current_user.id).all()
    consents = db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).all()
    reports = db.query(EvidenceReport).filter(EvidenceReport.worker_id == current_user.id).all()

    log_audit(db, current_user.id, "DATA_EXPORTED", "User", current_user.id, None, request)

    return {
        "export_metadata": {
            "worker_id": current_user.id,
            "exported_at": utc_now().isoformat(),
            "format_version": "1.0",
            "jurisdiction": "India - DPDP Act Compliant",
        },
        "profile": {
            "email": current_user.email,
            "phone": current_user.phone,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "preferred_language": current_user.preferred_language,
        },
        "consents": [
            {"purpose": c.purpose, "is_granted": c.is_granted, "granted_at": str(c.granted_at), "revoked_at": str(c.revoked_at)}
            for c in consents
        ],
        "shifts": [
            {"id": s.id, "started_at": str(s.started_at), "ended_at": str(s.ended_at), "working_minutes": s.total_working_minutes}
            for s in shifts
        ],
        "breaks": [
            {"id": b.id, "type": b.break_type, "started_at": str(b.started_at), "duration_minutes": b.duration_minutes}
            for b in breaks
        ],
        "earnings": [
            {"id": e.id, "platform": e.platform_name, "net_amount": e.net_amount, "period_start": str(e.statement_period_start)}
            for e in earnings
        ],
        "reports": [
            {"report_number": r.report_number, "sha256": r.integrity_sha256, "created_at": str(r.created_at)}
            for r in reports
        ],
    }

@router.delete("/me/delete")
def request_account_deletion(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Section 15: Account deletion workflow under Indian DPDP Act."""
    log_audit(db, current_user.id, "ACCOUNT_DELETED", "User", current_user.id, None, request)
    current_user.is_active = False
    current_user.email = f"deleted_{current_user.id}@heatledger.local"
    current_user.phone = None
    db.commit()
    return {"success": True, "message": "Account successfully deactivated and queued for full data purging."}
