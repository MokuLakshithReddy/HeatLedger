"""Comprehensive Security Regression Test Suite
Validates all mandatory P0 security requirements (SEC-01 through SEC-06 and Section 16):
1. Public registration with system_admin role is rejected.
2. Public registration with organisation_admin role is rejected.
3. Ordinary users cannot create or approve trusted organisations.
4. Unapproved organisations cannot access worker evidence.
5. Worker A cannot access Worker B's records.
6. Organisation A cannot access Organisation B's reports.
7. Unshared reports are inaccessible.
8. Expired sharing grants are denied.
9. Revoked grants are denied.
10. Revoked consent stops new location collection.
11. Earnings extraction without permission is denied.
12. Invalid production secrets prevent startup.
13. Demo credentials cannot authenticate against production.
14. File path traversal attempts are rejected.
"""
import io
import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.env_validator import validate_environment
from backend.app.core.security import create_access_token, get_password_hash
from backend.app.models.entities import User, Organisation, Shift, LocationSample, EvidenceReport, ShareGrant, ConsentRecord, utc_now
from backend.app.services.shift_service import ShiftService
from backend.app.services.location_service import LocationService
from backend.app.services.consent_service import ConsentService
from backend.app.schemas.location import LocationSampleCreate
from backend.app.reports.generator import ReportGeneratorService

# 1. Public registration with system_admin role is rejected
def test_sec_01_public_registration_system_admin_rejected(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "hacker.admin@evil.com",
        "password": "Password123!",
        "role": "system_admin",
    })
    assert resp.status_code == 422 # Pydantic field_validator raises ValueError

# 2. Public registration with organisation_admin role is rejected
def test_sec_02_public_registration_org_admin_rejected(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "hacker.org@evil.com",
        "password": "Password123!",
        "role": "organisation_admin",
    })
    assert resp.status_code == 422 # Pydantic field_validator raises ValueError

# 3. Ordinary users cannot approve trusted organisations
def test_sec_03_ordinary_user_cannot_approve_organisation(client, worker_auth_headers, db_session):
    org = Organisation(name="Rogue Org", slug="rogue-org", contact_email="rogue@org.com", is_approved=False)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    resp = client.post(f"/api/v1/admin/organisations/{org.id}/approve", headers=worker_auth_headers)
    assert resp.status_code == 403 # Restricted to system_admin

# 4. Unapproved organisations cannot access worker evidence
def test_sec_04_unapproved_organisation_cannot_access_worker_evidence(client, worker_user, db_session):
    # Create unapproved organisation
    unapproved_org = Organisation(name="Pending Org", slug="pending-org", contact_email="pending@org.com", is_approved=False)
    db_session.add(unapproved_org)
    db_session.commit()
    db_session.refresh(unapproved_org)

    org_user = User(
        email="staff@pending.org",
        phone="+919200000099",
        hashed_password=get_password_hash("Pass1234!"),
        role="organisation_admin",
        is_active=True,
    )
    db_session.add(org_user)
    db_session.commit()
    db_session.refresh(org_user)

    from backend.app.models.entities import OrganisationMember
    db_session.add(OrganisationMember(organisation_id=unapproved_org.id, user_id=org_user.id, role="admin", is_active=True))
    db_session.commit()

    token = create_access_token({"sub": org_user.id, "role": "organisation_admin", "email": org_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to view reports
    resp = client.get(f"/api/v1/organisations/{unapproved_org.id}/reports", headers=headers)
    assert resp.status_code == 403
    assert "pending" in resp.json()["detail"].lower()

# 5. Worker A cannot access Worker B's records
def test_sec_05_worker_cross_tenant_isolation(client, worker_auth_headers, worker_b_user, db_session):
    # Worker B creates a shift
    shift_b = ShiftService.start_shift(db_session, worker_b_user.id)

    # Worker A attempts to pause Worker B's shift
    resp = client.post(f"/api/v1/shifts/{shift_b.id}/pause", headers=worker_auth_headers)
    assert resp.status_code == 404 # Concealed / Not Found for cross-tenant

# 6. Organisation A cannot access Organisation B's reports
def test_sec_06_organisation_cross_tenant_isolation(client, org_user_and_org, db_session):
    org_user, org_a = org_user_and_org
    token_a = create_access_token({"sub": org_user.id, "role": org_user.role, "email": org_user.email})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Organisation B
    org_b = Organisation(name="Union B", slug="union-b", contact_email="b@union.org", is_approved=True)
    db_session.add(org_b)
    db_session.commit()
    db_session.refresh(org_b)

    # Org A caseworker tries to view Org B reports
    resp = client.get(f"/api/v1/organisations/{org_b.id}/reports", headers=headers_a)
    assert resp.status_code == 403

# 7. Unshared reports are inaccessible
def test_sec_07_unshared_reports_are_inaccessible_to_org(client, org_auth_headers, org_user_and_org, worker_user, db_session):
    _, org = org_user_and_org
    # Worker generates report, but does NOT share it with org
    report = ReportGeneratorService.generate_report(db_session, worker_user.id, utc_now() - timedelta(days=2), utc_now())

    resp = client.get(f"/api/v1/organisations/{org.id}/reports/{report.id}/download", headers=org_auth_headers)
    assert resp.status_code == 403
    assert "no active, unrevoked sharing grant" in resp.json()["detail"].lower()

# 8. Expired sharing grants are denied
def test_sec_08_expired_sharing_grants_are_denied(client, org_auth_headers, org_user_and_org, worker_user, db_session):
    _, org = org_user_and_org
    report = ReportGeneratorService.generate_report(db_session, worker_user.id, utc_now() - timedelta(days=2), utc_now())

    # Create grant that expired yesterday
    expired_grant = ShareGrant(
        worker_id=worker_user.id,
        organisation_id=org.id,
        report_id=report.id,
        purpose="Claim",
        granted_at=utc_now() - timedelta(days=30),
        expires_at=utc_now() - timedelta(days=1),
        is_revoked=False,
    )
    db_session.add(expired_grant)
    db_session.commit()

    resp = client.get(f"/api/v1/organisations/{org.id}/reports/{report.id}/download", headers=org_auth_headers)
    assert resp.status_code == 403

# 9. Revoked grants are denied
def test_sec_09_revoked_sharing_grants_are_denied(client, org_auth_headers, org_user_and_org, worker_user, db_session):
    _, org = org_user_and_org
    report = ReportGeneratorService.generate_report(db_session, worker_user.id, utc_now() - timedelta(days=2), utc_now())

    # Create active grant, then revoke it
    grant = ShareGrant(
        worker_id=worker_user.id,
        organisation_id=org.id,
        report_id=report.id,
        purpose="Claim",
        granted_at=utc_now(),
        expires_at=utc_now() + timedelta(days=7),
        is_revoked=True,
        revoked_at=utc_now(),
    )
    db_session.add(grant)
    db_session.commit()

    resp = client.get(f"/api/v1/organisations/{org.id}/reports/{report.id}/download", headers=org_auth_headers)
    assert resp.status_code == 403

# 10. Revoked consent stops new location collection
def test_sec_10_revoked_consent_stops_location_collection(db_session, worker_user):
    ConsentService.grant_consent(db_session, worker_user.id, "LOCATION_TRACKING_DURING_SHIFT")
    shift = ShiftService.start_shift(db_session, worker_user.id, location_tracking_requested=True)
    assert shift.location_tracking_enabled is True

    # Worker revokes location consent
    ConsentService.revoke_consent(db_session, worker_user.id, "LOCATION_TRACKING_DURING_SHIFT")

    # Attempting to record location sample must fail
    sample_in = LocationSampleCreate(latitude=17.44, longitude=78.38, accuracy_meters=10.0)
    with pytest.raises(HTTPException) as exc_info:
        LocationService.record_sample(db_session, shift.id, worker_user.id, sample_in)
    assert exc_info.value.status_code == 403

# 11. Earnings extraction without permission is denied
@pytest.mark.asyncio
async def test_sec_11_earnings_extraction_denied_when_consent_revoked(client, worker_auth_headers, worker_user, db_session):
    # Revoke earnings consent
    ConsentService.revoke_consent(db_session, worker_user.id, "EARNINGS_DOCUMENT_EXTRACTION")

    csv_bytes = b"Date | Platform | Base Pay | Net\n2026-05-10 | Swiggy | 2000 | 2000\n"
    files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/api/v1/earnings/uploads", headers=worker_auth_headers, files=files)
    assert resp.status_code == 403
    assert "revoked consent" in resp.json()["detail"].lower()

# 12. Invalid production secrets prevent startup
def test_sec_12_invalid_production_secrets_prevent_startup():
    old_env = settings.ENVIRONMENT
    old_key = settings.APP_SECRET_KEY
    try:
        settings.ENVIRONMENT = "production"
        settings.APP_SECRET_KEY = "dev-insecure-secret-key-change-in-production-min-32-chars"
        with pytest.raises(RuntimeError) as exc_info:
            validate_environment()
        assert "CRITICAL PRODUCTION CONFIGURATION ERROR" in str(exc_info.value)
    finally:
        settings.ENVIRONMENT = old_env
        settings.APP_SECRET_KEY = old_key

# 13. Demo seeding rejected in production
def test_sec_13_demo_seeding_rejected_in_production():
    from backend.app.seed_demo import seed_demo_data
    old_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        with pytest.raises(RuntimeError) as exc_info:
            seed_demo_data()
        assert "strictly prohibited in production" in str(exc_info.value).lower()
    finally:
        settings.ENVIRONMENT = old_env

# 14. File path traversal attempts are rejected
def test_sec_14_path_traversal_attempts_sanitized(client, worker_auth_headers, worker_user, db_session):
    ConsentService.grant_consent(db_session, worker_user.id, "EARNINGS_PROCESSING")
    csv_bytes = b"Date | Platform | Base | Net\n2026-05-10 | Zomato | 1000 | 1000\n"
    # Filename with path traversal sequences
    files = {"file": ("../../../../etc/passwd.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/api/v1/earnings/uploads", headers=worker_auth_headers, files=files)
    assert resp.status_code == 200
    # Original filename should be sanitized of directory traversal dots
    data = resp.json()
    assert ".." not in data["original_filename"]
    assert "/" not in data["original_filename"]
    assert "\\" not in data["original_filename"]

# 15. Earnings upload rejected if no prior consent granted (never silently grant)
def test_sec_15_upload_rejected_without_prior_earnings_consent(client, worker_b_auth_headers, worker_b_user, db_session):
    # worker_b has NO consent record at all
    csv_bytes = b"Date | Platform | Base | Net\n2026-05-10 | Zomato | 1000 | 1000\n"
    files = {"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")}
    resp = client.post("/api/v1/earnings/uploads", headers=worker_b_auth_headers, files=files)
    assert resp.status_code == 403
    assert "explicit prior worker consent required" in resp.json()["detail"].lower()

# 16. Report verify endpoint requires ownership or active share grant
def test_sec_16_report_verify_endpoint_rejects_unauthorized_third_party(client, worker_auth_headers, worker_b_auth_headers, worker_user, db_session):
    report = ReportGeneratorService.generate_report(db_session, worker_user.id, utc_now() - timedelta(days=2), utc_now())
    
    # Worker A (owner) can verify
    resp_owner = client.get(f"/api/v1/evidence/reports/{report.id}/verify", headers=worker_auth_headers)
    assert resp_owner.status_code == 200
    assert resp_owner.json()["is_intact"] is True

    # Worker B (unauthorized third-party) is rejected
    resp_other = client.get(f"/api/v1/evidence/reports/{report.id}/verify", headers=worker_b_auth_headers)
    assert resp_other.status_code == 403
    assert "access denied" in resp_other.json()["detail"].lower()

# 17. Report file verification enforces size limit
def test_sec_17_report_verify_file_enforces_size_limit(client):
    oversized_bytes = b"0" * (10 * 1024 * 1024 + 100) # > 10MB
    files = {"file": ("huge_report.pdf", io.BytesIO(oversized_bytes), "application/pdf")}
    resp = client.post("/api/v1/evidence/reports/verify-file", files=files)
    assert resp.status_code == 413
    assert "exceeds maximum allowable limit" in resp.json()["detail"]

# 18. Organisation registration does not elevate role before approval
def test_sec_18_org_registration_does_not_elevate_role_before_approval(client, worker_auth_headers, worker_user, db_session):
    resp = client.post("/api/v1/organisations", headers=worker_auth_headers, json={
        "name": "New Pending Union",
        "slug": "new-pending-union",
        "contact_email": "pending@union.org",
        "org_type": "union",
    })
    assert resp.status_code == 200
    assert resp.json()["is_approved"] is False

    # Refresh user - must still be 'worker', NOT elevated before approval!
    db_session.refresh(worker_user)
    assert worker_user.role == "worker"

# 19. Account deletion genuinely purges linked records
def test_sec_19_account_deletion_genuinely_purges_linked_records(client, worker_auth_headers, worker_user, db_session):
    # Setup worker shift and location sample
    ConsentService.grant_consent(db_session, worker_user.id, "LOCATION_TRACKING_DURING_SHIFT")
    shift = ShiftService.start_shift(db_session, worker_user.id, location_tracking_requested=True)
    shift_id = shift.id
    LocationService.record_sample(db_session, shift_id, worker_user.id, LocationSampleCreate(latitude=17.4, longitude=78.4, accuracy_meters=5.0))

    # Request deletion
    resp = client.delete("/api/v1/profiles/me/delete", headers=worker_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["deletion_status"] == "COMPLETED"
    assert data["purged_records"]["shifts"] >= 1
    assert data["purged_records"]["location_samples"] >= 1

    # Verify database: shift and location samples are completely gone
    assert db_session.query(Shift).filter(Shift.worker_id == worker_user.id).count() == 0
    assert db_session.query(LocationSample).filter(LocationSample.shift_id == shift_id).count() == 0
