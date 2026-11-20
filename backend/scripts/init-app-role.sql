-- HeatLedger Database Initialization: Provision Restricted Non-Superuser Application Role
-- Strictly enforces PostgreSQL Row Level Security (RLS) with NOBYPASSRLS and NOSUPERUSER

CREATE EXTENSION IF NOT EXISTS postgis;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'heatledger_app_user') THEN
        CREATE ROLE heatledger_app_user WITH LOGIN PASSWORD 'heatledger_app_pass' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
    END IF;
END
$$;

-- Restricted runtime role gets USAGE (not CREATE) on public schema
GRANT USAGE ON SCHEMA public TO heatledger_app_user;

-- DML privileges only on all tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO heatledger_app_user;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO heatledger_app_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO heatledger_app_user;

-- Default privileges for tables, sequences, and functions created by the database owner
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO heatledger_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO heatledger_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO heatledger_app_user;
