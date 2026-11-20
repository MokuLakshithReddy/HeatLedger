import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.entities import AuditLog, ProcessingJob, User, Organisation, utc_now
from backend.app.providers.weather.service import weather_service
from backend.app.api.deps import get_current_admin, log_audit
from backend.app.schemas.auth import UserRoleUpdate, UserResponse
from backend.app.schemas.organisations import OrganisationResponse

router = APIRouter(prefix="/admin", tags=["System Operations & Audit"])

@router.get("/health")
async def get_system_health(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    # 1. Check PostgreSQL Database
    db_health = "HEALTHY"
    user_count = 0
    org_count = 0
    try:
        user_count = db.query(User).count()
        org_count = db.query(Organisation).count()
    except Exception as e:
        logger.error(f"Health check database query failure: {str(e)}")
        db_health = "UNAVAILABLE"

    # 2. Check Storage Provider
    storage_health = "HEALTHY"
    try:
        from backend.app.core.storage import get_storage_provider
        storage = get_storage_provider()
        if settings.STORAGE_BACKEND == "local":
            if not os.path.exists(settings.LOCAL_STORAGE_DIR):
                os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    except Exception as e:
        logger.error(f"Health check storage verification failure: {str(e)}")
        storage_health = "DEGRADED"

    # 3. Check Weather Providers
    providers_status = await weather_service.get_all_providers_status()
    imd_operational = any(p.get("provider") == "IMD" and p.get("status") == "OPERATIONAL" for p in providers_status)
    era5_configured = bool(settings.CDS_API_KEY)

    # 4. Determine overall system status: HEALTHY, DEGRADED, UNAVAILABLE
    if db_health == "UNAVAILABLE":
        overall_status = "UNAVAILABLE"
    elif storage_health != "HEALTHY" or (settings.ENVIRONMENT == "production" and not imd_operational and not era5_configured):
        overall_status = "DEGRADED"
    else:
        overall_status = "HEALTHY"

    return {
        "system_status": overall_status,
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "components": {
            "database": {
                "status": db_health,
                "total_users": user_count,
                "total_organisations": org_count,
            },
            "storage": {
                "status": storage_health,
                "backend": settings.STORAGE_BACKEND,
            },
            "weather_providers": {
                "imd": "OPERATIONAL" if imd_operational else ("UNCONFIGURED" if not settings.IMD_API_KEY else "DEGRADED"),
                "era5_land": "CONFIGURED" if era5_configured else "UNCONFIGURED",
                "details": providers_status,
            },
            "ai_engine": {
                "status": "CONFIGURED" if settings.GEMINI_API_KEY else "LOCAL_HEURISTICS",
                "model": settings.LLM_MODEL_NAME,
            },
        },
    }

@router.get("/organisations", response_model=List[OrganisationResponse])
def list_all_organisations_for_admin(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """Admin view of all registered organisations, including pending approval status."""
    return db.query(Organisation).order_by(Organisation.created_at.desc()).all()

@router.post("/organisations/{org_id}/approve", response_model=OrganisationResponse)
def approve_organisation(
    org_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """SEC-02: Administrator verifies and approves an organisation to receive worker evidence."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    
    org.is_approved = True
    org.updated_at = utc_now()

    # Activate members and elevate creator to organisation_admin upon approval
    from backend.app.models.entities import OrganisationMember, User
    members = db.query(OrganisationMember).filter(OrganisationMember.organisation_id == org.id).all()
    for m in members:
        m.is_active = True
        if m.role == "admin":
            user = db.query(User).filter(User.id == m.user_id).first()
            if user and user.role == "worker":
                user.role = "organisation_admin"
                db.add(user)
        db.add(m)

    db.commit()
    db.refresh(org)

    log_audit(
        db, current_admin.id, "ORG_APPROVED", "Organisation", org.id,
        {"name": org.name, "slug": org.slug}, request
    )
    return org

@router.post("/organisations/{org_id}/reject", response_model=OrganisationResponse)
def reject_organisation(
    org_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """SEC-02: Administrator rejects or revokes approval for an organisation."""
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    
    org.is_approved = False
    org.updated_at = utc_now()

    from backend.app.models.entities import OrganisationMember
    members = db.query(OrganisationMember).filter(OrganisationMember.organisation_id == org.id).all()
    for m in members:
        m.is_active = False
        db.add(m)

    db.commit()
    db.refresh(org)

    log_audit(
        db, current_admin.id, "ORG_REJECTED", "Organisation", org.id,
        {"name": org.name, "slug": org.slug}, request
    )
    return org

@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: str,
    role_in: UserRoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """SEC-01: Secure administrator-only role provisioning."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_role = target_user.role
    target_user.role = role_in.role
    target_user.updated_at = utc_now()
    db.commit()
    db.refresh(target_user)

    log_audit(
        db, current_admin.id, "USER_ROLE_PROVISIONED", "User", target_user.id,
        {"old_role": old_role, "new_role": target_user.role}, request
    )
    return target_user

@router.get("/audit-logs")
def list_system_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )

@router.get("/jobs")
def list_processing_jobs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    return (
        db.query(ProcessingJob)
        .order_by(ProcessingJob.scheduled_at.desc())
        .limit(limit)
        .all()
    )
