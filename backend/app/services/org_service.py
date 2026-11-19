from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.models.entities import (
    Organisation,
    OrganisationMember,
    Case,
    CaseNote,
    EvidenceReport,
    ShareGrant,
    Shift,
    ExposureInterval,
    utc_now,
)
from backend.app.schemas.organisations import (
    CaseCreate,
    CaseNoteCreate,
    AggregateCohortAnalytics,
)

class OrgService:
    @staticmethod
    def get_user_organisation_id(db: Session, user_id: str) -> str:
        member = (
            db.query(OrganisationMember)
            .filter(OrganisationMember.user_id == user_id, OrganisationMember.is_active == True)
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not an active member of any approved organisation",
            )
        return member.organisation_id

    @staticmethod
    def get_shared_reports(db: Session, organisation_id: str) -> List[EvidenceReport]:
        now = utc_now()
        active_grants = (
            db.query(ShareGrant)
            .filter(
                ShareGrant.organisation_id == organisation_id,
                ShareGrant.is_revoked == False,
                ShareGrant.expires_at > now,
            )
            .all()
        )
        report_ids = [g.report_id for g in active_grants]
        return db.query(EvidenceReport).filter(EvidenceReport.id.in_(report_ids)).all() if report_ids else []

    @staticmethod
    def create_case(
        db: Session,
        organisation_id: str,
        case_in: CaseCreate,
    ) -> Case:
        # Verify that the report is actively shared with this org
        now = utc_now()
        grant = (
            db.query(ShareGrant)
            .filter(
                ShareGrant.organisation_id == organisation_id,
                ShareGrant.report_id == case_in.report_id,
                ShareGrant.is_revoked == False,
                ShareGrant.expires_at > now,
            )
            .first()
        )
        if not grant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create a case for a report not actively shared with your organisation.",
            )

        # Generate case number and worker pseudonym
        case_count = db.query(Case).filter(Case.organisation_id == organisation_id).count()
        case_number = f"CASE-{datetime.now(timezone.utc).strftime('%Y%m')}-{case_count + 1:04d}"
        pseudonym = f"Worker-{grant.worker_id[:6].upper()}"

        new_case = Case(
            organisation_id=organisation_id,
            report_id=case_in.report_id,
            case_number=case_number,
            title=case_in.title,
            priority=case_in.priority,
            status="OPEN",
            worker_pseudonym=pseudonym,
            created_at=utc_now(),
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        return new_case

    @staticmethod
    def add_case_note(
        db: Session,
        case_id: str,
        user_id: str,
        organisation_id: str,
        note_in: CaseNoteCreate,
    ) -> CaseNote:
        case = (
            db.query(Case)
            .filter(Case.id == case_id, Case.organisation_id == organisation_id)
            .first()
        )
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case record not found")

        note = CaseNote(
            case_id=case_id,
            author_user_id=user_id,
            note_content=note_in.note_content,
            created_at=utc_now(),
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def get_cohort_analytics(
        db: Session,
        organisation_id: str,
        cohort_name: str = "Hyderabad Gig Delivery Cohort",
    ) -> AggregateCohortAnalytics:
        # Minimum cohort safeguard (k-anonymity >= 5)
        k_min = settings.MINIMUM_COHORT_SIZE
        
        # Get count of distinct workers who shared active reports with this org
        now = utc_now()
        active_worker_ids = [
            row[0] for row in (
                db.query(ShareGrant.worker_id)
                .filter(
                    ShareGrant.organisation_id == organisation_id,
                    ShareGrant.is_revoked == False,
                    ShareGrant.expires_at > now,
                )
                .distinct()
                .all()
            )
        ]
        cohort_size = len(active_worker_ids)

        if cohort_size < k_min:
            # Privacy safeguard triggered: suppress granular analytics
            return AggregateCohortAnalytics(
                cohort_name=cohort_name,
                total_workers_in_cohort=cohort_size,
                meets_k_anonymity_threshold=False,
                k_threshold=k_min,
                average_heat_exposure_hours=None,
                average_shift_duration_hours=None,
                total_cases_filed=db.query(Case).filter(Case.organisation_id == organisation_id).count(),
                common_high_heat_time_bands=[],
                anonymity_notice=(
                    f"COHORT PRIVACY SAFEGUARD ACTIVE: Minimum cohort size of {k_min} distinct consented workers is required "
                    f"to prevent re-identification. Currently {cohort_size} worker(s) in cohort; individual metrics suppressed."
                ),
            )

        # If cohort meets k-anonymity threshold, compute aggregates safely
        reports = (
            db.query(EvidenceReport)
            .filter(EvidenceReport.worker_id.in_(active_worker_ids))
            .all()
        )
        avg_heat = (
            sum(r.total_extreme_heat_hours for r in reports) / len(reports)
            if reports else 0.0
        )
        avg_shift = (
            sum(r.total_hours_worked for r in reports) / len(reports)
            if reports else 0.0
        )

        return AggregateCohortAnalytics(
            cohort_name=cohort_name,
            total_workers_in_cohort=cohort_size,
            meets_k_anonymity_threshold=True,
            k_threshold=k_min,
            average_heat_exposure_hours=round(avg_heat, 1),
            average_shift_duration_hours=round(avg_shift, 1),
            total_cases_filed=db.query(Case).filter(Case.organisation_id == organisation_id).count(),
            common_high_heat_time_bands=["13:00 - 16:30 IST (Peak Solar/HI Danger)"],
            anonymity_notice="Privacy criteria satisfied: Aggregate metrics calculated with k-anonymity safeguards.",
        )
