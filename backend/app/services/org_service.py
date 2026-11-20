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
                detail="User is not an active member of any organisation",
            )
        
        # Verify organisation is approved
        org = db.query(Organisation).filter(Organisation.id == member.organisation_id).first()
        if not org or not org.is_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organisation is pending administrative verification and approval. Access to worker data is restricted.",
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
                detail="Cannot create case: No active, non-revoked worker share grant exists for this report",
            )

        report = db.query(EvidenceReport).filter(EvidenceReport.id == case_in.report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Referenced report not found")

        case_count = db.query(Case).filter(Case.organisation_id == organisation_id).count()
        case_number = f"CASE-{datetime.now(timezone.utc).strftime('%Y%m')}-{case_count + 1:04d}"

        # Pseudonymize worker identifier for union record handling
        worker_pseudonym = f"Worker-{report.worker_id[:8]}"

        new_case = Case(
            organisation_id=organisation_id,
            report_id=case_in.report_id,
            worker_pseudonym=worker_pseudonym,
            case_number=case_number,
            title=case_in.title,
            status="OPEN",
            priority=case_in.priority or "MEDIUM",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        return new_case

    @staticmethod
    def add_case_note(
        db: Session,
        case_id: str,
        author_user_id: str,
        organisation_id: str,
        note_in: CaseNoteCreate,
    ) -> CaseNote:
        case = db.query(Case).filter(Case.id == case_id, Case.organisation_id == organisation_id).first()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found in your organisation")

        note = CaseNote(
            case_id=case_id,
            author_user_id=author_user_id,
            note_content=note_in.note_content,
            created_at=utc_now(),
            updated_at=utc_now(),
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
        active_grants = (
            db.query(ShareGrant)
            .filter(
                ShareGrant.organisation_id == organisation_id,
                ShareGrant.is_revoked == False,
                ShareGrant.expires_at > now,
            )
            .all()
        )
        active_worker_ids = list(set(g.worker_id for g in active_grants))
        shared_report_ids = list(set(g.report_id for g in active_grants))
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

        # PRIV-02: Strictly query ONLY reports that have been explicitly shared with this organisation!
        # Never query unshared reports of active workers.
        if not shared_report_ids:
            return AggregateCohortAnalytics(
                cohort_name=cohort_name,
                total_workers_in_cohort=cohort_size,
                meets_k_anonymity_threshold=True,
                k_threshold=k_min,
                average_heat_exposure_hours=0.0,
                average_shift_duration_hours=0.0,
                total_cases_filed=db.query(Case).filter(Case.organisation_id == organisation_id).count(),
                common_high_heat_time_bands=["13:00 - 16:30 IST (Peak Solar/HI Danger)"],
                anonymity_notice="Privacy criteria satisfied: Aggregate metrics calculated from explicitly shared reports only.",
            )

        reports = (
            db.query(EvidenceReport)
            .filter(EvidenceReport.id.in_(shared_report_ids))
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

        # Derive common high-heat time bands strictly from authorized report shifts/intervals
        time_bands = []
        if shared_report_ids:
            from backend.app.models.entities import ReportSource, ExposureInterval
            from collections import Counter

            authorized_shift_sources = (
                db.query(ReportSource.source_id)
                .filter(
                    ReportSource.report_id.in_(shared_report_ids),
                    ReportSource.source_type == "SHIFT",
                )
                .all()
            )
            authorized_shift_ids = [s[0] for s in authorized_shift_sources]

            if authorized_shift_ids:
                intervals = (
                    db.query(ExposureInterval)
                    .filter(
                        ExposureInterval.shift_id.in_(authorized_shift_ids),
                        ExposureInterval.risk_category.in_(["DANGER", "EXTREME_DANGER"]),
                    )
                    .all()
                )
                hour_counts = Counter()
                for inv in intervals:
                    # Convert UTC to IST (+5:30)
                    ist_hour = (inv.start_time.hour + 5 + (1 if inv.start_time.minute >= 30 else 0)) % 24
                    bucket_start = (ist_hour // 2) * 2
                    hour_counts[bucket_start] += 1

                for bucket, count in hour_counts.most_common(3):
                    time_bands.append(f"{bucket:02d}:00 - {bucket+2:02d}:00 IST ({count} severe heat intervals)")

        if not time_bands:
            time_bands = ["No severe heat intervals recorded in authorized cohort shifts"]

        return AggregateCohortAnalytics(
            cohort_name=cohort_name,
            total_workers_in_cohort=cohort_size,
            meets_k_anonymity_threshold=True,
            k_threshold=k_min,
            average_heat_exposure_hours=round(avg_heat, 1),
            average_shift_duration_hours=round(avg_shift, 1),
            total_cases_filed=db.query(Case).filter(Case.organisation_id == organisation_id).count(),
            common_high_heat_time_bands=time_bands,
            anonymity_notice="Privacy criteria satisfied: Aggregate metrics calculated with k-anonymity safeguards from authorized shared reports.",
        )
