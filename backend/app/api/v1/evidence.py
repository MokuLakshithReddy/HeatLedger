from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import hashlib

from backend.app.core.database import get_db
from backend.app.models.entities import EvidenceReport, utc_now
from backend.app.schemas.evidence import EvidenceTimelineResponse
from backend.app.schemas.reports import EvidenceReportCreate, EvidenceReportResponse
from backend.app.evidence.correlator import EvidenceCorrelator
from backend.app.reports.generator import ReportGeneratorService
from backend.app.api.deps import get_current_user, get_current_worker, log_audit

router = APIRouter(prefix="/evidence", tags=["Evidence & Reports"])

@router.get("/timeline", response_model=EvidenceTimelineResponse)
@router.get("/timelines", response_model=EvidenceTimelineResponse)
def get_evidence_timeline(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    now = datetime.now(timezone.utc)
    start_dt = start or (now - timedelta(days=7))
    end_dt = end or now
    return EvidenceCorrelator.build_timeline(db, current_worker.id, start_dt, end_dt)

@router.post("/reports", response_model=EvidenceReportResponse)
def generate_evidence_report(
    req: EvidenceReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    report = ReportGeneratorService.generate_report(
        db,
        current_worker.id,
        req.period_start,
        req.period_end,
    )
    log_audit(
        db, current_worker.id, "REPORT_GENERATED", "EvidenceReport", report.id,
        {"report_number": report.report_number, "sha256": report.integrity_sha256}, request
    )
    return report

@router.get("/reports", response_model=List[EvidenceReportResponse])
def list_my_evidence_reports(
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    return (
        db.query(EvidenceReport)
        .filter(EvidenceReport.worker_id == current_worker.id, EvidenceReport.is_deleted == False)
        .order_by(EvidenceReport.created_at.desc())
        .all()
    )

@router.get("/reports/{report_id}", response_model=EvidenceReportResponse)
def get_report_details(
    report_id: str,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    report = (
        db.query(EvidenceReport)
        .filter(EvidenceReport.id == report_id, EvidenceReport.worker_id == current_worker.id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence report not found")
    return report

@router.get("/reports/{report_id}/download")
def download_report_pdf(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_worker = Depends(get_current_worker),
):
    pdf_bytes = ReportGeneratorService.get_report_pdf(db, report_id, worker_id=current_worker.id)
    report = db.query(EvidenceReport).filter(EvidenceReport.id == report_id).first()
    
    log_audit(
        db, current_worker.id, "REPORT_DOWNLOADED", "EvidenceReport", report_id,
        {"sha256": report.integrity_sha256 if report else None}, request
    )

    filename = f"{report.report_number if report else 'HeatLedger-Evidence'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Integrity-SHA256": report.integrity_sha256 if report else "",
        },
    )

@router.get("/reports/{report_id}/verify")
def verify_report_integrity(
    report_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
) -> Dict[str, Any]:
    """EVID-01: Verifies the integrity of a generated report against stored SHA-256 with strict scoped access."""
    report = db.query(EvidenceReport).filter(EvidenceReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Ownership and Scoped Access Enforcement (PRIV-02 & EVID-01)
    is_owner = report.worker_id == current_user.id
    is_admin = current_user.role == "system_admin"
    is_authorized_org = False

    if not is_owner and not is_admin:
        from backend.app.models.entities import ShareGrant, OrganisationMember, Organisation
        now = utc_now()
        active_grant = (
            db.query(ShareGrant)
            .join(OrganisationMember, OrganisationMember.organisation_id == ShareGrant.organisation_id)
            .join(Organisation, Organisation.id == ShareGrant.organisation_id)
            .filter(
                ShareGrant.report_id == report_id,
                OrganisationMember.user_id == current_user.id,
                OrganisationMember.is_active == True,
                Organisation.is_approved == True,
                ShareGrant.is_revoked == False,
                ShareGrant.expires_at > now,
            )
            .first()
        )
        if active_grant:
            is_authorized_org = True

    if not is_owner and not is_admin and not is_authorized_org:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not own this evidence dossier and have no active sharing grant.",
        )
    
    pdf_bytes = ReportGeneratorService.get_report_pdf(db, report_id, worker_id=report.worker_id)
    calculated_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    is_valid = calculated_sha256.lower() == report.integrity_sha256.lower()

    return {
        "report_id": report.id,
        "report_number": report.report_number,
        "is_intact": is_valid,
        "verified": is_valid,
        "sha256": calculated_sha256,
        "stored_sha256": report.integrity_sha256,
        "byte_calculated_sha256": calculated_sha256,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verification_explanation": (
            "Cryptographic SHA-256 integrity match confirms document has not been altered since generation. "
            "Integrity verifies bit-level stability; it does not independently verify external source claims."
        ),
    }

@router.post("/reports/verify-file")
async def verify_uploaded_report_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """EVID-01: Publicly verifiable endpoint to verify any HeatLedger PDF by file upload with strict 10MB bounds."""
    MAX_VERIFY_SIZE = 10 * 1024 * 1024 # 10MB
    contents = await file.read(MAX_VERIFY_SIZE + 1)
    if len(contents) > MAX_VERIFY_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded verification document exceeds maximum allowable limit of 10MB."
        )
    file_sha256 = hashlib.sha256(contents).hexdigest()

    matching_report = (
        db.query(EvidenceReport)
        .filter(EvidenceReport.integrity_sha256 == file_sha256)
        .first()
    )

    if matching_report:
        return {
            "verified": True,
            "report_number": matching_report.report_number,
            "report_id": matching_report.id,
            "created_at": matching_report.created_at.isoformat(),
            "sha256": file_sha256,
            "status": "VALID_AUTHENTIC_HEATLEDGER_DOCUMENT",
        }
    else:
        return {
            "verified": False,
            "sha256": file_sha256,
            "status": "UNRECOGNIZED_OR_ALTERED_DOCUMENT",
            "message": "The uploaded PDF hash does not match any registered HeatLedger evidence report.",
        }
