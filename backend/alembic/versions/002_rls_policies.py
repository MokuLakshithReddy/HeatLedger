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
        DROP FUNCTION IF EXISTS current_app_user_id();
        DROP FUNCTION IF EXISTS current_app_user_role();
        """)
