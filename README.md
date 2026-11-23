# HeatLedger

> **Your work. Your conditions. Your evidence.**  
> *Worker-owned climate exposure and earnings evidence platform.*  
> Primary Initial Geography: **Hyderabad, Telangana, India**  
> Supported Languages: **English**, **తెలుగు (Telugu)**, **हिन्दी (Hindi)**

---

## 1. Product Mission & Identity

Workers frequently have fragmented records of their working hours, environmental conditions, rest periods, and platform earnings. **HeatLedger** connects these separate records into an independent, transparent, and cryptographically verifiable evidence timeline.

### Core Capabilities:
1. **Shift & Rest Tracking:** One-touch shift start/pause/end with deterministic deduction of worker-declared rest and hydration breaks.
2. **Consented Location Recording:** Zero hidden tracking. GPS fixes collected strictly during active, explicitly consented shifts.
3. **Accredited Environmental Matching:** Live weather from IMD and historical reanalysis from Copernicus ERA5-Land matched by time and geographic proximity.
4. **Transparent Indicators:** Rothfusz Heat Index and simplified outdoor shade sWBGT proxy calculations with clear scientific caveats.
5. **Earnings Document Intelligence:** Upload payout slips (PDF/JPG/PNG/CSV), calculate SHA-256 integrity hashes, extract line items with OCR/LLM models, and require mandatory worker confirmation.
6. **Chronological Timeline & Verifiable PDF Dossiers:** Ordered evidence timeline across 10 typed categories, compiled into downloadable PDF dossiers with embedded SHA-256 fingerprints.
7. **Scoped & Revocable Sharing:** Workers grant purpose-specific access to trade unions (e.g. TGPWU). Revoking a grant immediately terminates access.
8. **Cohort Anonymity Safeguards:** Regional heat impact analytics enforce a strict minimum cohort size ($k \ge 5$) to prevent platform retaliation.

---

## 2. Monorepo Architecture

```
Idea_Forge_NIAT/
├── backend/                  # FastAPI 0.110+, Python 3.12, SQLAlchemy 2.0, Alembic
│   ├── app/
│   │   ├── api/v1/           # Versioned REST API endpoints
│   │   ├── climate/          # Rothfusz Heat Index & sWBGT calculation engine
│   │   ├── earnings/         # Document OCR, Gemini LLM parsing & confirmation
│   │   ├── evidence/         # Chronological evidence correlator & anomaly flags
│   │   ├── models/           # 20 SQLAlchemy entities & PostGIS support
│   │   ├── providers/        # IMD, ERA5-Land, & Hyderabad Demo Fixture adapters
│   │   ├── reports/          # ReportLab PDF generator & SHA-256 seal
│   │   ├── schemas/          # Pydantic V2 request & response contracts
│   │   └── services/         # Shift, Break, Consent, Share, and Org services
│   ├── alembic/              # Database migration versions & RLS policies
│   └── tests/                # Unit tests, integration tests, & E2E scenarios 1-7
├── web/                      # Next.js 14 App Router, TypeScript, Tailwind CSS
│   └── src/
│       ├── app/              # Portal, Cohort Analytics, Admin Ops, Landing
│       ├── components/       # Accessible UI & EvidenceTimelineView
│       └── lib/              # i18n (en, te, hi) & API client
├── mobile/                   # Expo ~51, React Native 0.74, Expo Router, TypeScript
│   └── app/                  # (tabs) for Home, Shifts, Heat, Earnings, Dossier, Settings
├── shared/                   # Shared TypeScript contracts and domain models
├── docker-compose.yml        # PostgreSQL + PostGIS, Backend, & Web orchestration
└── docs/                     # Architecture, Security & DPDP, Climate Methodology, Demo
```

---

## 3. Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Docker (optional for PostgreSQL + PostGIS)

### Backend Setup
```bash
# 1. Activate Python virtual environment
cd backend
python -m venv venv
venv\Scripts\activate # On Windows (or source venv/bin/activate on Linux/macOS)
pip install -r requirements.txt

# 2. Run database migrations (creates 20 tables & indexes)
python -m alembic -c backend/alembic.ini upgrade head

# 3. Seed demonstration data for Hyderabad
python -m backend.app.seed_demo

# 4. Run automated tests (20 unit, integration, and E2E tests)
python -m pytest backend/tests -v

# 5. Start development API server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation: `http://localhost:8000/docs`

### Web Portal Setup
```bash
cd web
npm install
npm run dev
```
Web Application: `http://localhost:3000`

### Mobile App Setup
```bash
cd mobile
npm install
npx expo start
```

---

## 4. Demonstration Accounts (Hyderabad Pilot / Test Environment)

> [!NOTE]
> Demo accounts and seed scripts (`backend/app/seed_demo.py`) are strictly restricted to local and staging environments. The production environment validator (`backend/app/core/env_validator.py`) raises a critical exception if demo mode is enabled in production.

| Role | Email | Default Local Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Worker** | `demo.worker@heatledger.local` | `DemoWorker123!` | Delivery partner in Hyderabad (Swiggy/Zomato) |
| **Organisation** | `advocate@telanganaworkers.org` | `TelanganaUnion123!` | Telangana Gig & Platform Workers Union (TGPWU) |
| **Admin** | `admin@heatledger.local` | `HeatLedgerAdmin2026!` | Operations & telemetry auditor |

---

## 5. Verification & Test Suite

HeatLedger includes **34 automated tests** across unit, integration, end-to-end, and security regression suites:

- **Security Regressions (SEC-01 through SEC-14):**
  - Privilege escalation prevention on public registration (SEC-01 & SEC-02)
  - Ordinary user cannot approve organisation (SEC-03)
  - Unapproved organisations blocked from worker dossiers (SEC-04)
  - Strict cross-tenant worker & organisation isolation (SEC-05 & SEC-06)
  - Unshared and expired report denial (SEC-07 & SEC-08)
  - Immediate share revocation enforcement (SEC-09)
  - Immediate mid-shift GPS collection halt on consent revocation (SEC-10)
  - Earnings extraction rejection on consent revocation (SEC-11)
  - Insecure production secrets fail fast on startup (SEC-12)
  - Demo seeding strictly rejected in production (SEC-13)
  - Path traversal attempts sanitized (SEC-14)
- **E2E User Journeys (Scenarios 1 through 7):**
  - Shift and break lifecycle with break time deduction
  - Earnings statement upload, OCR parsing, and worker verification
  - Environmental matching and PDF evidence dossier generation
  - Scoped sharing with worker organisations and immediate revocation
  - Meteorological provider failover and resilience
- **Scientific Unit Testing:**
  - Rothfusz regression heat index calculations
  - Australian BOM simplified WBGT proxy formula
  - Haversine geodesic distance calculations

Run all tests:
```bash
python -m pytest backend/tests -v
```
Result: **34 passed in 8.32s**

---

## 6. License

This repository is licensed under the [MIT License](LICENSE).
