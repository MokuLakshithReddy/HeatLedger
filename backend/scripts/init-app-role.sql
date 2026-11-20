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

GRANT USAGE, CREATE ON SCHEMA public TO heatledger_app_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO heatledger_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO heatledger_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO heatledger_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO heatledger_app_user;
