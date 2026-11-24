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
        base_engine = create_engine(url, echo=False)

        # Check if the connecting role is a superuser (e.g. default POSTGRES_USER in Docker)
        # PostgreSQL superusers bypass RLS policies even with FORCE RLS.
        # We ensure tests execute under a restricted non-superuser role with NOBYPASSRLS.
        try:
            with base_engine.connect() as conn:
                is_super = conn.execute(text("SELECT usesuper FROM pg_user WHERE usename = current_user")).scalar()
                if is_super:
                    conn.execute(text("""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'heatledger_restricted_app_user') THEN
                                CREATE ROLE heatledger_restricted_app_user WITH LOGIN PASSWORD 'restricted_pass_123' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
                            END IF;
                        END
                        $$;
                        GRANT USAGE ON SCHEMA public TO heatledger_restricted_app_user;
                        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO heatledger_restricted_app_user;
                        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO heatledger_restricted_app_user;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO heatledger_restricted_app_user;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO heatledger_restricted_app_user;
                    """))
                    conn.commit()

                    from urllib.parse import urlparse, urlunparse
                    parsed = urlparse(url)
                    host = parsed.hostname or "localhost"
                    port = parsed.port or 5432
                    dbname = parsed.path.lstrip("/")
                    restricted_url = f"{parsed.scheme}://heatledger_restricted_app_user:restricted_pass_123@{host}:{port}/{dbname}"
                    restricted_engine = create_engine(restricted_url, echo=False)
                    yield restricted_engine
                    restricted_engine.dispose()
                    base_engine.dispose()
                    return
        except Exception:
            pass

        yield base_engine
        base_engine.dispose()

    @pytest.fixture
    def pg_session(self, pg_engine):
        Session = sessionmaker(bind=pg_engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

    def test_database_role_is_restricted_non_superuser(self, pg_session):
        """Verifies the active database role enforces RLS (NOSUPERUSER, NOBYPASSRLS)."""
        res = pg_session.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")).fetchone()
        if res:
            assert res[0] is False, "Active role for RLS tests must not be a superuser"
            assert res[1] is False, "Active role for RLS tests must have NOBYPASSRLS"

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

    def test_unauthenticated_login_lookup_allowed(self, pg_session):
        """Unauthenticated requests cannot dump users table directly, but can securely authenticate via authenticate_user_lookup."""
        worker_id = "worker-auth-rls-test"
        pg_session.execute(text("SELECT set_config('app.current_user_id', 'admin', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'system_admin', true)"))
        pg_session.execute(text("""
            INSERT INTO users (id, email, hashed_password, role, preferred_language, is_active, created_at, updated_at)
            VALUES (:uid, 'login_test@worker.org', 'test_hash', 'worker', 'en', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": worker_id})
        pg_session.commit()

        # Switch to unauthenticated state (NULL / empty session identity)
        pg_session.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', '', true)"))

        # Table-level query MUST fail closed (0 rows) to prevent user enumeration / password dumping
        all_users = pg_session.execute(text("SELECT id, email, hashed_password FROM users")).fetchall()
        assert len(all_users) == 0, "Direct table query on users table must return 0 rows when unauthenticated"

        # Security definer function allows single-user lookup for the specific credentials
        auth_row = pg_session.execute(text("SELECT id, email, hashed_password FROM authenticate_user_lookup('login_test@worker.org', NULL)")).fetchone()
        assert auth_row is not None
        assert auth_row[0] == worker_id
        assert auth_row[1] == 'login_test@worker.org'

        # Non-matching credentials return 0 rows
        non_existent = pg_session.execute(text("SELECT id, email, hashed_password FROM authenticate_user_lookup('nobody@worker.org', NULL)")).fetchone()
        assert non_existent is None

    def test_unauthenticated_cannot_insert_worker_profile(self, pg_session):
        """Unauthenticated client cannot insert worker profile for arbitrary user under hardened RLS."""
        pg_session.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', '', true)"))

        with pytest.raises(Exception) as exc_info:
            pg_session.execute(text("""
                INSERT INTO worker_profiles (id, user_id, city, consented_location_tracking, created_at, updated_at)
                VALUES ('prof-unauth-violating', 'arbitrary-user-id', 'Hyderabad', false, NOW(), NOW())
            """))
            pg_session.commit()
        assert "row-level security" in str(exc_info.value).lower() or "policy" in str(exc_info.value).lower()

    def test_report_source_insert_and_isolation(self, pg_session):
        """Report owner can insert report sources; other workers cannot."""
        worker_a = "worker-rep-a"
        worker_b = "worker-rep-b"
        rep_a = "rep-a-rls-test"

        # Seed users and report as admin
        pg_session.execute(text("SELECT set_config('app.current_user_id', 'admin', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'system_admin', true)"))
        for uid in [worker_a, worker_b]:
            pg_session.execute(text("""
                INSERT INTO users (id, hashed_password, role, preferred_language, is_active, created_at, updated_at)
                VALUES (:uid, 'hash', 'worker', 'en', true, NOW(), NOW())
                ON CONFLICT (id) DO NOTHING
            """), {"uid": uid})
        pg_session.execute(text("""
            INSERT INTO evidence_reports (id, worker_id, report_number, period_start, period_end, integrity_sha256, limitations_disclaimer, created_at)
            VALUES (:rid, :wid, 'REP-RLS-001', NOW() - INTERVAL '1 day', NOW(), 'sha256hash', 'disclaimer', NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"rid": rep_a, "wid": worker_a})
        pg_session.commit()

        # Worker A (owner) can insert report source
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": worker_a})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))
        pg_session.execute(text("""
            INSERT INTO report_sources (id, report_id, source_type, source_id, created_at)
            VALUES ('src-a-owner', :rid, 'SHIFT', 'shift-1', NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"rid": rep_a})
        pg_session.commit()

        # Worker B (non-owner) attempting to insert source for Worker A's report must fail under RLS
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": worker_b})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))
        with pytest.raises(Exception) as exc_info:
            pg_session.execute(text("""
                INSERT INTO report_sources (id, report_id, source_type, source_id, created_at)
                VALUES ('src-b-violating', :rid, 'SHIFT', 'shift-2', NOW())
            """), {"rid": rep_a})
            pg_session.commit()
        assert "row-level security" in str(exc_info.value).lower() or "policy" in str(exc_info.value).lower()

    def test_registration_full_flow_under_restricted_role(self, pg_session):
        """Full registration flow: user insertion + profile creation + post-commit refresh under restricted role."""
        new_uid = "worker-reg-flow-test-01"
        new_email = "new_worker_rls@example.org"

        # Simulate registration: identity set before inserting and committed
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": new_uid})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', false)"))

        pg_session.execute(text("""
            INSERT INTO users (id, email, hashed_password, role, preferred_language, is_active, created_at, updated_at)
            VALUES (:uid, :email, 'hash123', 'worker', 'en', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": new_uid, "email": new_email})

        pg_session.execute(text("""
            INSERT INTO worker_profiles (id, user_id, city, consented_location_tracking, created_at, updated_at)
            VALUES ('prof-flow-01', :uid, 'Hyderabad', false, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": new_uid})
        pg_session.commit()

        # Re-apply identity for post-commit read (simulating after_begin event)
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": new_uid})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))

        user_row = pg_session.execute(text("SELECT id, email FROM users WHERE id = :uid"), {"uid": new_uid}).fetchone()
        assert user_row is not None
        assert user_row[0] == new_uid

        prof_row = pg_session.execute(text("SELECT id, user_id FROM worker_profiles WHERE user_id = :uid"), {"uid": new_uid}).fetchone()
        assert prof_row is not None
        assert prof_row[1] == new_uid

    def test_organisation_operations_non_recursive_rls(self, pg_session):
        """Validates non-recursive organisation membership checks and initial registration authorization."""
        admin_uid = "org-founder-test"
        org_id = "org-advocacy-rls-test"

        # 1. Founder registers new unapproved organisation with initial pending admin membership
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": admin_uid})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', false)"))

        # Seed founder user
        pg_session.execute(text("""
            INSERT INTO users (id, email, hashed_password, role, preferred_language, is_active, created_at, updated_at)
            VALUES (:uid, 'founder@union.org', 'hash', 'worker', 'en', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": admin_uid})

        # Insert unapproved organisation and member
        pg_session.execute(text("""
            INSERT INTO organisations (id, name, slug, contact_email, org_type, is_approved, created_at, updated_at)
            VALUES (:oid, 'Advocacy Union', 'advocacy-union-rls', 'info@union.org', 'union', false, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"oid": org_id})

        pg_session.execute(text("""
            INSERT INTO organisation_members (id, organisation_id, user_id, role, is_active, created_at)
            VALUES ('mem-founder-01', :oid, :uid, 'admin', false, NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"oid": org_id, "uid": admin_uid})
        pg_session.commit()

        # Founder can read their own pending organisation
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": admin_uid})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))
        visible_org = pg_session.execute(text("SELECT id, name FROM organisations WHERE id = :oid"), {"oid": org_id}).fetchone()
        assert visible_org is not None
        assert visible_org[0] == org_id

        # Third-party worker cannot read this unapproved organisation
        outsider_uid = "outsider-worker-01"
        pg_session.execute(text("SELECT set_config('app.current_user_id', :uid, true)"), {"uid": outsider_uid})
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'worker', true)"))
        outsider_view = pg_session.execute(text("SELECT id FROM organisations WHERE id = :oid"), {"oid": org_id}).fetchone()
        assert outsider_view is None

    def test_security_definer_functions_not_executable_by_public(self, pg_session):
        """Verifies that SECURITY DEFINER functions have execute revoked from PUBLIC."""
        funcs = [
            "authenticate_user_lookup(text, text)",
            "is_org_member(text, text)",
            "is_org_admin(text, text)",
            "is_org_caseworker(text, text)",
            "is_user_linked_to_org(text, text)",
            "org_has_members(text)",
        ]
        for fn in funcs:
            has_priv = pg_session.execute(
                text("SELECT has_function_privilege('public', :fn, 'execute')"),
                {"fn": fn}
            ).scalar()
            assert has_priv is False, f"Function {fn} must not be executable by PUBLIC"

    def test_authenticated_user_lookup_succeeds_under_rls(self, pg_session):
        """Verifies get_current_user logic where RLS identity is initialized before querying users."""
        from backend.app.core.security import create_access_token
        from backend.app.api.deps import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        test_uid = "auth-rls-test-worker"
        # Seed test user using admin identity
        pg_session.execute(text("SELECT set_config('app.current_user_id', 'admin', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', 'system_admin', true)"))
        pg_session.execute(text("""
            INSERT INTO users (id, email, hashed_password, role, preferred_language, is_active, created_at, updated_at)
            VALUES (:uid, 'auth_test@heatledger.local', 'hash', 'worker', 'en', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"uid": test_uid})
        pg_session.commit()

        # Clear session variables to simulate fresh unauthenticated connection state
        pg_session.execute(text("SELECT set_config('app.current_user_id', '', true)"))
        pg_session.execute(text("SELECT set_config('app.current_user_role', '', true)"))

        token = create_access_token(data={"sub": test_uid, "role": "worker"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = get_current_user(credentials=creds, db=pg_session)
        assert user is not None
        assert user.id == test_uid
        assert user.role == "worker"
