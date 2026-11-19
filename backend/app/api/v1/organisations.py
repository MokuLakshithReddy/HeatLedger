from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.core.database import get_db
from backend.app.models.entities import Organisation, Case, CaseNote, EvidenceReport
from backend.app.schemas.organisations import (
    OrganisationCreate,
    OrganisationResponse,
    CaseCreate,
    CaseResponse,
    CaseNoteCreate,
    CaseNoteResponse,
    AggregateCohortAnalytics,
)
from backend.app.schemas.reports import EvidenceReportResponse
from backend.app.services.org_service import OrgService
from backend.app.services.share_service import ShareService
from backend.app.reports.generator import ReportGeneratorService
from backend.app.api.deps import get_current_user, get_current_org_member, log_audit

router = APIRouter(prefix="/organisations", tags=["Organisations & Advocacy"])

@router.get("", response_model=List[OrganisationResponse])
def list_organisations(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return db.query(Organisation).filter(Organisation.is_approved == True).all()

@router.post("", response_model=OrganisationResponse)
def register_organisation(
    org_in: OrganisationCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    existing = db.query(Organisation).filter(Organisation.slug == org_in.slug).first()
    if existing:
        raise HTTPException(status_code=409, detail="Organisation slug already exists")
    
    org = Organisation(
        name=org_in.name,
        slug=org_in.slug,
        contact_email=org_in.contact_email,
        description=org_in.description,
        org_type=org_in.org_type,
        is_approved=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Creator becomes initial OrganisationMember admin
    from backend.app.models.entities import OrganisationMember
    member = OrganisationMember(
        organisation_id=org.id,
        user_id=current_user.id,
        role="admin",
        is_active=True,
    )
    db.add(member)
    db.commit()
    return org

@router.get("/{org_id}/reports", response_model=List[EvidenceReportResponse])
def list_shared_reports_for_org(
    org_id: str,
    db: Session = Depends(get_db),
    current_org_user = Depends(get_current_org_member),
):
    # Verify user belongs to this org
    user_org_id = OrgService.get_user_organisation_id(db, current_org_user.id)
    if user_org_id != org_id and current_org_user.role != "system_admin":
        raise HTTPException(status_code=403, detail="Forbidden: You can only view reports for your own organisation.")
    return OrgService.get_shared_reports(db, org_id)

@router.get("/{org_id}/reports/{report_id}/download")
def download_shared_report_for_org(
    org_id: str,
    report_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_org_user = Depends(get_current_org_member),
):
    # Verify user belongs to org
    user_org_id = OrgService.get_user_organisation_id(db, current_org_user.id)
    if user_org_id != org_id and current_org_user.role != "system_admin":
        raise HTTPException(status_code=403, detail="Forbidden: You can only access reports for your own organisation.")

    # Strictly verify active share grant exists
    grant = ShareService.verify_org_access_to_report(db, org_id, report_id)

    pdf_bytes = ReportGeneratorService.get_report_pdf(db, report_id)
    report = db.query(EvidenceReport).filter(EvidenceReport.id == report_id).first()

    log_audit(
        db, current_org_user.id, "ORG_REPORT_DOWNLOADED", "EvidenceReport", report_id,
        {"organisation_id": org_id, "share_grant_id": grant.id}, request
    )

    filename = f"{report.report_number if report else 'Shared-Evidence'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Integrity-SHA256": report.integrity_sha256 if report else "",
        },
    )

@router.get("/{org_id}/cases", response_model=List[CaseResponse])
def list_organisation_cases(
    org_id: str,
    db: Session = Depends(get_db),
    current_org_user = Depends(get_current_org_member),
):
    user_org_id = OrgService.get_user_organisation_id(db, current_org_user.id)
    if user_org_id != org_id and current_org_user.role != "system_admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return db.query(Case).filter(Case.organisation_id == org_id).all()

@router.post("/{org_id}/cases", response_model=CaseResponse)
def create_case(
    org_id: str,
    case_in: CaseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_org_user = Depends(get_current_org_member),
):
    user_org_id = OrgService.get_user_organisation_id(db, current_org_user.id)
    if user_org_id != org_id and current_org_user.role != "system_admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    new_case = OrgService.create_case(db, org_id, case_in)
    log_audit(db, current_org_user.id, "CASE_CREATED", "Case", new_case.id, {"case_number": new_case.case_number}, request)
    return new_case

@router.post("/{org_id}/cases/{case_id}/notes", response_model=CaseNoteResponse)
def add_case_note(
    org_id: str,
    case_id: str,
    note_in: CaseNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_org_user = Depends(get_current_org_member),
):
    user_org_id = OrgService.get_user_organisation_id(db, current_org_user.id)
    if user_org_id != org_id and current_org_user.role != "system_admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    note = OrgService.add_case_note(db, case_id, current_org_user.id, org_id, note_in)
    log_audit(db, current_org_user.id, "CASE_NOTE_ADDED", "CaseNote", note.id, {"case_id": case_id}, request)
    return note

@router.get("/{org_id}/analytics", response_model=AggregateCohortAnalytics)
def get_cohort_analytics(
    org_id: str,
    db: Session = Depends(get_db),
    current_org_user = Depends(get_current_org_member),
):
    user_org_id = OrgService.get_user_organisation_id(db, current_org_user.id)
    if user_org_id != org_id and current_org_user.role != "system_admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return OrgService.get_cohort_analytics(db, org_id)
