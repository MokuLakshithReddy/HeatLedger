"""Comprehensive End-to-End Scenarios 1 to 7
Validates all critical user journeys defined in Section 18 of Master Build Prompt.
"""
import pytest
import io
from datetime import datetime, timezone, timedelta

def test_scenario_1_worker_shift_and_break_lifecycle(client):
    """Scenario 1: Worker registers → completes onboarding → starts shift → records break → resumes shift → ends shift."""
    # 1. Register worker
    reg_payload = {
        "email": "e2e.worker1@heatledger.local",
        "phone": "+919100000001",
        "password": "StrongPassword123!",
        "full_name": "E2E Worker Venkat",
        "role": "worker",
        "preferred_language": "te",
        "primary_platforms": ["Swiggy", "Zomato"],
        "city": "Hyderabad",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Complete onboarding by granting location consent
    consent_resp = client.post(
        "/api/v1/profiles/me/consents",
        headers=headers,
        json={"purpose": "LOCATION_TRACKING_DURING_SHIFT", "is_granted": True},
    )
    assert consent_resp.status_code == 200

    # 3. Start shift with location tracking enabled
    start_resp = client.post(
        "/api/v1/shifts/start",
        headers=headers,
        json={"location_tracking_enabled": True},
    )
    assert start_resp.status_code == 200
    shift_id = start_resp.json()["id"]
    assert start_resp.json()["status"] == "ACTIVE"
    assert start_resp.json()["location_tracking_enabled"] is True

    # 4. Record a break
    break_resp = client.post(
        f"/api/v1/shifts/{shift_id}/breaks",
        headers=headers,
        json={"break_type": "HYDRATION", "worker_notes": "Drinking electrolytes at shaded booth"},
    )
    assert break_resp.status_code == 200
    break_id = break_resp.json()["id"]
    assert break_resp.json()["is_worker_declared"] is True

    # Verify shift is paused during break
    active_resp = client.get("/api/v1/shifts/active", headers=headers)
    assert active_resp.json()["active_shift"]["status"] == "PAUSED"

    # 5. End break / resume shift
    end_break_resp = client.post(f"/api/v1/breaks/{break_id}/end", headers=headers, json={})
    assert end_break_resp.status_code == 200

    # Verify shift is active again
    active_after = client.get("/api/v1/shifts/active", headers=headers)
    assert active_after.json()["active_shift"]["status"] == "ACTIVE"

    # 6. End shift
    end_resp = client.post(f"/api/v1/shifts/{shift_id}/end", headers=headers, json={})
    assert end_resp.status_code == 200
    assert end_resp.json()["status"] == "COMPLETED"
    assert end_resp.json()["location_tracking_enabled"] is False

def test_scenario_2_earnings_upload_and_confirmation(client):
    """Scenario 2: Worker uploads earnings statement → AI extracts values → worker reviews them → confirms them."""
    # 1. Login or register worker
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": "e2e.worker2@heatledger.local",
        "phone": "+919100000002",
        "password": "StrongPassword123!",
        "role": "worker",
    })
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Explicitly grant prior consent for earnings processing
    consent_resp = client.post("/api/v1/profiles/me/consents", headers=headers, json={
        "purpose": "EARNINGS_PROCESSING",
        "is_granted": True,
        "consent_text_version": "1.0",
    })
    assert consent_resp.status_code == 200

    # 2. Upload statement CSV
    csv_bytes = (
        b"Period | Platform | Base Delivery | Incentives | Deductions | Net Payment\n"
        b"2026-05-15 to 2026-05-21 | Zomato | 4800.00 | 1100.00 | 150.00 | 5750.00\n"
    )
    files = {"file": ("zomato_week20.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_resp = client.post("/api/v1/earnings/uploads", headers=headers, files=files)
    assert upload_resp.status_code == 200
    upload_id = upload_resp.json()["id"]
    assert upload_resp.json()["sha256_hash"] is not None

    # 3. List extracted entries (unconfirmed)
    entries_resp = client.get("/api/v1/earnings/entries", headers=headers)
    assert entries_resp.status_code == 200
    entries = entries_resp.json()
    assert len(entries) > 0
    entry = entries[0]
    assert entry["is_confirmed_by_worker"] is False
    assert entry["platform_name"] == "Zomato"

    # 4. Worker reviews and confirms
    confirm_resp = client.post(
        f"/api/v1/earnings/entries/{entry['id']}/confirm",
        headers=headers,
        json={"is_confirmed": True, "worker_adjusted_notes": "Cross-verified with bank account credit"},
    )
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["is_confirmed_by_worker"] is True
    assert confirm_resp.json()["worker_confirmed_at"] is not None

def test_scenario_3_correlation_and_pdf_report_download(client):
    """Scenario 3: Environmental records and worker records correlated → evidence timeline generated → PDF downloaded."""
    reg_resp = client.post("/api/v1/auth/register", json={
        "email": "e2e.worker3@heatledger.local",
        "phone": "+919100000003",
        "password": "StrongPassword123!",
        "role": "worker",
    })
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Start and end a shift
    shift_resp = client.post("/api/v1/shifts/start", headers=headers, json={"location_tracking_enabled": False})
    shift_id = shift_resp.json()["id"]
    client.post(f"/api/v1/shifts/{shift_id}/end", headers=headers, json={})

    # Retrieve timeline
    timeline_resp = client.get("/api/v1/evidence/timelines", headers=headers)
    assert timeline_resp.status_code == 200
    assert "events" in timeline_resp.json()
    assert timeline_resp.json()["events_count"] > 0

    # Generate Evidence Report
    now = datetime.now(timezone.utc)
    report_gen_resp = client.post(
        "/api/v1/evidence/reports",
        headers=headers,
        json={
            "period_start": (now - timedelta(days=7)).isoformat(),
            "period_end": now.isoformat(),
        },
    )
    assert report_gen_resp.status_code == 200
    report_id = report_gen_resp.json()["id"]
    sha256_hash = report_gen_resp.json()["integrity_sha256"]
    assert len(sha256_hash) == 64

    # Download PDF
    download_resp = client.get(f"/api/v1/evidence/reports/{report_id}/download", headers=headers)
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.headers["x-report-integrity-sha256"] == sha256_hash
    assert len(download_resp.content) > 1000

def test_scenario_4_sharing_and_revocation_enforcement(client, admin_user):
    """Scenario 4: Worker shares report with org → org opens it → worker revokes access → org can no longer open it."""
    # Register worker
    w_resp = client.post("/api/v1/auth/register", json={
        "email": "e2e.worker4@heatledger.local",
        "phone": "+919100000004",
        "password": "StrongPassword123!",
        "role": "worker",
    })
    w_token = w_resp.json()["access_token"]
    w_headers = {"Authorization": f"Bearer {w_token}"}

    # Register Org Officer as worker account (SEC-01)
    org_user_resp = client.post("/api/v1/auth/register", json={
        "email": "caseworker@hyd.org",
        "phone": "+919100000044",
        "password": "StrongPassword123!",
        "role": "worker",
    })
    org_token = org_user_resp.json()["access_token"]
    org_headers = {"Authorization": f"Bearer {org_token}"}

    # Register organisation by org officer
    org_resp = client.post(
        "/api/v1/organisations",
        headers=org_headers,
        json={"name": "Hyderabad Delivery Union", "slug": "hyd-delivery-union", "contact_email": "union@hyd.org"},
    )
    org_id = org_resp.json()["id"]

    # SEC-02: Administrator approves the organisation for worker evidence sharing
    from backend.app.core.security import create_access_token
    admin_token = create_access_token({"sub": admin_user.id, "role": "system_admin", "email": admin_user.email})
    appr_resp = client.post(f"/api/v1/admin/organisations/{org_id}/approve", headers={"Authorization": f"Bearer {admin_token}"})
    assert appr_resp.status_code == 200

    # Worker generates report
    now = datetime.now(timezone.utc)
    rep_resp = client.post(
        "/api/v1/evidence/reports",
        headers=w_headers,
        json={"period_start": (now - timedelta(days=3)).isoformat(), "period_end": now.isoformat()},
    )
    report_id = rep_resp.json()["id"]

    # Worker grants share
    share_resp = client.post(
        "/api/v1/shares",
        headers=w_headers,
        json={"organisation_id": org_id, "report_id": report_id, "purpose": "Summer heat emergency relief claim"},
    )
    assert share_resp.status_code == 200
    share_id = share_resp.json()["id"]

    # Org downloads shared report successfully
    org_dl = client.get(f"/api/v1/organisations/{org_id}/reports/{report_id}/download", headers=org_headers)
    assert org_dl.status_code == 200

    # Worker revokes share
    revoke_resp = client.post(f"/api/v1/shares/{share_id}/revoke", headers=w_headers)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["is_revoked"] is True

    # Org tries downloading again -> MUST BE 403 FORBIDDEN!
    revoked_dl = client.get(f"/api/v1/organisations/{org_id}/reports/{report_id}/download", headers=org_headers)
    assert revoked_dl.status_code == 403

def test_scenario_5_cross_worker_isolation(client):
    """Scenario 5: Worker A attempts to access Worker B's records → request is denied."""
    wa_resp = client.post("/api/v1/auth/register", json={
        "email": "worker.alice@heatledger.local", "password": "StrongPassword123!", "role": "worker"
    })
    wa_headers = {"Authorization": f"Bearer {wa_resp.json()['access_token']}"}

    wb_resp = client.post("/api/v1/auth/register", json={
        "email": "worker.bob@heatledger.local", "password": "StrongPassword123!", "role": "worker"
    })
    wb_headers = {"Authorization": f"Bearer {wb_resp.json()['access_token']}"}

    # Alice starts a shift
    shift_a = client.post("/api/v1/shifts/start", headers=wa_headers, json={}).json()

    # Bob attempts to read or end Alice's shift
    read_attempt = client.get(f"/api/v1/shifts/{shift_a['id']}", headers=wb_headers)
    assert read_attempt.status_code == 404

    end_attempt = client.post(f"/api/v1/shifts/{shift_a['id']}/end", headers=wb_headers, json={})
    assert end_attempt.status_code == 404

def test_scenario_6_weather_provider_resilience(client):
    """Scenario 6: Weather provider resilience → application displays honest status and fallback demo data rather than fabricated info."""
    w_resp = client.post("/api/v1/auth/register", json={
        "email": "worker.resilience@heatledger.local", "password": "StrongPassword123!", "role": "worker"
    })
    headers = {"Authorization": f"Bearer {w_resp.json()['access_token']}"}

    # Check provider health
    health_resp = client.get("/api/v1/climate/providers/status", headers=headers)
    assert health_resp.status_code == 200
    providers = health_resp.json()["providers"]
    
    # Verify IMD is reported honestly (unconfigured or operational) and demo provider is transparently designated
    demo_provider = next((p for p in providers if p["provider"] == "DEMO_HYDERABAD"), None)
    assert demo_provider is not None
    assert demo_provider["is_live"] is False
    assert "synthetic demonstration" in demo_provider["disclaimer"].lower()

    # Weather observations report data_freshness_status = DEMO_SAMPLE when using fallback
    obs_resp = client.get("/api/v1/climate/observations?lat=17.3850&lon=78.4867", headers=headers)
    assert obs_resp.status_code == 200
    assert obs_resp.json()["data_freshness_status"] in ["DEMO_SAMPLE", "REALTIME"]

def test_scenario_7_location_consent_revocation_during_shift(client):
    """Scenario 7: Worker revokes location consent during a shift → future collection stops immediately."""
    w_resp = client.post("/api/v1/auth/register", json={
        "email": "worker.gps_revoked@heatledger.local", "password": "StrongPassword123!", "role": "worker"
    })
    headers = {"Authorization": f"Bearer {w_resp.json()['access_token']}"}

    # 1. Grant location consent
    client.post("/api/v1/profiles/me/consents", headers=headers, json={
        "purpose": "LOCATION_TRACKING_DURING_SHIFT", "is_granted": True
    })

    # 2. Start shift with location tracking enabled
    shift = client.post("/api/v1/shifts/start", headers=headers, json={"location_tracking_enabled": True}).json()
    assert shift["location_tracking_enabled"] is True

    # 3. Post a valid sample
    sample_resp = client.post(
        f"/api/v1/shifts/{shift['id']}/location-samples",
        headers=headers,
        json={"latitude": 17.3850, "longitude": 78.4867, "accuracy_meters": 10.0},
    )
    assert sample_resp.status_code == 200

    # 4. Worker revokes location consent mid-shift
    client.post("/api/v1/profiles/me/consents/revoke", headers=headers, json={
        "purpose": "LOCATION_TRACKING_DURING_SHIFT"
    })

    # 5. Future location sample MUST be rejected with 403 Forbidden!
    future_sample = client.post(
        f"/api/v1/shifts/{shift['id']}/location-samples",
        headers=headers,
        json={"latitude": 17.3855, "longitude": 78.4870, "accuracy_meters": 12.0},
    )
    assert future_sample.status_code == 403
    assert "revoked location tracking consent" in future_sample.json()["detail"].lower()
