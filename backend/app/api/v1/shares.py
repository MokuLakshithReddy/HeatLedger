from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from backend.app.core.database import get_db
from backend.app.schemas.shares import ShareGrantCreate, ShareGrantResponse, ShareRevokeRequest
from backend.app.services.share_service import ShareService
from backend.app.api.deps import get_current_worker, log_audit

router = APIRouter(prefix="/shares", tags=["Data Sharing"])

@router.post("", response_model=ShareGrantResponse)
def create_share_grant(
    req: ShareGrantCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    grant = ShareService.create_share_grant(db, current_worker.id, req)
    log_audit(
        db, current_worker.id, "REPORT_SHARE_GRANTED", "ShareGrant", grant.id,
        {"organisation_id": grant.organisation_id, "report_id": grant.report_id, "purpose": grant.purpose},
        request
    )
    return grant

@router.get("", response_model=List[ShareGrantResponse])
def list_my_shares(
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return ShareService.get_worker_shares(db, current_worker.id)

@router.post("/{share_id}/revoke", response_model=ShareGrantResponse)
def revoke_share(
    share_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    grant = ShareService.revoke_share_grant(db, share_id, current_worker.id)
    log_audit(
        db, current_worker.id, "REPORT_SHARE_REVOKED", "ShareGrant", grant.id,
        {"organisation_id": grant.organisation_id, "report_id": grant.report_id}, request
    )
    return grant
