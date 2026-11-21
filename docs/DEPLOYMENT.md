# HeatLedger Production Deployment & Infrastructure Guide

This guide describes how to deploy, configure, and maintain HeatLedger across containerized environments (Docker Compose, Kubernetes, AWS/GCP, or Vercel/Fly.io).

---

## 1. Environment Architecture

```
                    ┌────────────────────────┐
                    │ Cloudflare / CDN Proxy  │
                    │   (HSTS, WAF, SSL)     │
                    └───────────┬────────────┘
                                │
               ┌────────────────┴────────────────┐
               ▼                                 ▼
    ┌──────────────────────┐          ┌──────────────────────┐
    │ Next.js Web App      │          │ FastAPI API Backend  │
    │ (Port 3000)          │          │ (Port 8000)          │
    │ Non-root node user   │          │ Non-root heatledger  │
    └──────────────────────┘          └──────────┬───────────┘
                                                 │
                                ┌────────────────┴────────────────┐
                                ▼                                 ▼
                     ┌──────────────────────┐          ┌──────────────────────┐
                     │ PostgreSQL 16 PostGIS│          │ S3 / Private Storage │
                     │ Encrypted DB Volume  │          │ Encrypted AES-256    │
                     └──────────────────────┘          └──────────────────────┘
```

---

## 2. Production Environment Variables

Before starting HeatLedger in production, all environment variables are validated by `backend/app/core/env_validator.py`. Missing or insecure parameters will cause an immediate startup failure (fail-fast architecture).

### Mandatory Production Settings (`ENVIRONMENT=production`):

| Variable | Description | Example / Requirement |
|---|---|---|
| `ENVIRONMENT` | Target runtime environment | `production` |
| `APP_SECRET_KEY` | HMAC token signing secret | Minimum 32 random characters (never commit!) |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/heatledger` (SQLite rejected) |
| `DEMO_MODE` | Mock data seeding flag | Must be `false` in production |
| `CORS_ORIGINS` | Permitted web clients | Explicit domain list, e.g. `https://heatledger.org` |
| `STORAGE_BACKEND` | File storage provider | `s3` or `local` |
| `S3_BUCKET_NAME` | S3 bucket for private files | `heatledger-prod-private-vault` |
| `S3_REGION_NAME` | AWS / Object store region | `ap-south-1` (Hyderabad / Mumbai) |
| `AWS_ACCESS_KEY_ID` | Storage access key | Required if `STORAGE_BACKEND=s3` |
| `AWS_SECRET_ACCESS_KEY` | Storage secret key | Required if `STORAGE_BACKEND=s3` |
| `CDS_API_KEY` | Copernicus CDS ERA5 key | Required for real satellite climate ingest |
| `IMD_API_KEY` | India Met Dept API key | Required for AWS weather observations |

---

## 3. Docker Compose Deployment

Run the complete multi-tier system with persistent PostGIS and private storage:

```bash
# 1. Clone repository
git clone https://github.com/MokuLakshithReddy/HeatLedger.git
cd HeatLedger

# 2. Configure .env file
cp .env.example .env

# 3. Build and launch services
docker compose up -d --build

# 4. Run database migrations
docker compose exec backend alembic upgrade head
```

---

## 4. Container Security Hardening

1. **Non-Root Execution:**
   - Backend runs as UID 1000 (`heatledger`).
   - Web frontend runs as UID 1001 (`nextjs`).
2. **Read-Only Root Filesystem Ready:**
   - File uploads and PDF caches are routed to persistent volumes (`/app/uploads/private`).
3. **HTTP Security Headers Enforced:**
   - `Content-Security-Policy: default-src 'self'`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: strict-origin-when-cross-origin`

---

## 5. Database Roles & Migration Architecture (Least Privilege & RLS)

HeatLedger enforces strict privilege separation between schema migrations (DDL) and runtime application queries (DML with Row-Level Security):

### 5.1 Dual Database Connection Model

1. **`MIGRATION_DATABASE_URL` (Schema Owner):**
   - Connects as the database/schema owner role (e.g., `heatledger_owner`).
   - Has DDL privileges (`CREATE TABLE`, `ALTER TABLE`, `CREATE POLICY`, `SECURITY DEFINER` function management).
   - Used exclusively by Alembic during build/release deployment steps.
   - Example: `postgresql://heatledger_owner:OwnerSecret@postgres:5432/heatledger`

2. **`DATABASE_URL` (Runtime Application Role):**
   - Connects as the restricted application role (e.g., `heatledger_app_user`).
   - Configured with `NOBYPASSRLS`. All queries strictly adhere to Row-Level Security policies.
   - Has DML privileges only (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on application tables.
   - Example: `postgresql://heatledger_app_user:AppSecret@postgres:5432/heatledger`

### 5.2 Release Migration Workflow

In production Kubernetes / ECS / PaaS deployments:
- **Do not** run Alembic migrations inside the FastAPI application container startup script across multiple autoscaled replicas.
- **Run migrations as an isolated pre-deployment release job** prior to routing traffic to new application instances:
  ```bash
  # Execute schema migrations using owner credentials in an isolated release container
  alembic -c backend/alembic.ini upgrade head
  ```
- **Verify migration reversibility in CI/CD:**
  ```bash
  # Test schema rollback and re-application
  alembic -c backend/alembic.ini downgrade 001_initial_schema
  alembic -c backend/alembic.ini upgrade head
  ```
