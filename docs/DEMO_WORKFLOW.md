# HeatLedger Demonstration & Verification Workflow

This guide details how to run, inspect, and demonstrate HeatLedger locally using the pre-seeded Hyderabad demonstration fixtures.

---

## 1. Quick Start Commands

### Backend Service
```bash
# 1. Activate Python virtual environment
cd backend
source venv/bin/activate # or backend\venv\Scripts\activate on Windows

# 2. Run migrations
python -m alembic -c backend/alembic.ini upgrade head

# 3. Seed demonstration data (Hyderabad pilot)
python -m backend.app.seed_demo

# 4. Start the FastAPI server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation is available at: **http://localhost:8000/docs**

### Web Application (Organisation Portal)
```bash
cd web
npm run dev
```
Access the web portal at: **http://localhost:3000**

---

## 2. Pre-Seeded Demonstration Accounts

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Worker Account** | `demo.worker@heatledger.local` | `DemoWorker123!` | Raju K., Swiggy/Zomato partner in Hyderabad (Begumpet / Hitec City) |
| **Organisation Admin** | `advocate@telanganaworkers.org` | `TelanganaUnion123!` | Priya V., Telangana Gig and Platform Workers Union (TGPWU) |
| **System Auditor** | `admin@heatledger.local` | `HeatLedgerAdmin2026!` | Administrative telemetry and audit log reviewer |

---

## 3. End-to-End Walkthrough Scenarios

### Workflow A: Worker Shift Tracking & Climate Correlation
1. Log in on the worker mobile app using `demo.worker@heatledger.local`.
2. Tap **Start Shift** with location tracking enabled.
3. Observe live Hyderabad Heat Index (e.g. 47.8°C Extreme Heat alert for Begumpet / Charminar stations).
4. Tap **Take Break** → select **Hydration** → record "Electrolyte stop at shaded booth".
5. Conclude break and end shift.
6. Open **Dossiers** tab → tap **Generate 7-Day Evidence Report**.
7. Download verifiable PDF and observe embedded SHA-256 hash.

### Workflow B: Worker-to-Union Dossier Sharing & Revocation
1. On the worker app, select the generated report (`HL-HYD-...`).
2. Tap **Share with TGPWU Union**.
3. Open the Web Portal at **http://localhost:3000/portal**.
4. Log in as `advocate@telanganaworkers.org`.
5. Observe the worker's shared dossier appear on the casework desk.
6. Click **Download Verifiable PDF** to review the tamper-evident document.
7. Return to the worker app and tap **Revoke Union Access**.
8. Refresh the web portal and attempt to download the report again: access is immediately blocked with HTTP 403 Forbidden.

### Workflow C: Cohort Anonymity Safeguard Verification
1. On the web portal, navigate to **Cohort Analytics** (`/analytics`).
2. Observe the k-anonymity safeguard message (k ≥ 5): individual identifiers are suppressed when the cohort has fewer than 5 consented workers to protect against platform retaliation.
