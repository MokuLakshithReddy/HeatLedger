import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from backend.app.models.entities import Shift, ExposureInterval, utc_now
from backend.app.evidence.correlator import EvidenceCorrelator
from backend.app.services.share_service import ShareService
from backend.app.services.consent_service import ConsentService
from backend.app.schemas.shares import ShareGrantCreate
from backend.app.reports.generator import ReportGeneratorService

def test_evidence_timeline_chronological_ordering(db_session, worker_user):
    now = utc_now()
    # Shift started 4 hours ago
    s = Shift(
        worker_id=worker_user.id,
        status="COMPLETED",
        started_at=now - timedelta(hours=4),
        ended_at=now - timedelta(hours=1),
        total_working_minutes=180,
    )
    db_session.add(s)
    db_session.commit()

    # Exposure interval 3 hours ago
    exp = ExposureInterval(
        shift_id=s.id,
        worker_id=worker_user.id,
        start_time=now - timedelta(hours=3),
        end_time=now - timedelta(hours=2),
        mean_temperature_celsius=42.0,
        mean_relative_humidity_pct=40.0,
        heat_index_celsius=49.1,
        risk_category="EXTREME_DANGER",
        quality_grade="HIGH",
    )
    db_session.add(exp)
    db_session.commit()

    timeline = EvidenceCorrelator.build_timeline(
        db_session, worker_user.id, now - timedelta(hours=5), now
    )
    assert timeline.events_count >= 2
    # Check that events are strictly sorted by timestamp ascending
    for i in range(len(timeline.events) - 1):
        assert timeline.events[i].timestamp <= timeline.events[i+1].timestamp
    
    # Check that extreme heat flag was triggered
    assert any("HIGH_CLIMATE_EXPOSURE" in flag for flag in timeline.flags_detected)

def test_share_grant_lifecycle_and_immediate_revocation(db_session, worker_user, org_user_and_org):
    _, org = org_user_and_org
    report = ReportGeneratorService.generate_report(
        db_session, worker_user.id, utc_now() - timedelta(days=2), utc_now()
    )

    grant_in = ShareGrantCreate(
        organisation_id=org.id,
        report_id=report.id,
        purpose="Occupational heatwave relief claim",
        duration_days=30,
    )
    grant = ShareService.create_share_grant(db_session, worker_user.id, grant_in)
    assert grant.is_revoked is False

    # Org access is verified
    verified = ShareService.verify_org_access_to_report(db_session, org.id, report.id)
    assert verified.id == grant.id

    # Worker revokes access
    revoked = ShareService.revoke_share_grant(db_session, grant.id, worker_user.id)
    assert revoked.is_revoked is True
    assert revoked.revoked_at is not None

    # Immediate revocation enforcement: Org access must now be rejected with 403 Forbidden!
    with pytest.raises(HTTPException) as exc_info:
        ShareService.verify_org_access_to_report(db_session, org.id, report.id)
    assert exc_info.value.status_code == 403
