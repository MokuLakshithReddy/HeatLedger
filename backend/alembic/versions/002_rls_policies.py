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

RLS_UPGRADE_SQL = """
-- 1. Helper functions for transaction-level session identity
CREATE OR REPLACE FUNCTION current_app_user_id() RETURNS text AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '');
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION current_app_user_role() RETURNS text AS $$
  SELECT NULLIF(current_setting('app.current_user_role', true), '');
$$ LANGUAGE sql STABLE;

-- 2. Enable Row Level Security (RLS) on sensitive tables
ALTER TABLE shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE break_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE exposure_intervals ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE earning_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;

-- 3. Worker Data Ownership
DROP POLICY IF EXISTS worker_shift_isolation ON shifts;
CREATE POLICY worker_shift_isolation ON shifts
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS worker_location_isolation ON location_samples;
CREATE POLICY worker_location_isolation ON location_samples
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS worker_break_isolation ON break_events;
CREATE POLICY worker_break_isolation ON break_events
    FOR ALL
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM shifts s
            WHERE s.id = break_events.shift_id
              AND s.worker_id = current_app_user_id()
        )
    )
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM shifts s
            WHERE s.id = break_events.shift_id
              AND s.worker_id = current_app_user_id()
        )
    );

DROP POLICY IF EXISTS worker_earnings_upload_isolation ON earnings_uploads;
CREATE POLICY worker_earnings_upload_isolation ON earnings_uploads
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS worker_earning_entries_isolation ON earning_entries;
CREATE POLICY worker_earning_entries_isolation ON earning_entries
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS worker_report_isolation ON evidence_reports;
CREATE POLICY worker_report_isolation ON evidence_reports
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 4. Organisation Scoped Access via Active ShareGrants
DROP POLICY IF EXISTS org_shared_reports_access ON evidence_reports;
CREATE POLICY org_shared_reports_access ON evidence_reports
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM share_grants sg
            JOIN organisation_members om ON om.organisation_id = sg.organisation_id
            JOIN organisations o ON o.id = sg.organisation_id
            WHERE sg.report_id = evidence_reports.id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND sg.is_revoked = FALSE
              AND sg.expires_at > NOW()
        )
    );

-- 5. Cases Access
DROP POLICY IF EXISTS org_cases_access ON cases;
CREATE POLICY org_cases_access ON cases
    FOR ALL
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM organisation_members om
            JOIN organisations o ON o.id = cases.organisation_id
            WHERE om.organisation_id = cases.organisation_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
        )
    );
"""

RLS_DOWNGRADE_SQL = """
DROP POLICY IF EXISTS worker_shift_isolation ON shifts;
DROP POLICY IF EXISTS worker_location_isolation ON location_samples;
DROP POLICY IF EXISTS worker_break_isolation ON break_events;
DROP POLICY IF EXISTS worker_earnings_upload_isolation ON earnings_uploads;
DROP POLICY IF EXISTS worker_earning_entries_isolation ON earning_entries;
DROP POLICY IF EXISTS worker_report_isolation ON evidence_reports;
DROP POLICY IF EXISTS org_shared_reports_access ON evidence_reports;
DROP POLICY IF EXISTS org_cases_access ON cases;

ALTER TABLE shifts DISABLE ROW LEVEL SECURITY;
ALTER TABLE location_samples DISABLE ROW LEVEL SECURITY;
ALTER TABLE break_events DISABLE ROW LEVEL SECURITY;
ALTER TABLE exposure_intervals DISABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_uploads DISABLE ROW LEVEL SECURITY;
ALTER TABLE earning_entries DISABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE share_grants DISABLE ROW LEVEL SECURITY;
ALTER TABLE cases DISABLE ROW LEVEL SECURITY;

DROP FUNCTION IF EXISTS current_app_user_id();
DROP FUNCTION IF EXISTS current_app_user_role();
"""

def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(RLS_UPGRADE_SQL)

def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(RLS_DOWNGRADE_SQL)
