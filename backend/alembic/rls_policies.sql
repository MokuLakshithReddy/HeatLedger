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

-- Authentication Lookup Function (SECURITY DEFINER)
-- Enables unauthenticated login & registration existence checks without exposing the entire users table
CREATE OR REPLACE FUNCTION authenticate_user_lookup(p_email text, p_phone text)
RETURNS TABLE (
    id text,
    email text,
    phone text,
    hashed_password text,
    role text,
    is_active boolean,
    preferred_language text,
    full_name text
)
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, u.email, u.phone, u.hashed_password, u.role, u.is_active, u.preferred_language, u.full_name
    FROM users u
    WHERE (p_email IS NOT NULL AND u.email = p_email)
       OR (p_phone IS NOT NULL AND u.phone = p_phone)
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Non-recursive Organisation Membership Helpers (SECURITY DEFINER)
-- Evaluates membership without triggering recursive RLS policy evaluations
CREATE OR REPLACE FUNCTION is_org_member(p_org_id text, p_user_id text)
RETURNS boolean
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_org_id IS NULL OR p_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM organisation_members
        WHERE organisation_id = p_org_id
          AND user_id = p_user_id
          AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_org_admin(p_org_id text, p_user_id text)
RETURNS boolean
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_org_id IS NULL OR p_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM organisation_members
        WHERE organisation_id = p_org_id
          AND user_id = p_user_id
          AND is_active = TRUE
          AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_org_caseworker(p_org_id text, p_user_id text)
RETURNS boolean
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_org_id IS NULL OR p_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM organisation_members
        WHERE organisation_id = p_org_id
          AND user_id = p_user_id
          AND is_active = TRUE
          AND role IN ('admin', 'caseworker')
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_user_linked_to_org(p_org_id text, p_user_id text)
RETURNS boolean
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_org_id IS NULL OR p_user_id IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM organisation_members
        WHERE organisation_id = p_org_id
          AND user_id = p_user_id
    );
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION org_has_members(p_org_id text)
RETURNS boolean
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_org_id IS NULL THEN
        RETURN FALSE;
    END IF;
    RETURN EXISTS (
        SELECT 1 FROM organisation_members
        WHERE organisation_id = p_org_id
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Explicitly revoke public execution from all SECURITY DEFINER functions (SEC-DEF PRIVILEGE HARDENING)
REVOKE ALL ON FUNCTION authenticate_user_lookup(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION is_org_member(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION is_org_admin(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION is_org_caseworker(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION is_user_linked_to_org(text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION org_has_members(text) FROM PUBLIC;

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

ALTER TABLE organisations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organisations FORCE ROW LEVEL SECURITY;

ALTER TABLE organisation_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE organisation_members FORCE ROW LEVEL SECURITY;

ALTER TABLE analysis_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_runs FORCE ROW LEVEL SECURITY;

ALTER TABLE processing_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_jobs FORCE ROW LEVEL SECURITY;

ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY;

-- 3. Users: Strict self and admin isolation (table-level unauthenticated queries return 0 rows)
DROP POLICY IF EXISTS user_self_isolation ON users;
DROP POLICY IF EXISTS user_select ON users;
CREATE POLICY user_select ON users
    FOR SELECT
    USING (
        id = current_app_user_id()
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

-- 4. Worker Profiles: Worker owns their profile (requires matching active session identity)
DROP POLICY IF EXISTS worker_profile_isolation ON worker_profiles;
DROP POLICY IF EXISTS worker_profile_select ON worker_profiles;
CREATE POLICY worker_profile_select ON worker_profiles
    FOR SELECT
    USING (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS worker_profile_insert ON worker_profiles;
CREATE POLICY worker_profile_insert ON worker_profiles
    FOR INSERT
    WITH CHECK (
        user_id = current_app_user_id()
        OR current_app_user_role() = 'system_admin'
    );

DROP POLICY IF EXISTS worker_profile_update ON worker_profiles;
CREATE POLICY worker_profile_update ON worker_profiles
    FOR UPDATE
    USING (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS worker_profile_delete ON worker_profiles;
CREATE POLICY worker_profile_delete ON worker_profiles
    FOR DELETE
    USING (user_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

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
            JOIN organisations o ON o.id = sg.organisation_id
            WHERE rs.source_id = exposure_intervals.id
              AND rs.source_type = 'WEATHER'
              AND is_org_member(sg.organisation_id, current_app_user_id())
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
            JOIN organisations o ON o.id = sg.organisation_id
            WHERE sg.report_id = evidence_reports.id
              AND is_org_member(sg.organisation_id, current_app_user_id())
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
            JOIN organisations o ON o.id = sg.organisation_id
            WHERE sg.report_id = report_sources.report_id
              AND is_org_member(sg.organisation_id, current_app_user_id())
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
        OR (
            is_org_member(share_grants.organisation_id, current_app_user_id())
            AND EXISTS (
                SELECT 1 FROM organisations o
                WHERE o.id = share_grants.organisation_id
                  AND o.is_approved = TRUE
            )
        )
    );

-- 16. Cases: Separate SELECT, INSERT, UPDATE, DELETE permissions
-- All active members of approved org can SELECT (non-recursive check via is_org_member)
DROP POLICY IF EXISTS org_cases_select ON cases;
CREATE POLICY org_cases_select ON cases
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR is_org_member(cases.organisation_id, current_app_user_id())
    );

-- Only admin and caseworker can INSERT cases (viewer cannot write)
DROP POLICY IF EXISTS org_cases_insert ON cases;
CREATE POLICY org_cases_insert ON cases
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR is_org_caseworker(cases.organisation_id, current_app_user_id())
    );

-- Only admin and caseworker can UPDATE cases (viewer cannot write)
DROP POLICY IF EXISTS org_cases_update ON cases;
CREATE POLICY org_cases_update ON cases
    FOR UPDATE
    USING (
        current_app_user_role() = 'system_admin'
        OR is_org_caseworker(cases.organisation_id, current_app_user_id())
    )
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR is_org_caseworker(cases.organisation_id, current_app_user_id())
    );

-- Only org admin can DELETE cases
DROP POLICY IF EXISTS org_cases_delete ON cases;
CREATE POLICY org_cases_delete ON cases
    FOR DELETE
    USING (
        current_app_user_role() = 'system_admin'
        OR is_org_admin(cases.organisation_id, current_app_user_id())
    );

-- 17. Case Notes: Members can read; admin & caseworker can insert
DROP POLICY IF EXISTS org_case_notes_select ON case_notes;
CREATE POLICY org_case_notes_select ON case_notes
    FOR SELECT
    USING (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM cases c
            WHERE c.id = case_notes.case_id
              AND is_org_member(c.organisation_id, current_app_user_id())
        )
    );

DROP POLICY IF EXISTS org_case_notes_insert ON case_notes;
CREATE POLICY org_case_notes_insert ON case_notes
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR EXISTS (
            SELECT 1 FROM cases c
            WHERE c.id = case_notes.case_id
              AND is_org_caseworker(c.organisation_id, current_app_user_id())
        )
    );

-- 18. Organisations: Public can read approved orgs; creators can read their own pending org; admins manage orgs
DROP POLICY IF EXISTS org_public_approved_select ON organisations;
CREATE POLICY org_public_approved_select ON organisations
    FOR SELECT
    USING (
        is_approved = TRUE
        OR current_app_user_role() = 'system_admin'
        OR is_user_linked_to_org(id, current_app_user_id())
    );

DROP POLICY IF EXISTS org_insert ON organisations;
CREATE POLICY org_insert ON organisations
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR is_approved = FALSE
    );

DROP POLICY IF EXISTS org_admin_update ON organisations;
CREATE POLICY org_admin_update ON organisations
    FOR UPDATE
    USING (current_app_user_role() = 'system_admin')
    WITH CHECK (current_app_user_role() = 'system_admin');

DROP POLICY IF EXISTS org_admin_delete ON organisations;
CREATE POLICY org_admin_delete ON organisations
    FOR DELETE
    USING (current_app_user_role() = 'system_admin');

-- 19. Organisation Members: Non-recursive member read and write; allows initial pending founder registration
DROP POLICY IF EXISTS org_members_select ON organisation_members;
CREATE POLICY org_members_select ON organisation_members
    FOR SELECT
    USING (
        user_id = current_app_user_id()
        OR current_app_user_role() = 'system_admin'
        OR is_org_member(organisation_id, current_app_user_id())
    );

DROP POLICY IF EXISTS org_members_write ON organisation_members;
DROP POLICY IF EXISTS org_members_insert ON organisation_members;
CREATE POLICY org_members_insert ON organisation_members
    FOR INSERT
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR is_org_admin(organisation_id, current_app_user_id())
        OR (
            user_id = current_app_user_id()
            AND role = 'admin'
            AND is_active = FALSE
            AND NOT org_has_members(organisation_id)
        )
    );

DROP POLICY IF EXISTS org_members_update ON organisation_members;
CREATE POLICY org_members_update ON organisation_members
    FOR UPDATE
    USING (
        current_app_user_role() = 'system_admin'
        OR is_org_admin(organisation_id, current_app_user_id())
    )
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR is_org_admin(organisation_id, current_app_user_id())
    );

DROP POLICY IF EXISTS org_members_delete ON organisation_members;
CREATE POLICY org_members_delete ON organisation_members
    FOR DELETE
    USING (
        current_app_user_role() = 'system_admin'
        OR is_org_admin(organisation_id, current_app_user_id())
    );

-- 20. Analysis Runs: Worker owns their analysis runs
DROP POLICY IF EXISTS analysis_runs_isolation ON analysis_runs;
CREATE POLICY analysis_runs_isolation ON analysis_runs
    FOR ALL
    USING (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin')
    WITH CHECK (worker_id = current_app_user_id() OR current_app_user_role() = 'system_admin');

-- 21. Processing Jobs: Worker can view their own triggered jobs; system admin has full access
DROP POLICY IF EXISTS processing_jobs_isolation ON processing_jobs;
CREATE POLICY processing_jobs_isolation ON processing_jobs
    FOR ALL
    USING (
        current_app_user_role() = 'system_admin'
        OR (payload IS NOT NULL AND payload->>'worker_id' = current_app_user_id())
    )
    WITH CHECK (
        current_app_user_role() = 'system_admin'
        OR (payload IS NOT NULL AND payload->>'worker_id' = current_app_user_id())
    );

-- 22. Audit Logs: Worker can view their own audit logs; append-only for active sessions
DROP POLICY IF EXISTS audit_logs_select ON audit_logs;
CREATE POLICY audit_logs_select ON audit_logs
    FOR SELECT
    USING (
        user_id = current_app_user_id()
        OR current_app_user_role() = 'system_admin'
    );

DROP POLICY IF EXISTS audit_logs_insert ON audit_logs;
CREATE POLICY audit_logs_insert ON audit_logs
    FOR INSERT
    WITH CHECK (
        user_id = current_app_user_id()
        OR user_id IS NULL
        OR current_app_user_role() = 'system_admin'
    );

-- 23. Ensure runtime application role has appropriate permissions
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'heatledger_app_user') THEN
        GRANT USAGE ON SCHEMA public TO heatledger_app_user;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO heatledger_app_user;
        GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO heatledger_app_user;
        GRANT EXECUTE ON FUNCTION authenticate_user_lookup(text, text) TO heatledger_app_user;
        GRANT EXECUTE ON FUNCTION is_org_member(text, text) TO heatledger_app_user;
        GRANT EXECUTE ON FUNCTION is_org_admin(text, text) TO heatledger_app_user;
        GRANT EXECUTE ON FUNCTION is_org_caseworker(text, text) TO heatledger_app_user;
        GRANT EXECUTE ON FUNCTION is_user_linked_to_org(text, text) TO heatledger_app_user;
        GRANT EXECUTE ON FUNCTION org_has_members(text) TO heatledger_app_user;
    END IF;
END
$$;
