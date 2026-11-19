# HeatLedger Implementation Plan & Architecture Specification

## Product Overview
- **Name:** HeatLedger
- **Tagline:** Your work. Your conditions. Your evidence.
- **Category:** Worker-owned climate exposure and earnings evidence platform.
- **Target Users:** Food delivery workers, grocery delivery, ride-hailing drivers, logistics & outdoor workers, worker unions & welfare organisations.
- **Initial Location:** Hyderabad, Telangana, India.
- **Languages:** English, Telugu, Hindi.

## Architectural Boundaries & Principles
1. **Worker Data Sovereignty:** Worker owns all primary records (shifts, breaks, location, uploaded earnings). Sharing with organizations requires explicit, scoped, revocable consent grants.
2. **Transparent Provenance:** No blurred data types. Timeline distinguishes:
   - WORKER_ACTION
   - LOCATION_OBSERVATION
   - WEATHER_OBSERVATION
   - HISTORICAL_ENVIRONMENTAL_DATA
   - ESTIMATED_EXPOSURE
   - WORKER_DECLARED_BREAK
   - DOCUMENT_UPLOAD
   - AI_EXTRACTED_VALUE
   - WORKER_CONFIRMED_VALUE
   - ANALYTICAL_FLAG
3. **No False Claims:** Never claim environmental correlation proves legal liability or medical causation. Reports clearly labeled as non-government-certified evidence records with SHA-256 integrity hashes.
4. **Resilient Data Providers:** Weather provider abstraction with IMD API adapter, Copernicus ERA5-Land adapter, and validated Hyderabad demo fixtures. Honest states when providers are unavailable.
5. **Robust Multilingual Architecture:** Complete i18n support for English, Telugu (`te`), and Hindi (`hi`).

## Work Breakdown Stages
- **Stage 1:** Monorepo scaffolding, environment configuration, database models & Alembic migrations (all 19 entities), PostGIS support.
- **Stage 2:** Backend core: Auth, security (JWT + API key + RLS concepts), audit logging, and CRUD services for Profiles, Consents, Shifts, Breaks, Location Samples.
- **Stage 3:** Climate Engine & Weather Providers: Provider abstraction (Base, IMD, ERA5-Land, Hyderabad Demo Fixture), Heat Index, humidex/WBGT proxy, spatiotemporal matching, exposure calculation.
- **Stage 4:** Earnings Document Intelligence: File upload with SHA-256 hash, private storage, OCR text extraction, structured extraction with schema validation, worker review and confirmation workflow.
- **Stage 5:** Evidence Correlation & PDF Report Generator: Ordered timeline builder, anomaly/flag detector, PDF report generator with SHA-256 integrity hashing and source attribution.
- **Stage 6:** Sharing, Organisation Portal & System Ops APIs: Scoped share grants, instant revocation, organisation case management, aggregate cohort analytics (k-anonymity >= 5), admin health endpoints.
- **Stage 7:** Web Application (Next.js): Organisation portal, case review, aggregate analytics, admin health dashboard, i18n support, responsive accessible UI.
- **Stage 8:** Mobile Application (React Native / Expo): Onboarding, dashboard, shift & break controls, optional location recording with clear consent toggle, environmental exposure screen, earnings upload & confirmation, evidence timeline & PDF viewer, settings (consent, data export, languages: EN, TE, HI).
- **Stage 9:** Testing Suite: Unit tests, integration tests, E2E scenarios matching Section 18.
- **Stage 10:** Documentation & Verification: `.env.example`, Docker Compose, complete documentation suite (Architecture, Security & DPDP, Climate Methodology, Demo Workflow).
