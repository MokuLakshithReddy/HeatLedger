from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.entities import AuditLog, ProcessingJob, User, Organisation
from backend.app.providers.weather.service import weather_service
from backend.app.api.deps import get_current_admin

router = APIRouter(prefix="/admin", tags=["System Operations & Audit"])

@router.get("/health")
async def get_system_health(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    # Check DB
    try:
        user_count = db.query(User).count()
        db_status = "CONNECTED"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
        user_count = 0

    providers_status = await weather_service.get_all_providers_status()

    return {
        "system_status": "HEALTHY",
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "database": {
            "status": db_status,
            "total_users": user_count,
            "total_organisations": db.query(Organisation).count(),
        },
        "storage": {
            "backend": settings.STORAGE_BACKEND,
            "local_dir": settings.LOCAL_STORAGE_DIR,
        },
        "ai_provider": {
            "configured_model": settings.LLM_MODEL_NAME,
            "has_gemini_key": bool(settings.GEMINI_API_KEY),
        },
        "weather_providers": providers_status,
    }

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
