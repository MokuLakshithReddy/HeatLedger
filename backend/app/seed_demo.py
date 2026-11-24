"""Demonstration Data Seeder for HeatLedger (Hyderabad, Telangana)
Creates clearly designated [DEMO / SAMPLE] worker accounts, organisations, shifts,
breaks, climate observations, earnings records, and evidence dossiers.
SEC-03: Strictly restricted to non-production environments with explicit fictional labeling.
"""
from datetime import datetime, timezone, timedelta
import os
import hashlib
from sqlalchemy.orm import Session

from backend.app.core.config import settings
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
    if settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError("CRITICAL: Seeding demonstration data is strictly prohibited in production environments.")

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
                full_name="Raju K. (DEMO / Sample Worker)",
                role="worker",
                preferred_language="te", # Telugu default
                is_active=True,
            )
            db.add(worker_user)
            db.commit()
            db.refresh(worker_user)

            worker_profile = WorkerProfile(
                user_id=worker_user.id,
                worker_badge_id="SAMPLE-HYD-SWIG-8842",
                primary_platforms=["Swiggy", "Zomato"],
                vehicle_type="two_wheeler",
                city="Hyderabad",
                consented_location_tracking=True,
            )
            db.add(worker_profile)

            # Consents
            for purpose in ["location_tracking", "earnings_processing", "organisation_sharing"]:
                db.add(ConsentRecord(
                    user_id=worker_user.id,
                    purpose=purpose,
                    is_granted=True,
                    consent_text_version="v1.0-demo",
                    granted_at=utc_now(),
                ))
            db.commit()
            print(f"Created demo worker: {worker_email}")

        # 2. Demo Organisation (SEC-03: explicitly labeled demonstration entity for Hyderabad pilot)
        org_slug = "tgpwu-telangana"
        org = db.query(Organisation).filter(
            (Organisation.slug == org_slug) | (Organisation.slug == "demo-hyderabad-gig-workers-collective")
        ).first()
        if not org:
            org = Organisation(
                name="Telangana Gig & Platform Workers Union (TGPWU)",
                slug=org_slug,
                description="[DEMO ALLIANCE] Telangana Gig and Platform Workers Union representing gig delivery workers for platform testing and evidence evaluation.",
                contact_email="advocate@telanganaworkers.org",
                org_type="union",
                is_approved=True, # Approved specifically for local demonstration
            )
            db.add(org)
            db.commit()
            db.refresh(org)

        # 2.1 Primary Documented Org Admin User
        primary_org_email = "advocate@telanganaworkers.org"
        org_user = db.query(User).filter(User.email == primary_org_email).first()
        if not org_user:
            org_user = User(
                email=primary_org_email,
                phone="+919844001122",
                hashed_password=get_password_hash("TelanganaUnion123!"),
                full_name="Priya V. (TGPWU Union Lead)",
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
            print(f"Created demo organisation admin: {primary_org_email}")

        # 2.2 Optional legacy alias for backward compatibility
        legacy_org_email = "advocate@demoworkers.local"
        legacy_user = db.query(User).filter(User.email == legacy_org_email).first()
        if not legacy_user:
            legacy_user = User(
                email=legacy_org_email,
                phone="+919844001123",
                hashed_password=get_password_hash("DemoAdvocate123!"),
                full_name="Priya V. (DEMO Alias)",
                role="organisation_admin",
                preferred_language="en",
                is_active=True,
            )
            db.add(legacy_user)
            db.commit()
            db.refresh(legacy_user)

            db.add(OrganisationMember(
                organisation_id=org.id,
                user_id=legacy_user.id,
                role="admin",
                is_active=True,
            ))
            db.commit()

        # 3. System Admin User
        admin_email = "admin@heatledger.local"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                email=admin_email,
                phone="+919000000001",
                hashed_password=get_password_hash("HeatLedgerAdmin2026!"),
                full_name="System Administrator (DEMO)",
                role="system_admin",
                preferred_language="en",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"Created system admin: {admin_email}")

        # 4. Shifts and Breaks
        now = utc_now()
        existing_shift = db.query(Shift).filter(Shift.worker_id == worker_user.id).first()
        if not existing_shift:
            # Shift 1: Completed high-heat shift yesterday
            shift1_start = now - timedelta(days=1, hours=8)
            shift1_end = now - timedelta(days=1, hours=1)
            shift1 = Shift(
                worker_id=worker_user.id,
                started_at=shift1_start,
                ended_at=shift1_end,
                status="COMPLETED",
                location_tracking_enabled=True,
                total_working_minutes=375, # 7 hrs total - 45 min break
                total_break_minutes=45,
            )
            db.add(shift1)
            db.commit()
            db.refresh(shift1)

            # Break event
            break1 = BreakEvent(
                shift_id=shift1.id,
                worker_id=worker_user.id,
                break_type="HYDRATION_HEAT",
                started_at=shift1_start + timedelta(hours=3),
                ended_at=shift1_start + timedelta(hours=3, minutes=45),
                duration_minutes=45,
                notes="Rest at shaded bus shelter near Hitec City. Extreme heat peak.",
            )
            db.add(break1)

            # Location Samples (Hyderabad route: Begumpet -> Madhapur -> Hitec City -> Gachibowli)
            coords = [
                (17.4447, 78.4664, 15.0), # Begumpet
                (17.4483, 78.3915, 12.0), # Madhapur
                (17.4504, 78.3808, 8.5),  # Hitec City
                (17.4401, 78.3489, 10.0), # Gachibowli
            ]
            for idx, (lat, lon, acc) in enumerate(coords):
                db.add(LocationSample(
                    shift_id=shift1.id,
                    worker_id=worker_user.id,
                    latitude=lat,
                    longitude=lon,
                    accuracy_meters=acc,
                    recorded_at=shift1_start + timedelta(hours=idx * 2),
                    provider_source="gps_foreground_service",
                ))

            # Weather Observations & Exposure
            obs_times = [
                (shift1_start, 38.5, 45.0, 48.2, "DANGER"),
                (shift1_start + timedelta(hours=2), 41.2, 38.0, 52.8, "EXTREME_DANGER"),
                (shift1_start + timedelta(hours=4), 42.0, 35.0, 53.5, "EXTREME_DANGER"),
                (shift1_start + timedelta(hours=6), 39.0, 40.0, 49.5, "DANGER"),
            ]
            for obs_time, temp, rh, hi, risk in obs_times:
                w_obs = WeatherObservation(
                    provider_name="IMD",
                    source_identifier="HYD_BEGUMPET_AWS_43128",
                    latitude=17.4447,
                    longitude=78.4664,
                    spatial_resolution_km=10.0,
                    observed_at=obs_time,
                    temperature_celsius=temp,
                    relative_humidity_pct=rh,
                    heat_index_celsius=hi,
                    wbgt_estimated_celsius=round(0.7 * (temp * 0.8) + 0.3 * temp, 1),
                    wind_speed_mps=3.2,
                    confidence_score=0.95,
                    data_freshness_status="REALTIME",
                    validation_status="VALIDATED",
                )
                db.add(w_obs)
                db.commit()
                db.refresh(w_obs)

                db.add(ExposureInterval(
                    shift_id=shift1.id,
                    weather_observation_id=w_obs.id,
                    interval_start=obs_time,
                    interval_end=obs_time + timedelta(hours=1),
                    duration_minutes=60,
                    temperature_celsius=temp,
                    relative_humidity_pct=rh,
                    heat_index_celsius=hi,
                    risk_category=risk,
                    spatio_temporal_precision="HIGH",
                    source_attribution=f"IMD Begumpet Station (43128). Lat: {w_obs.latitude}, Lon: {w_obs.longitude}",
                ))
            db.commit()
            print("Seeded demo shift, breaks, locations, and weather observations.")

        # 5. Earnings entries
        existing_earnings = db.query(EarningEntry).filter(EarningEntry.worker_id == worker_user.id).first()
        if not existing_earnings:
            period_start = now - timedelta(days=7)
            upload = EarningsUpload(
                worker_id=worker_user.id,
                original_filename="Swiggy_Weekly_Payout_May2026_SAMPLE.pdf",
                stored_file_path=f"demo/{worker_user.id}/Swiggy_SAMPLE.pdf",
                file_size_bytes=425120,
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                file_type="pdf",
                processing_status="EXTRACTED",
                has_document_consent=True,
            )
            db.add(upload)
            db.commit()
            db.refresh(upload)

            entry = EarningEntry(
                upload_id=upload.id,
                worker_id=worker_user.id,
                platform_name="Swiggy",
                statement_period_start=period_start,
                statement_period_end=now,
                base_earnings=4520.0,
                order_payments=1200.0,
                incentives=850.0,
                bonuses=200.0,
                deductions=150.0,
                penalties=100.0,
                taxes=75.0,
                net_amount=6445.0,
                is_confirmed_by_worker=True,
                worker_confirmed_at=utc_now(),
                confidence_score=0.92,
                source_attribution_notes="[SAMPLE] Extracted from Swiggy Weekly Statement with worker confirmation.",
            )
            db.add(entry)
            db.commit()
            print("Seeded demo earnings upload and verified entry.")

        # 6. Generate Demo Evidence Report
        existing_report = db.query(EvidenceReport).filter(EvidenceReport.worker_id == worker_user.id).first()
        if not existing_report:
            start_window = now - timedelta(days=7)
            end_window = now
            report = ReportGeneratorService.generate_report(
                db, worker_user.id, start_window, end_window
            )
            print(f"Generated demo evidence report: {report.report_number} (Hash: {report.integrity_sha256[:16]}...)")

            # 7. Share Report with Demo Organisation
            grant = ShareGrant(
                report_id=report.id,
                worker_id=worker_user.id,
                organisation_id=org.id,
                purpose="heat_hardship_claim",
                expires_at=utc_now() + timedelta(days=30),
                is_revoked=False,
            )
            db.add(grant)
            db.commit()

            # Create Case for Union
            db.add(Case(
                organisation_id=org.id,
                report_id=report.id,
                worker_pseudonym=f"Worker-{worker_user.id[:8]}",
                case_number="CASE-202605-0001",
                title="Hyderabad May Heatwave Claim — Prolonged Level 4 Heat Index Exposure",
                description="Worker documented 4+ hours in extreme heat (>52°C Heat Index) during peak hours in Hyderabad.",
                status="UNDER_REVIEW",
                priority="HIGH",
            ))
            db.commit()
            print("Created shared case with demo organisation.")

        print(" Demonstration Data Seeding Completed Successfully.")
    except Exception as e:
        db.rollback()
        print(f" Seeding Error: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
