-- HeatLedger Database Hardening & Row Level Security (RLS) Policies
-- Designed for PostgreSQL 15+ / PostGIS with Transaction-Level Identity Propagation

-- 1. Helper functions to retrieve active session identity (set via SET LOCAL by FastAPI backend)
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

-- 3. RLS Policies: Worker Data Ownership (with admin bypass)
-- Shifts: Worker owns their shifts
DROP POLICY IF EXISTS worker_shift_isolation ON shifts;
CREATE POLICY worker_shift_isolation ON shifts
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- Location Samples: Strictly isolated to worker during consented shifts
DROP POLICY IF EXISTS worker_location_isolation ON location_samples;
CREATE POLICY worker_location_isolation ON location_samples
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- Break Events: Worker owns their breaks
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

-- Earnings Uploads: Only worker can access original uploads
DROP POLICY IF EXISTS worker_earnings_upload_isolation ON earnings_uploads;
CREATE POLICY worker_earnings_upload_isolation ON earnings_uploads
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- Earning Entries: Worker owns their confirmed earnings entries
DROP POLICY IF EXISTS worker_earning_entries_isolation ON earning_entries;
CREATE POLICY worker_earning_entries_isolation ON earning_entries
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- Evidence Reports: Worker owns their reports (or admin)
DROP POLICY IF EXISTS worker_report_isolation ON evidence_reports;
CREATE POLICY worker_report_isolation ON evidence_reports
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 4. RLS Policies: Organisation Access Strictly via Active, Unrevoked Share Grants to APPROVED Organisations
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

-- 5. Cases: Accessible only to approved organisation members or admin
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
