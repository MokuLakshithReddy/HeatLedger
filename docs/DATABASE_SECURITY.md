# Database Architecture & Security Controls

HeatLedger employs PostgreSQL 16 with PostGIS extensions to manage geospatial shift tracks, meteorological station observations, and sensitive worker earnings data.

---

## 1. Schema Isolation & Foreign Key Cascades

All entities enforce strict database-level referential integrity:

- **`User` (Core Tenant):**
  - Primary identification key (`UUID`).
  - Strict roles: `worker`, `org_admin`, `system_admin`.
  - Roles cannot be self-escalated via public registration endpoints.
- **`ConsentRecord`:**
  - Purpose-specific tracking per worker.
  - Cascade rules ensure audit trail preservation while respecting deletion requests.
- **`Shift` & `Break`:**
  - Timestamps stored in UTC (`TIMESTAMP WITH TIME ZONE`).
  - Spatial columns use PostGIS `GEOMETRY(Point, 4326)`.
- **`EarningsUpload` & `EarningEntry`:**
  - Files stored outside DB with SHA-256 fingerprint linkage.
  - Monetary values stored using `NUMERIC(10, 2)` (Python `Decimal`) to eliminate floating-point representation drift.

---

## 2. Row-Level & Application Access Control

1. **Worker Isolation:**
   - Every read and write query in `shift_service.py`, `break_service.py`, and `pipeline.py` filters explicitly on `worker_id == current_user.id`.
   - SQLite and PostgreSQL queries are immune to user ID tampering.
2. **Organisation Access Boundary:**
   - Organisations query exclusively through the `ShareGrant` join table.
   - Any query attempting to access an unshared or revoked report returns HTTP 404 / 403.
   - Direct querying of `LocationSample` or raw GPS by organisations is structurally prevented in code and query design.
3. **Admin Privilege Separation:**
   - Only users with verified `role == "system_admin"` can invoke `/api/v1/admin/*` endpoints.
   - Public registration always forces `role = "worker"`. Organisation approval requires explicit admin action via `POST /api/v1/admin/organisations/{id}/approve`.
