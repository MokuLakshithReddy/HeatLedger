"""Demonstration Data Seeder for HeatLedger (Hyderabad, Telangana)
Creates clearly designated [DEMO / SAMPLE] worker accounts, organisations, shifts,
breaks, climate observations, earnings records, and evidence dossiers.
"""
from datetime import datetime, timezone, timedelta
import os
import hashlib
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.security import get_password_hash
from backend.app.models.entities import (
    User,
    WorkerProfile,
    Organisation,
    OrganisationMember,
    ConsentRecord,
    Shift,
    BreakEvent,
    LocationSample,
    WeatherObservation,
    ExposureInterval,
    EarningsUpload,
    EarningEntry,
    EvidenceReport,
    ReportSource,
    ShareGrant,
    Case,
    CaseNote,
    utc_now,
)
from backend.app.reports.generator import ReportGeneratorService

def seed_demo_data():
    db: Session = SessionLocal()
    try:
        print("🌱 Checking and seeding HeatLedger Hyderabad Demonstration Data...")
        Base.metadata.create_all(bind=engine)

        # 1. Demo Worker
        worker_email = "demo.worker@heatledger.local"
        worker_user = db.query(User).filter(User.email == worker_email).first()
        if not worker_user:
            worker_user = User(
                email=worker_email,
                phone="+919876543210",
                hashed_password=get_password_hash("DemoWorker123!"),
                full_name="Raju K. (Demo Worker)",
                role="worker",
                preferred_language="te", # Telugu default
                is_active=True,
            )
            db.add(worker_user)
            db.commit()
            db.refresh(worker_user)

            worker_profile = WorkerProfile(
                user_id=worker_user.id,
                worker_badge_id="HYD-SWIG-8842",
                primary_platforms=["Swiggy", "Zomato"],
                vehicle_type="motorcycle",
                city="Hyderabad",
                state="Telangana",
                country="India",
                consented_location_tracking=True,
            )
            db.add(worker_profile)

            # Consents
            for purpose in [
                "LOCATION_TRACKING_DURING_SHIFT",
                "EARNINGS_DOCUMENT_EXTRACTION",
                "ORGANISATION_REPORT_SHARING",
            ]:
                db.add(ConsentRecord(
                    user_id=worker_user.id,
                    purpose=purpose,
                    consent_text_version="1.0",
                    is_granted=True,
                    granted_at=utc_now(),
                ))
            db.commit()
            print(f"Created demo worker: {worker_email}")

        # 2. Demo Organisation
        org_slug = "telangana-gig-workers-union"
        org = db.query(Organisation).filter(Organisation.slug == org_slug).first()
        if not org:
            org = Organisation(
                name="Telangana Gig and Platform Workers Union (TGPWU)",
                slug=org_slug,
                description="Worker-led collective advocating for occupational health, social security, and fair heat compensation in Telangana.",
                contact_email="advocacy@tgpwu.org",
                org_type="union",
                is_approved=True,
            )
            db.add(org)
            db.commit()
            db.refresh(org)

            # Org Admin User
            org_user_email = "advocate@telanganaworkers.org"
            org_user = db.query(User).filter(User.email == org_user_email).first()
            if not org_user:
                org_user = User(
                    email=org_user_email,
                    phone="+919844001122",
                    hashed_password=get_password_hash("TelanganaUnion123!"),
                    full_name="Priya V. (Advocacy Lead)",
                    role="organisation_admin",
                    preferred_language="en",
                    is_active=True,
                )
                db.add(org_user)
                db.commit()
                db.refresh(org_user)

                member = OrganisationMember(
                    organisation_id=org.id,
                    user_id=org_user.id,
                    role="admin",
                    is_active=True,
                )
                db.add(member)
                db.commit()
                print(f"Created demo organisation: {org.name}")

        # 3. System Admin User
        admin_email = "admin@heatledger.local"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                email=admin_email,
                hashed_password=get_password_hash("HeatLedgerAdmin2026!"),
                full_name="System Auditor",
                role="system_admin",
                preferred_language="en",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"Created system admin: {admin_email}")

        # 4. Sample Shifts & Breaks in Hyderabad
        existing_shifts = db.query(Shift).filter(Shift.worker_id == worker_user.id).count()
        if existing_shifts == 0:
            now = utc_now()
            # Sample Shift 1: Extreme heat shift yesterday
            shift1_start = now - timedelta(days=1, hours=8)
            shift1_end = now - timedelta(days=1, hours=1)
            shift1 = Shift(
                worker_id=worker_user.id,
                status="COMPLETED",
                started_at=shift1_start,
                ended_at=shift1_end,
                total_working_minutes=375,
                total_break_minutes=45,
                location_tracking_enabled=True,
            )
            db.add(shift1)
            db.commit()
            db.refresh(shift1)

            # Breaks for Shift 1
            break1 = BreakEvent(
                shift_id=shift1.id,
                worker_id=worker_user.id,
                break_type="HYDRATION",
                started_at=shift1_start + timedelta(hours=3),
                ended_at=shift1_start + timedelta(hours=3, minutes=20),
                duration_minutes=20,
                worker_notes="Stopped at shaded water kiosk near Hitec City due to intense dizziness",
                is_worker_declared=True,
            )
            break2 = BreakEvent(
                shift_id=shift1.id,
                worker_id=worker_user.id,
                break_type="REST",
                started_at=shift1_start + timedelta(hours=5),
                ended_at=shift1_start + timedelta(hours=5, minutes=25),
                duration_minutes=25,
                worker_notes="Tree shade rest at Jubilee Hills",
                is_worker_declared=True,
            )
            db.add(break1)
            db.add(break2)

            # Sample Location Samples
            locations = [
                (17.4485, 78.4714, 15.0), # Begumpet
                (17.4401, 78.3489, 12.0), # Gachibowli
                (17.4332, 78.3845, 18.0), # Madhapur
                (17.4256, 78.4112, 14.0), # Jubilee Hills
            ]
            for i, (lat, lon, acc) in enumerate(locations):
                db.add(LocationSample(
                    shift_id=shift1.id,
                    worker_id=worker_user.id,
                    latitude=lat,
                    longitude=lon,
                    accuracy_meters=acc,
                    recorded_at=shift1_start + timedelta(hours=i*1.5),
                    is_valid=True,
                ))

            # Exposure Intervals for Shift 1
            for h in range(7):
                int_start = shift1_start + timedelta(hours=h)
                int_end = int_start + timedelta(hours=1)
                temp = 41.5 if h in [3, 4] else 38.0
                rh = 38.0
                db.add(ExposureInterval(
                    shift_id=shift1.id,
                    worker_id=worker_user.id,
                    start_time=int_start,
                    end_time=int_end,
                    mean_temperature_celsius=temp,
                    mean_relative_humidity_pct=rh,
                    heat_index_celsius=48.2 if temp > 40 else 42.0,
                    risk_category="EXTREME_DANGER" if temp > 40 else "DANGER",
                    wbgt_proxy_celsius=32.4,
                    quality_grade="HIGH",
                    distance_to_source_km=4.2,
                    temporal_offset_minutes=15,
                ))
            db.commit()
            print("Seeded sample shifts and exposure intervals.")

        # 5. Sample Earnings Statement & Entry
        existing_earnings = db.query(EarningsUpload).filter(EarningsUpload.worker_id == worker_user.id).count()
        if existing_earnings == 0:
            mock_upload = EarningsUpload(
                worker_id=worker_user.id,
                original_filename="Swiggy_Weekly_Payout_May2026.pdf",
                stored_filepath="/demo/uploads/swiggy_demo.pdf",
                file_type="pdf",
                file_size_bytes=142850,
                sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                upload_status="CONFIRMED",
                uploaded_at=utc_now() - timedelta(days=2),
            )
            db.add(mock_upload)
            db.commit()
            db.refresh(mock_upload)

            entry = EarningEntry(
                upload_id=mock_upload.id,
                worker_id=worker_user.id,
                platform_name="Swiggy",
                statement_period_start=utc_now() - timedelta(days=7),
                statement_period_end=utc_now() - timedelta(days=1),
                base_earnings=4250.00,
                order_payments=3100.00,
                incentives=850.00,
                bonuses=300.00,
                deductions=150.00,
                penalties=0.00,
                taxes=75.00,
                net_amount=5175.00,
                payment_date=utc_now() - timedelta(days=1),
                extraction_confidence=0.96,
                is_confirmed_by_worker=True,
                worker_confirmed_at=utc_now() - timedelta(days=1),
                worker_adjusted_notes="Verified against bank UPI credit confirmation",
            )
            db.add(entry)
            db.commit()
            print("Seeded sample earnings statement and entry.")

        # 6. Sample Evidence Report & Sharing Grant to Org
        existing_reports = db.query(EvidenceReport).filter(EvidenceReport.worker_id == worker_user.id).count()
        if existing_reports == 0:
            report = ReportGeneratorService.generate_report(
                db,
                worker_user.id,
                utc_now() - timedelta(days=7),
                utc_now(),
            )
            print(f"Generated sample evidence report: {report.report_number} (Hash: {report.integrity_sha256[:16]}...)")

            # Create active share grant to Telangana Gig Workers Union
            grant = ShareGrant(
                worker_id=worker_user.id,
                organisation_id=org.id,
                report_id=report.id,
                purpose="Occupational Heat Stress Compensation Review & Welfare Claim",
                granted_at=utc_now(),
                expires_at=utc_now() + timedelta(days=30),
                is_revoked=False,
                access_count=1,
            )
            db.add(grant)
            db.commit()
            db.refresh(grant)

            # Create sample union case
            case = Case(
                organisation_id=org.id,
                report_id=report.id,
                case_number="CASE-HYD-2026-0001",
                title="Extreme Heatwave Exposure Incident - Hitec City Corridor",
                status="UNDER_REVIEW",
                priority="HIGH",
                worker_pseudonym=f"Worker-{worker_user.id[:6].upper()}",
                created_at=utc_now(),
            )
            db.add(case)
            db.commit()
            db.refresh(case)

            note = CaseNote(
                case_id=case.id,
                author_user_id=org_user.id,
                note_content="Reviewing high heat index period (48.2°C). Worker documented hydration stops. Evidence integrity verified via SHA-256.",
                created_at=utc_now(),
            )
            db.add(note)
            db.commit()
            print("Created shared grant, case record, and caseworker note.")

        print("✅ Demo seeding completed successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
