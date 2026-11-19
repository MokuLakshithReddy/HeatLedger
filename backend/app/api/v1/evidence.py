from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from backend.app.core.database import get_db
from backend.app.models.entities import EvidenceReport
from backend.app.schemas.evidence import EvidenceTimelineResponse
from backend.app.schemas.reports import EvidenceReportCreate, EvidenceReportResponse
from backend.app.evidence.correlator import EvidenceCorrelator
from backend.app.reports.generator import ReportGeneratorService
from backend.app.api.deps import get_current_user, get_current_worker, log_audit

router = APIRouter(prefix="/evidence", tags=["Evidence & Reports"])

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
