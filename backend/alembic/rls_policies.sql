-- HeatLedger Database Hardening & Row Level Security (RLS) Policies
-- Designed for PostgreSQL 15+ / Supabase with dedicated PostGIS schema

-- 1. Install PostGIS in dedicated extensions schema
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA extensions;

-- Ensure public search_path includes extensions
ALTER DATABASE CURRENT_DATABASE() SET search_path TO "$user", public, extensions;

-- 2. Enable Row Level Security (RLS) on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE location_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE break_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE exposure_intervals ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE earning_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE share_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;

-- 3. RLS Policies: Worker Data Ownership
-- Shifts: Worker owns their shifts
CREATE POLICY worker_shift_isolation ON shifts
    FOR ALL
    USING (worker_id = auth.uid()::text)
    WITH CHECK (worker_id = auth.uid()::text);

-- Location Samples: Strictly isolated to worker during consented shifts
CREATE POLICY worker_location_isolation ON location_samples
    FOR ALL
    USING (worker_id = auth.uid()::text)
    WITH CHECK (worker_id = auth.uid()::text);

-- Break Events: Worker owns their breaks
CREATE POLICY worker_break_isolation ON break_events
    FOR ALL
    USING (worker_id = auth.uid()::text)
    WITH CHECK (worker_id = auth.uid()::text);

-- Earnings Uploads: Only worker can access original uploads
CREATE POLICY worker_earnings_upload_isolation ON earnings_uploads
    FOR ALL
    USING (worker_id = auth.uid()::text)
    WITH CHECK (worker_id = auth.uid()::text);

-- Earning Entries: Worker owns their confirmed earnings entries
CREATE POLICY worker_earning_entries_isolation ON earning_entries
    FOR ALL
    USING (worker_id = auth.uid()::text)
    WITH CHECK (worker_id = auth.uid()::text);

-- Evidence Reports: Worker owns their reports
CREATE POLICY worker_report_isolation ON evidence_reports
    FOR ALL
    USING (worker_id = auth.uid()::text)
    WITH CHECK (worker_id = auth.uid()::text);

-- 4. RLS Policies: Organisation Access Strictly via Active, Unrevoked Share Grants
-- Organisations can only read reports explicitly shared with them, where is_revoked = false and expires_at > NOW()
CREATE POLICY org_shared_reports_access ON evidence_reports
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM share_grants sg
            JOIN organisation_members om ON om.organisation_id = sg.organisation_id
            WHERE sg.report_id = evidence_reports.id
              AND om.user_id = auth.uid()::text
              AND sg.is_revoked = FALSE
              AND sg.expires_at > NOW()
        )
    );

-- 5. Cases: Accessible only to approved organisation members
CREATE POLICY org_cases_access ON cases
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM organisation_members om
            WHERE om.organisation_id = cases.organisation_id
              AND om.user_id = auth.uid()::text
              AND om.is_active = TRUE
        )
    );
