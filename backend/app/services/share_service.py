from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.models.entities import ShareGrant, EvidenceReport, Organisation, utc_now
from backend.app.schemas.shares import ShareGrantCreate

class ShareService:
    @staticmethod
    def create_share_grant(
        db: Session,
        worker_id: str,
        grant_in: ShareGrantCreate,
    ) -> ShareGrant:
        # 1. Verify report belongs to worker
        report = (
            db.query(EvidenceReport)
            .filter(EvidenceReport.id == grant_in.report_id, EvidenceReport.worker_id == worker_id)
            .first()
        )
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence report not found")

        # 2. Verify organisation exists and is approved
        org = (
            db.query(Organisation)
            .filter(Organisation.id == grant_in.organisation_id, Organisation.is_approved == True)
            .first()
        )
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found or not approved")

        now = utc_now()
        expires_at = now + timedelta(days=grant_in.duration_days)

        grant = ShareGrant(
            worker_id=worker_id,
            organisation_id=grant_in.organisation_id,
            report_id=grant_in.report_id,
            purpose=grant_in.purpose,
            granted_at=now,
            expires_at=expires_at,
            is_revoked=False,
            revoked_at=None,
            access_count=0,
        )
        db.add(grant)
        db.commit()
        db.refresh(grant)
        return grant

    @staticmethod
    def revoke_share_grant(
        db: Session,
        share_id: str,
        worker_id: str,
    ) -> ShareGrant:
        grant = (
            db.query(ShareGrant)
            .filter(ShareGrant.id == share_id, ShareGrant.worker_id == worker_id)
            .first()
        )
        if not grant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share grant not found")
        
        grant.is_revoked = True
        grant.revoked_at = utc_now()
        db.commit()
        db.refresh(grant)
        return grant

    @staticmethod
    def verify_org_access_to_report(
        db: Session,
        organisation_id: str,
        report_id: str,
    ) -> ShareGrant:
        now = utc_now()
        grant = (
            db.query(ShareGrant)
            .filter(
                ShareGrant.organisation_id == organisation_id,
                ShareGrant.report_id == report_id,
                ShareGrant.is_revoked == False,
                ShareGrant.expires_at > now,
            )
            .first()
        )
        if not grant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No active, unrevoked sharing grant exists for this organisation and report.",
            )
        grant.access_count += 1
        db.commit()
        return grant

    @staticmethod
    def get_worker_shares(db: Session, worker_id: str) -> List[ShareGrant]:
        return db.query(ShareGrant).filter(ShareGrant.worker_id == worker_id).all()
