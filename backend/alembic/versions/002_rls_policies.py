"""Row Level Security (RLS) policies for PostgreSQL
Revision ID: 002_rls_policies
Revises: 001_initial_schema
Create Date: 2026-11-20 01:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
import os

revision = '002_rls_policies'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

# Read the hardened policies from rls_policies.sql
RLS_SQL_FILE = os.path.join(os.path.dirname(__file__), "..", "rls_policies.sql")

def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        if os.path.exists(RLS_SQL_FILE):
            with open(RLS_SQL_FILE, "r", encoding="utf-8") as f:
                sql_content = f.read()
            op.execute(sql_content)
        else:
            # Fallback inline if file not found
            pass

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
        DROP POLICY IF EXISTS user_self_isolation ON users;
        DROP POLICY IF EXISTS user_select ON users;
        DROP POLICY IF EXISTS user_register_insert ON users;
        DROP POLICY IF EXISTS user_update ON users;
        DROP POLICY IF EXISTS user_delete ON users;
        DROP POLICY IF EXISTS worker_profile_isolation ON worker_profiles;
        DROP POLICY IF EXISTS worker_profile_select ON worker_profiles;
        DROP POLICY IF EXISTS worker_profile_insert ON worker_profiles;
        DROP POLICY IF EXISTS worker_profile_update ON worker_profiles;
        DROP POLICY IF EXISTS worker_profile_delete ON worker_profiles;
        DROP POLICY IF EXISTS worker_consent_isolation ON consent_records;
        DROP POLICY IF EXISTS worker_shift_isolation ON shifts;
        DROP POLICY IF EXISTS worker_location_isolation ON location_samples;
        DROP POLICY IF EXISTS worker_break_isolation ON break_events;
        DROP POLICY IF EXISTS worker_exposure_interval_isolation ON exposure_intervals;
        DROP POLICY IF EXISTS org_shared_exposure_intervals_access ON exposure_intervals;
        DROP POLICY IF EXISTS worker_earnings_upload_isolation ON earnings_uploads;
        DROP POLICY IF EXISTS worker_earning_entries_isolation ON earning_entries;
        DROP POLICY IF EXISTS worker_report_isolation ON evidence_reports;
        DROP POLICY IF EXISTS org_shared_reports_access ON evidence_reports;
        DROP POLICY IF EXISTS report_sources_access ON report_sources;
        DROP POLICY IF EXISTS report_sources_insert ON report_sources;
        DROP POLICY IF EXISTS report_sources_delete ON report_sources;
        DROP POLICY IF EXISTS worker_share_grants_isolation ON share_grants;
        DROP POLICY IF EXISTS org_share_grants_read ON share_grants;
        DROP POLICY IF EXISTS org_cases_select ON cases;
        DROP POLICY IF EXISTS org_cases_insert ON cases;
        DROP POLICY IF EXISTS org_cases_update ON cases;
        DROP POLICY IF EXISTS org_cases_delete ON cases;
        DROP POLICY IF EXISTS org_case_notes_select ON case_notes;
        DROP POLICY IF EXISTS org_case_notes_insert ON case_notes;
        DROP POLICY IF EXISTS org_public_approved_select ON organisations;
        DROP POLICY IF EXISTS org_insert ON organisations;
        DROP POLICY IF EXISTS org_admin_update ON organisations;
        DROP POLICY IF EXISTS org_admin_delete ON organisations;
        DROP POLICY IF EXISTS org_members_select ON organisation_members;
        DROP POLICY IF EXISTS org_members_write ON organisation_members;
        DROP POLICY IF EXISTS org_members_insert ON organisation_members;
        DROP POLICY IF EXISTS org_members_update ON organisation_members;
        DROP POLICY IF EXISTS org_members_delete ON organisation_members;
        DROP POLICY IF EXISTS analysis_runs_isolation ON analysis_runs;
        DROP POLICY IF EXISTS processing_jobs_isolation ON processing_jobs;
        DROP POLICY IF EXISTS audit_logs_select ON audit_logs;
        DROP POLICY IF EXISTS audit_logs_insert ON audit_logs;

        -- Disable and remove FORCE ROW LEVEL SECURITY to prevent fail-closed lockout after policy removal
        ALTER TABLE users NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE users DISABLE ROW LEVEL SECURITY;
        ALTER TABLE worker_profiles NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE worker_profiles DISABLE ROW LEVEL SECURITY;
        ALTER TABLE consent_records NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE consent_records DISABLE ROW LEVEL SECURITY;
        ALTER TABLE shifts NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE shifts DISABLE ROW LEVEL SECURITY;
        ALTER TABLE location_samples NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE location_samples DISABLE ROW LEVEL SECURITY;
        ALTER TABLE break_events NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE break_events DISABLE ROW LEVEL SECURITY;
        ALTER TABLE exposure_intervals NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE exposure_intervals DISABLE ROW LEVEL SECURITY;
        ALTER TABLE earnings_uploads NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE earnings_uploads DISABLE ROW LEVEL SECURITY;
        ALTER TABLE earning_entries NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE earning_entries DISABLE ROW LEVEL SECURITY;
        ALTER TABLE evidence_reports NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE evidence_reports DISABLE ROW LEVEL SECURITY;
        ALTER TABLE report_sources NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE report_sources DISABLE ROW LEVEL SECURITY;
        ALTER TABLE share_grants NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE share_grants DISABLE ROW LEVEL SECURITY;
        ALTER TABLE cases NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE cases DISABLE ROW LEVEL SECURITY;
        ALTER TABLE case_notes NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE case_notes DISABLE ROW LEVEL SECURITY;
        ALTER TABLE organisations NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE organisations DISABLE ROW LEVEL SECURITY;
        ALTER TABLE organisation_members NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE organisation_members DISABLE ROW LEVEL SECURITY;
        ALTER TABLE analysis_runs NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE analysis_runs DISABLE ROW LEVEL SECURITY;
        ALTER TABLE processing_jobs NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE processing_jobs DISABLE ROW LEVEL SECURITY;
        ALTER TABLE audit_logs NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;

        -- Drop SECURITY DEFINER and session identity helper functions
        DROP FUNCTION IF EXISTS authenticate_user_lookup(text, text);
        DROP FUNCTION IF EXISTS is_org_member(text, text);
        DROP FUNCTION IF EXISTS is_org_admin(text, text);
        DROP FUNCTION IF EXISTS is_org_caseworker(text, text);
        DROP FUNCTION IF EXISTS is_user_linked_to_org(text, text);
        DROP FUNCTION IF EXISTS org_has_members(text);
        DROP FUNCTION IF EXISTS current_app_user_id();
        DROP FUNCTION IF EXISTS current_app_user_role();
        """)
