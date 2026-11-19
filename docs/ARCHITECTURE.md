# HeatLedger System Architecture

> **Product Tagline:** Your work. Your conditions. Your evidence.  
> **Product Category:** Worker-owned climate exposure and earnings evidence platform.  
> **Primary Pilot Deployment:** Hyderabad, Telangana, India.

---

## 1. High-Level Architecture Overview

HeatLedger is structured as a modular monorepo containing:
1. **Backend Service:** High-performance Python / FastAPI versioned REST API (`/api/v1/`) with SQLAlchemy ORM, Alembic migrations, deterministic climate calculation engine, and background document intelligence pipeline.
2. **Web Portal (Next.js 14 App Router):** Accessible, modern dashboard designed for Trade Unions (e.g. Telangana Gig and Platform Workers Union) and Welfare Boards to review worker-consented evidence dossiers, manage casework, and analyze regional heat trends with k-anonymity safeguards.
3. **Mobile Application (Expo / React Native):** Cross-platform mobile app built for outdoor gig delivery workers, featuring large touch targets, high contrast, offline resilience, and multilingual support in English, Telugu (`te`), and Hindi (`hi`).
4. **Data Layer (PostgreSQL + PostGIS):** Relational schema with 20 normalized entities, spatial indexing for meteorological station matching, and Row-Level Security (RLS) policies.

```
                      ┌──────────────────────────────────────────────┐
                      │             HeatLedger Architecture          │
                      └──────────────────────┬───────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             │                               │                               │
             ▼                               ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
    │  Mobile Client  │             │   Web Portal    │             │  Admin / System │
    │ (React Native / │             │    (Next.js     │             │   Diagnostics   │
    │  Expo Router)   │             │   App Router)   │             │  & Audit Engine │
    └────────┬────────┘             └────────┬────────┘             └────────┬────────┘
             │                               │                               │
             └───────────────────────┬───────┴───────────────────────────────┘
                                     │ JSON API (v1)
                                     ▼
                      ┌──────────────────────────────┐
                      │     FastAPI Core Engine      │
                      │   - JWT Auth & RBAC          │
                      │   - DPDP Consent Service     │
                      │   - Shift & Break Service    │
                      │   - Scoped Share Grants      │
                      └──────┬───────────────┬───────┘
                             │               │
             ┌───────────────┴────┐     ┌────┴───────────────────────────┐
             ▼                    ▼     ▼                                ▼
    ┌─────────────────┐  ┌───────────────┐  ┌─────────────────┐  ┌──────────────────┐
    │ Climate Engine  │  │ Earnings OCR  │  │ Evidence Engine │  │ Report Generator │
    │ - IMD Adapter   │  │ - Pydantic V2 │  │ - Chronological │  │ - ReportLab PDF  │
    │ - ERA5 Reanal.  │  │ - Multi-layout│  │   Ordering      │  │ - SHA-256 Hash   │
    │ - Rothfusz HI   │  │ - Gemini LLM  │  │ - Provenance    │  │ - Cryptographic  │
    │ - sWBGT Proxy   │  │ - Worker Rev. │  │ - Anomaly Flags │  │   Integrity Seal │
    └─────────────────┘  └───────────────┘  └─────────────────┘  └──────────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    PostgreSQL + PostGIS      │
                      │    20 Normalized Tables      │
                      │    Row Level Security (RLS)  │
                      └──────────────────────────────┘
```

---

## 2. Evidence Categorization & Provenance Model

To ensure transparency and prevent false claims, HeatLedger strictly segregates all events into typed categories:

| Evidence Category | Description | Source / Provenance |
| :--- | :--- | :--- |
| `WORKER_ACTION` | Shift start, pause, resume, end actions | Worker client timestamp |
| `LOCATION_OBSERVATION` | GPS coordinates during consented shifts | On-device GPS receiver (Accuracy in meters) |
| `WEATHER_OBSERVATION` | Ambient temperature, relative humidity, wind, solar | IMD AWS / Begumpet Observatory |
| `HISTORICAL_ENVIRONMENTAL_DATA` | Gridded meteorological reanalysis | Copernicus CDS ERA5-Land (9km grid) |
| `ESTIMATED_EXPOSURE` | Computed Heat Index (°C) and sWBGT proxy | Deterministic formula with spatial match distance |
| `WORKER_DECLARED_BREAK` | Rest, hydration, meal, and shelter stops | Worker declaration (Never inferred from missing GPS) |
| `DOCUMENT_UPLOAD` | Original payout slips and tax statements | SHA-256 hashed private upload |
| `AI_EXTRACTED_VALUE` | OCR and LLM structured extraction candidates | Unconfirmed extraction model output |
| `WORKER_CONFIRMED_VALUE` | Verified and approved financial values | Worker explicit confirmation |
| `ANALYTICAL_FLAG` | High climate exposure and consistency notices | Deterministic rule engine |

---

## 3. Database Schema Overview (20 Entities)

1. `users`: System identity, role, language preference, auth credentials.
2. `worker_profiles`: Vehicle type, platform affiliations, city, tracking preferences.
3. `organisations`: Trade unions, NGOs, and welfare boards.
4. `organisation_members`: Role-based membership within approved organizations.
5. `consent_records`: DPDP-compliant purpose-specific consent grants and revocations.
6. `shifts`: Shift lifecycle with state transition validation.
7. `location_samples`: Time-stamped GPS samples recorded during active shifts.
8. `break_events`: Worker-declared rest periods.
9. `weather_observations`: Station observations with spatial resolution and freshness.
10. `exposure_intervals`: Hourly exposure computations with risk levels.
11. `earnings_uploads`: Original uploaded payout slips with SHA-256 hashes.
12. `earning_entries`: Structured line-item earnings with confirmation status.
13. `analysis_runs`: Audit records of background climate and earnings jobs.
14. `evidence_reports`: Immutable report records with SHA-256 integrity hash.
15. `report_sources`: Foreign key attribution of every input in a report.
16. `share_grants`: Scoped, revocable sharing permissions granted to organizations.
17. `cases`: Casework records opened by trade unions for welfare claims.
18. `case_notes`: Chronological caseworker notes.
19. `audit_logs`: Tamper-evident system security audit logs.
20. `processing_jobs`: Background asynchronous task records.
