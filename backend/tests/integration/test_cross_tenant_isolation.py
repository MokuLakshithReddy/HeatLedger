import pytest
from datetime import datetime, timezone, timedelta
from backend.app.services.shift_service import ShiftService
from backend.app.reports.generator import ReportGeneratorService
from backend.app.models.entities import utc_now

def test_worker_cross_tenant_isolation(client, worker_user, worker_b_user, worker_auth_headers, worker_b_auth_headers, db_session):
    # Worker A creates a shift
    shift_a = ShiftService.start_shift(db_session, worker_user.id)
    ShiftService.end_shift(db_session, shift_a.id, worker_user.id)

    # Worker A creates a report
    report_a = ReportGeneratorService.generate_report(
        db_session, worker_user.id, utc_now() - timedelta(days=1), utc_now()
    )

    # 1. Worker B attempts to read Worker A's shift details via API
    resp_shift = client.get(f"/api/v1/shifts/{shift_a.id}", headers=worker_b_auth_headers)
    assert resp_shift.status_code == 404 # Concealed / denied

    # 2. Worker B attempts to access Worker A's report details
    resp_report = client.get(f"/api/v1/evidence/reports/{report_a.id}", headers=worker_b_auth_headers)
    assert resp_report.status_code == 404

    # 3. Worker B attempts to download Worker A's report PDF
    resp_download = client.get(f"/api/v1/evidence/reports/{report_a.id}/download", headers=worker_b_auth_headers)
    assert resp_download.status_code == 404

    # 4. Worker A can access their own report successfully
    resp_valid = client.get(f"/api/v1/evidence/reports/{report_a.id}", headers=worker_auth_headers)
    assert resp_valid.status_code == 200
    assert resp_valid.json()["id"] == report_a.id

def test_org_cannot_access_unshared_report(client, worker_user, org_auth_headers, org_user_and_org, db_session):
    _, org = org_user_and_org
    # Worker creates report without sharing it with this org
    report = ReportGeneratorService.generate_report(
        db_session, worker_user.id, utc_now() - timedelta(days=1), utc_now()
    )

    # Org attempts to download unshared report PDF
    resp = client.get(
        f"/api/v1/organisations/{org.id}/reports/{report.id}/download",
        headers=org_auth_headers,
    )
    assert resp.status_code == 403
    assert "No active, unrevoked sharing grant exists" in resp.json()["detail"]
