"""PostgreSQL Row Level Security (RLS) Integration Test Suite
Validates that PostgreSQL RLS policies enforce multi-tenant isolation, worker privacy,
and scoped organisation access at the database engine level using restricted database roles.

Run under PostgreSQL (e.g. in GitHub Actions CI with PostGIS container):
  pytest backend/tests/integration/test_postgresql_rls.py -v
"""
import os
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings

def is_postgres_configured() -> bool:
    url = os.getenv("POSTGRES_TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or settings.DATABASE_URL
    return "postgresql" in url or "postgres" in url

@pytest.mark.skipif(not is_postgres_configured(), reason="Requires live PostgreSQL/PostGIS environment")
class TestPostgreSQLRowLevelSecurity:
    @pytest.fixture(scope="class")
    def pg_engine(self):
        url = os.getenv("POSTGRES_TEST_DATABASE_URL") or os.getenv("DATABASE_URL") or settings.DATABASE_URL
        engine = create_engine(url, echo=False)
        yield engine
        engine.dispose()

    @pytest.fixture
    def pg_session(self, pg_engine):
        Session = sessionmaker(bind=pg_engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    def test_missing_identity_fails_closed(self, pg_session):
        """Anonymous queries without session identity must return 0 rows under RLS."""
        pg_session.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', '', true)"))
        
        shifts = pg_session.execute(text("SELECT * FROM shifts")).fetchall()
        assert len(shifts) == 0

        reports = pg_session.execute(text("SELECT * FROM evidence_reports")).fetchall()
        assert len(reports) == 0

    def test_worker_cannot_see_other_worker_shifts(self, pg_session):
        """Worker A cannot view Worker B's shifts."""
        worker_a_id = "worker-a-rls-test"
        worker_b_id = "worker-b-rls-test"

        # As system admin, seed test records
        pg_session.execute(text("SELECT set_config('app.current_user_id', 'admin', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'system_admin', true)"))
        
        pg_session.execute(text("""
            INSERT INTO users (id, hashed_password, role, preferred_language, is_active, created_at, updated_at)
            VALUES (:uid, 'hash', 'worker', 'en', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": worker_b_id})

        pg_session.execute(text("""
            INSERT INTO shifts (id, worker_id, status, started_at, total_working_minutes, total_break_minutes, location_tracking_enabled, created_at, updated_at)
            VALUES ('shift-b-rls-test', :uid, 'COMPLETED', NOW(), 120, 0, false, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": worker_b_id})
        pg_session.commit()

        # Switch context to Worker A
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": worker_a_id})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))

        # Query shifts
        visible_shifts = pg_session.execute(text("SELECT id FROM shifts WHERE worker_id = :w_b"), {"w_b": worker_b_id}).fetchall()
        assert len(visible_shifts) == 0

    def test_worker_cannot_see_other_worker_exposure_intervals(self, pg_session):
        """Worker A cannot view Worker B's exposure intervals."""
        worker_a_id = "worker-a-rls-test"
        worker_b_id = "worker-b-rls-test"

        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": worker_a_id})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))

        visible_exposures = pg_session.execute(text("SELECT id FROM exposure_intervals WHERE worker_id = :w_b"), {"w_b": worker_b_id}).fetchall()
        assert len(visible_exposures) == 0

    def test_org_viewer_cannot_write_cases(self, pg_session):
        """Organisation members with 'viewer' or 'analyst' role cannot insert or modify cases."""
        org_id = "org-test-rls"
        viewer_id = "viewer-user-rls"

        # Seed org and member as system_admin
        pg_session.execute(text("SELECT set_config('app.current_user_id', 'admin', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'system_admin', true)"))

        pg_session.execute(text("""
            INSERT INTO organisations (id, name, slug, contact_email, org_type, is_approved, created_at, updated_at)
            VALUES (:oid, 'RLS Test Org', 'rls-test-org', 'rls@org.test', 'union', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"oid": org_id})

        pg_session.execute(text("""
            INSERT INTO users (id, hashed_password, role, preferred_language, is_active, created_at, updated_at)
            VALUES (:uid, 'hash', 'organisation_viewer', 'en', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": viewer_id})

        pg_session.execute(text("""
            INSERT INTO organisation_members (id, organisation_id, user_id, role, is_active, created_at)
            VALUES ('mem-viewer-rls', :oid, :uid, 'viewer', true, NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"oid": org_id, "uid": viewer_id})
        pg_session.commit()

        # Switch to Viewer identity
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": viewer_id})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'organisation_viewer', true)"))

        # Viewer attempts to insert a case -> RLS WITH CHECK policy violation or 0 rows affected
        with pytest.raises(Exception) as exc_info:
            pg_session.execute(text("""
                INSERT INTO cases (id, organisation_id, report_id, case_number, title, status, priority, worker_pseudonym, created_at, updated_at)
                VALUES ('case-violating-rls', :oid, 'dummy-rep', 'CASE-001', 'Test', 'OPEN', 'MEDIUM', 'Worker-1', NOW(), NOW())
            """), {"oid": org_id})
            pg_session.commit()
        assert "row-level security" in str(exc_info.value).lower() or "policy" in str(exc_info.value).lower()
