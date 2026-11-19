import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from backend.app.services.shift_service import ShiftService
from backend.app.services.break_service import BreakService
from backend.app.services.consent_service import ConsentService
from backend.app.models.entities import Shift, BreakEvent, utc_now

def test_start_shift_and_prevent_overlap(db_session, worker_user):
    # 1. Start initial shift
    shift1 = ShiftService.start_shift(db_session, worker_user.id)
    assert shift1.status == "ACTIVE"
    assert shift1.worker_id == worker_user.id

    # 2. Attempting to start a second shift while one is active MUST raise 409 Conflict
    with pytest.raises(HTTPException) as exc_info:
        ShiftService.start_shift(db_session, worker_user.id)
    assert exc_info.value.status_code == 409

    # 3. End shift
    ended_shift = ShiftService.end_shift(db_session, shift1.id, worker_user.id)
    assert ended_shift.status == "COMPLETED"

    # 4. Now a new shift can be started
    shift2 = ShiftService.start_shift(db_session, worker_user.id)
    assert shift2.status == "ACTIVE"
    assert shift2.id != shift1.id

def test_shift_pause_resume_break_deduction(db_session, worker_user):
    # Start shift 2 hours ago
    start_time = utc_now() - timedelta(hours=2)
    shift = ShiftService.start_shift(db_session, worker_user.id, started_at=start_time)

    # Start break 30 mins ago
    break_start = utc_now() - timedelta(minutes=30)
    break_event = BreakService.start_break(
        db_session, shift.id, worker_user.id, break_type="HYDRATION", started_at=break_start
    )
    assert break_event.break_type == "HYDRATION"
    assert break_event.is_worker_declared is True

    # Check shift is PAUSED
    db_session.refresh(shift)
    assert shift.status == "PAUSED"

    # End break 10 mins ago (duration = 20 mins)
    break_end = utc_now() - timedelta(minutes=10)
    BreakService.end_break(db_session, break_event.id, worker_user.id, ended_at=break_end)

    # End shift now
    end_time = utc_now()
    completed_shift = ShiftService.end_shift(db_session, shift.id, worker_user.id, ended_at=end_time)

    assert completed_shift.status == "COMPLETED"
    assert completed_shift.total_break_minutes == 20
    # 120 mins elapsed - 20 mins break = 100 mins working
    assert 98 <= completed_shift.total_working_minutes <= 102

def test_shift_manual_correction_requires_reason(db_session, worker_user):
    shift = ShiftService.start_shift(db_session, worker_user.id)
    ShiftService.end_shift(db_session, shift.id, worker_user.id)

    # Missing or trivial reason (<5 chars) must be rejected
    with pytest.raises(HTTPException) as exc_info:
        ShiftService.correct_shift(db_session, shift.id, worker_user.id, None, None, reason="bad")
    assert exc_info.value.status_code == 400

    # Valid audited correction
    corrected = ShiftService.correct_shift(
        db_session,
        shift.id,
        worker_user.id,
        started_at=utc_now() - timedelta(hours=3),
        ended_at=utc_now(),
        reason="App crashed during shift and did not record actual 09:00 AM start.",
    )
    assert "App crashed" in corrected.manual_correction_reason
