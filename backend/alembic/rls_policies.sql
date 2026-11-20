-- HeatLedger Database Hardening & Row Level Security (RLS) Policies
-- Designed for PostgreSQL 15+ / PostGIS with Transaction-Level Identity Propagation
-- Fully protects Worker Data Ownership, Role-Based Access, and Scoped Organisation Access

-- 1. Helper functions to retrieve active session identity (set via set_config by FastAPI backend)
CREATE OR REPLACE FUNCTION current_app_user_id() RETURNS text AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '');
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION current_app_user_role() RETURNS text AS $$
  SELECT NULLIF(current_setting('app.current_user_role', true), '');
$$ LANGUAGE sql STABLE;

-- 2. Enable and FORCE Row Level Security (RLS) on sensitive tables
-- FORCE ensures table owners/application roles are also strictly subjected to RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;

ALTER TABLE worker_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_profiles FORCE ROW LEVEL SECURITY;

ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_records FORCE ROW LEVEL SECURITY;

ALTER TABLE shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE shifts FORCE ROW LEVEL SECURITY;

ALTER TABLE location_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_samples FORCE ROW LEVEL SECURITY;

ALTER TABLE break_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE break_events FORCE ROW LEVEL SECURITY;

ALTER TABLE exposure_intervals ENABLE ROW LEVEL SECURITY;
ALTER TABLE exposure_intervals FORCE ROW LEVEL SECURITY;

ALTER TABLE earnings_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_uploads FORCE ROW LEVEL SECURITY;

ALTER TABLE earning_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE earning_entries FORCE ROW LEVEL SECURITY;

ALTER TABLE evidence_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_reports FORCE ROW LEVEL SECURITY;

ALTER TABLE report_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_sources FORCE ROW LEVEL SECURITY;

ALTER TABLE share_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_grants FORCE ROW LEVEL SECURITY;

ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases FORCE ROW LEVEL SECURITY;

ALTER TABLE case_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_notes FORCE ROW LEVEL SECURITY;

-- 3. Users: Unauthenticated lookup for login, public registration, and strict self/admin isolation
DROP POLICY IF EXISTS user_self_isolation ON users;
DROP POLICY IF EXISTS user_select ON users;
CREATE POLICY user_select ON users
    FOR SELECT
    USING (
        current_app_user_id() IS NULL
        OR id = current_app_user_id()
        OR current_app_user_role() = 'system_admin'
    );

DROP POLICY IF EXISTS user_register_insert ON users;
CREATE POLICY user_register_insert ON users
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR (current_app_user_id() IS NULL AND role IN ('worker', 'union_member'))
        OR id = current_app_user_id()
    );

DROP POLICY IF EXISTS user_update ON users;
CREATE POLICY user_update ON users
    FOR UPDATE
    USING (id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS user_delete ON users;
CREATE POLICY user_delete ON users
    FOR DELETE
    USING (id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 4. Worker Profiles: Worker owns their profile
DROP POLICY IF EXISTS worker_profile_isolation ON worker_profiles;
CREATE POLICY worker_profile_isolation ON worker_profiles
    FOR ALL
    USING (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 5. Consent Records: Worker owns their consent declarations
DROP POLICY IF EXISTS worker_consent_isolation ON consent_records;
CREATE POLICY worker_consent_isolation ON consent_records
    FOR ALL
    USING (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 6. Shifts: Worker owns their shifts
DROP POLICY IF EXISTS worker_shift_isolation ON shifts;
CREATE POLICY worker_shift_isolation ON shifts
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 7. Location Samples: Strictly isolated to worker
DROP POLICY IF EXISTS worker_location_isolation ON location_samples;
CREATE POLICY worker_location_isolation ON location_samples
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 8. Break Events: Worker owns their breaks
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

-- 9. Exposure Intervals: Worker owns their intervals; authorized orgs can SELECT if in shared report
DROP POLICY IF EXISTS worker_exposure_interval_isolation ON exposure_intervals;
CREATE POLICY worker_exposure_interval_isolation ON exposure_intervals
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS org_shared_exposure_intervals_access ON exposure_intervals;
CREATE POLICY org_shared_exposure_intervals_access ON exposure_intervals
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM report_sources rs
            JOIN share_grants sg ON sg.report_id = rs.report_id
            JOIN organisation_members om ON om.organisation_id = sg.organisation_id
            JOIN organisations o ON o.id = sg.organisation_id
            WHERE rs.source_id = exposure_intervals.id
              AND rs.source_type = 'WEATHER'
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND sg.is_revoked = FALSE
              AND sg.expires_at > NOW()
        )
    );

-- 10. Earnings Uploads: Only worker can access original uploads
DROP POLICY IF EXISTS worker_earnings_upload_isolation ON earnings_uploads;
CREATE POLICY worker_earnings_upload_isolation ON earnings_uploads
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 11. Earning Entries: Worker owns their confirmed earnings entries
DROP POLICY IF EXISTS worker_earning_entries_isolation ON earning_entries;
CREATE POLICY worker_earning_entries_isolation ON earning_entries
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 12. Evidence Reports: Worker owns their reports
DROP POLICY IF EXISTS worker_report_isolation ON evidence_reports;
CREATE POLICY worker_report_isolation ON evidence_reports
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 13. Evidence Reports: Organisation Access Strictly via Active, Unrevoked Share Grants to APPROVED Organisations
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

-- 14. Report Sources: Readable by report owner or authorized org member; writable by report owner
DROP POLICY IF EXISTS report_sources_access ON report_sources;
CREATE POLICY report_sources_access ON report_sources
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM evidence_reports er
            WHERE er.id = report_sources.report_id
              AND er.worker_id = current_app_user_id()
        )
        OR EXISTS (
            SELECT 1 FROM share_grants sg
            JOIN organisation_members om ON om.organisation_id = sg.organisation_id
            JOIN organisations o ON o.id = sg.organisation_id
            WHERE sg.report_id = report_sources.report_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND sg.is_revoked = FALSE
              AND sg.expires_at > NOW()
        )
    );

DROP POLICY IF EXISTS report_sources_insert ON report_sources;
CREATE POLICY report_sources_insert ON report_sources
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM evidence_reports er
            WHERE er.id = report_sources.report_id
              AND er.worker_id = current_app_user_id()
        )
    );

DROP POLICY IF EXISTS report_sources_delete ON report_sources;
CREATE POLICY report_sources_delete ON report_sources
    FOR DELETE
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM evidence_reports er
            WHERE er.id = report_sources.report_id
              AND er.worker_id = current_app_user_id()
        )
    );

-- 15. Share Grants: Worker owns their share grants; approved org members can SELECT grants directed to their org
DROP POLICY IF EXISTS worker_share_grants_isolation ON share_grants;
CREATE POLICY worker_share_grants_isolation ON share_grants
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS org_share_grants_read ON share_grants;
CREATE POLICY org_share_grants_read ON share_grants
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM organisation_members om
            JOIN organisations o ON o.id = om.organisation_id
            WHERE om.organisation_id = share_grants.organisation_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
        )
    );

-- 16. Cases: Separate SELECT, INSERT, UPDATE, DELETE permissions
-- All active members of approved org can SELECT
DROP POLICY IF EXISTS org_cases_select ON cases;
CREATE POLICY org_cases_select ON cases
    FOR SELECT
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

-- Only admin and caseworker can INSERT cases (viewer cannot write)
DROP POLICY IF EXISTS org_cases_insert ON cases;
CREATE POLICY org_cases_insert ON cases
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM organisation_members om
            JOIN organisations o ON o.id = cases.organisation_id
            WHERE om.organisation_id = cases.organisation_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND om.role IN ('admin', 'caseworker')
        )
    );

-- Only admin and caseworker can UPDATE cases (viewer cannot write)
DROP POLICY IF EXISTS org_cases_update ON cases;
CREATE POLICY org_cases_update ON cases
    FOR UPDATE
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM organisation_members om
            JOIN organisations o ON o.id = cases.organisation_id
            WHERE om.organisation_id = cases.organisation_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND om.role IN ('admin', 'caseworker')
        )
    )
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM organisation_members om
            JOIN organisations o ON o.id = cases.organisation_id
            WHERE om.organisation_id = cases.organisation_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND om.role IN ('admin', 'caseworker')
        )
    );

-- Only org admin can DELETE cases
DROP POLICY IF EXISTS org_cases_delete ON cases;
CREATE POLICY org_cases_delete ON cases
    FOR DELETE
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM organisation_members om
            JOIN organisations o ON o.id = cases.organisation_id
            WHERE om.organisation_id = cases.organisation_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND om.role = 'admin'
        )
    );

-- 17. Case Notes: Members can read; admin & caseworker can insert
DROP POLICY IF EXISTS org_case_notes_select ON case_notes;
CREATE POLICY org_case_notes_select ON case_notes
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM cases c
            JOIN organisation_members om ON om.organisation_id = c.organisation_id
            JOIN organisations o ON o.id = c.organisation_id
            WHERE c.id = case_notes.case_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
        )
    );

DROP POLICY IF EXISTS org_case_notes_insert ON case_notes;
CREATE POLICY org_case_notes_insert ON case_notes
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM cases c
            JOIN organisation_members om ON om.organisation_id = c.organisation_id
            JOIN organisations o ON o.id = c.organisation_id
            WHERE c.id = case_notes.case_id
              AND om.user_id = current_app_user_id()
              AND om.is_active = TRUE
              AND o.is_approved = TRUE
              AND om.role IN ('admin', 'caseworker')
        )
    );
