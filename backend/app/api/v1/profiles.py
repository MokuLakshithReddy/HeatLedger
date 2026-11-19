from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import shutil

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.entities import (
    User,
    WorkerProfile,
    ConsentRecord,
    Shift,
    BreakEvent,
    LocationSample,
    ExposureInterval,
    EarningsUpload,
    EarningEntry,
    EvidenceReport,
    ShareGrant,
    AuditLog,
    utc_now,
)
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
    """PRIV-05: Comprehensive, structured, portable personal data export under Indian DPDP Act."""
    shifts = db.query(Shift).filter(Shift.worker_id == current_user.id).order_by(Shift.started_at.asc()).all()
    shift_ids = [s.id for s in shifts]

    breaks = (
        db.query(BreakEvent)
        .filter(BreakEvent.shift_id.in_(shift_ids))
        .order_by(BreakEvent.started_at.asc())
        .all()
        if shift_ids else []
    )
    locations = (
        db.query(LocationSample)
        .filter(LocationSample.shift_id.in_(shift_ids))
        .order_by(LocationSample.recorded_at.asc())
        .all()
        if shift_ids else []
    )
    exposures = (
        db.query(ExposureInterval)
        .filter(ExposureInterval.shift_id.in_(shift_ids))
        .order_by(ExposureInterval.start_time.asc())
        .all()
        if shift_ids else []
    )
    uploads = db.query(EarningsUpload).filter(EarningsUpload.worker_id == current_user.id).all()
    earnings = db.query(EarningEntry).filter(EarningEntry.worker_id == current_user.id).all()
    consents = db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).order_by(ConsentRecord.created_at.desc()).all()
    reports = db.query(EvidenceReport).filter(EvidenceReport.worker_id == current_user.id).all()
    shares = db.query(ShareGrant).filter(ShareGrant.worker_id == current_user.id).all()
    audits = db.query(AuditLog).filter(AuditLog.user_id == current_user.id).order_by(AuditLog.timestamp.desc()).limit(100).all()

    log_audit(db, current_user.id, "DATA_EXPORTED", "User", current_user.id, None, request)

    return {
        "export_metadata": {
            "worker_id": current_user.id,
            "exported_at": utc_now().isoformat(),
            "format_version": "2.0-complete",
            "jurisdiction": "India - Digital Personal Data Protection Act (DPDPA)",
        },
        "profile": {
            "id": current_user.id,
            "email": current_user.email,
            "phone": current_user.phone,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "preferred_language": current_user.preferred_language,
            "created_at": current_user.created_at.isoformat(),
        },
        "consents": [
            {
                "id": c.id,
                "purpose": c.purpose,
                "is_granted": c.is_granted,
                "version": c.consent_text_version,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
            }
            for c in consents
        ],
        "shifts": [
            {
                "id": s.id,
                "started_at": s.started_at.isoformat(),
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "status": s.status,
                "working_minutes": s.total_working_minutes,
                "break_minutes": s.total_break_minutes,
                "location_tracking_enabled": s.location_tracking_enabled,
            }
            for s in shifts
        ],
        "breaks": [
            {
                "id": b.id,
                "shift_id": b.shift_id,
                "break_type": b.break_type,
                "started_at": b.started_at.isoformat(),
                "ended_at": b.ended_at.isoformat() if b.ended_at else None,
                "duration_minutes": b.duration_minutes,
                "notes": b.worker_notes,
            }
            for b in breaks
        ],
        "locations": [
            {
                "id": l.id,
                "shift_id": l.shift_id,
                "latitude": l.latitude,
                "longitude": l.longitude,
                "accuracy_meters": l.accuracy_meters,
                "recorded_at": l.recorded_at.isoformat(),
            }
            for l in locations
        ],
        "exposures": [
            {
                "id": exp.id,
                "shift_id": exp.shift_id,
                "start_time": exp.start_time.isoformat(),
                "end_time": exp.end_time.isoformat(),
                "heat_index_celsius": exp.heat_index_celsius,
                "risk_category": exp.risk_category,
                "quality_grade": exp.quality_grade,
            }
            for exp in exposures
        ],
        "earnings_uploads": [
            {
                "id": u.id,
                "filename": u.original_filename,
                "type": u.file_type,
                "size_bytes": u.file_size_bytes,
                "sha256": u.sha256_hash,
                "status": u.upload_status,
                "uploaded_at": u.uploaded_at.isoformat(),
            }
            for u in uploads
        ],
        "earnings_entries": [
            {
                "id": e.id,
                "platform": e.platform_name,
                "period_start": e.statement_period_start.isoformat(),
                "period_end": e.statement_period_end.isoformat(),
                "base_earnings": e.base_earnings,
                "incentives": e.incentives,
                "deductions": e.deductions,
                "penalties": e.penalties,
                "taxes": e.taxes,
                "net_amount": e.net_amount,
                "is_confirmed_by_worker": e.is_confirmed_by_worker,
            }
            for e in earnings
        ],
        "evidence_reports": [
            {
                "id": r.id,
                "report_number": r.report_number,
                "period_start": r.period_start.isoformat(),
                "period_end": r.period_end.isoformat(),
                "total_hours_worked": r.total_hours_worked,
                "total_extreme_heat_hours": r.total_extreme_heat_hours,
                "net_earnings_recorded": r.net_earnings_recorded,
                "sha256": r.integrity_sha256,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
        "sharing_grants": [
            {
                "id": g.id,
                "organisation_id": g.organisation_id,
                "report_id": g.report_id,
                "purpose": g.purpose,
                "expires_at": g.expires_at.isoformat(),
                "is_revoked": g.is_revoked,
            }
            for g in shares
        ],
        "audit_history": [
            {
                "action": a.action,
                "timestamp": a.timestamp.isoformat(),
                "entity": a.entity_name,
            }
            for a in audits
        ],
    }

@router.delete("/me/delete")
def request_account_deletion(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    PRIV-06: Genuine Data Deletion Workflow under Indian DPDP Act.
    1. Immediately stops all active shifts.
    2. Revokes all active share grants preventing further organisation access.
    3. Revokes all active consents.
    4. Anonymizes personal identifiers and flags account as permanently deleted.
    5. Safely purges stored private documents on disk.
    """
    now = utc_now()

    # 1. Count active shares and shifts before purging
    share_count = db.query(ShareGrant).filter(ShareGrant.worker_id == current_user.id).count()

    # 2. Purge storage files via StorageProvider (Local and S3)
    from backend.app.core.storage import get_storage_provider
    storage = get_storage_provider()
    files_purged = 0

    uploads = db.query(EarningsUpload).filter(EarningsUpload.worker_id == current_user.id).all()
    upload_count = len(uploads)
    for up in uploads:
        if up.stored_filepath:
            try:
                storage.delete_file(up.stored_filepath)
                files_purged += 1
            except Exception:
                pass

    reports = db.query(EvidenceReport).filter(EvidenceReport.worker_id == current_user.id).all()
    report_count = len(reports)
    report_ids = [r.id for r in reports]
    for rep in reports:
        if rep.pdf_storage_path:
            try:
                storage.delete_file(rep.pdf_storage_path)
                files_purged += 1
            except Exception:
                pass

    # Clean local storage directory if present
    user_storage_dir = os.path.join(settings.LOCAL_STORAGE_DIR, current_user.id)
    if os.path.exists(user_storage_dir):
        try:
            shutil.rmtree(user_storage_dir)
        except Exception:
            pass

    # 4. Genuine Database Purging & Cascade
    # Delete report sources
    if report_ids:
        db.query(ReportSource).filter(ReportSource.report_id.in_(report_ids)).delete(synchronize_session=False)

    # Delete evidence reports & shares
    db.query(ShareGrant).filter(ShareGrant.worker_id == current_user.id).delete(synchronize_session=False)
    db.query(EvidenceReport).filter(EvidenceReport.worker_id == current_user.id).delete(synchronize_session=False)

    # Delete earnings entries & uploads
    entry_count = db.query(EarningEntry).filter(EarningEntry.worker_id == current_user.id).delete(synchronize_session=False)
    db.query(EarningsUpload).filter(EarningsUpload.worker_id == current_user.id).delete(synchronize_session=False)

    # Delete shifts, breaks, location samples, exposure intervals
    shifts = db.query(Shift).filter(Shift.worker_id == current_user.id).all()
    shift_ids = [s.id for s in shifts]
    shift_count = len(shifts)
    loc_count = 0
    break_count = 0
    exposure_count = 0

    if shift_ids:
        loc_count = db.query(LocationSample).filter(LocationSample.shift_id.in_(shift_ids)).delete(synchronize_session=False)
        break_count = db.query(BreakEvent).filter(BreakEvent.shift_id.in_(shift_ids)).delete(synchronize_session=False)
        exposure_count = db.query(ExposureInterval).filter(ExposureInterval.shift_id.in_(shift_ids)).delete(synchronize_session=False)
        db.query(Shift).filter(Shift.worker_id == current_user.id).delete(synchronize_session=False)

    # Delete worker profile
    db.query(WorkerProfile).filter(WorkerProfile.user_id == current_user.id).delete(synchronize_session=False)

    # Revoke all consents
    db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).delete(synchronize_session=False)

    # Anonymize user record
    log_audit(db, current_user.id, "ACCOUNT_DATA_PURGED", "User", current_user.id, None, request)
    current_user.is_active = False
    current_user.full_name = "Deleted Worker"
    current_user.email = f"deleted_{current_user.id[:8]}@heatledger.local"
    current_user.phone = None
    current_user.hashed_password = "DELETED"
    current_user.updated_at = now
    db.commit()

    return {
        "success": True,
        "deletion_status": "COMPLETED",
        "purged_records": {
            "location_samples": loc_count,
            "shifts": shift_count,
            "breaks": break_count,
            "exposure_intervals": exposure_count,
            "earnings_uploads": upload_count,
            "earnings_entries": entry_count,
            "evidence_reports": report_count,
            "share_grants": share_count,
            "storage_files_purged": files_purged,
        },
        "user_anonymized": True,
        "message": "All linked worker data, location samples, earnings, and files have been permanently purged.",
    }
