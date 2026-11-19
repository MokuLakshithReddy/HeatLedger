# Data Retention, Portability & DPDP Deletion Policy

Under the Digital Personal Data Protection (DPDP) Act, 2023, gig workers have explicit rights regarding consent lifecycle, data portability, and right to erasure.

---

## 1. Consent Purpose Lifecycle

HeatLedger maintains separate consent records for each discrete processing purpose:

1. `LOCATION_TRACKING_DURING_SHIFT`:
   - Enables fine-grained GPS sampling during active shifts.
   - Workers may revoke at any time. When revoked, ongoing shifts immediately stop location collection.
2. `EARNINGS_PROCESSING`:
   - Authorizes OCR and AI parsing of uploaded platform slips.
   - Revocation prevents future document analysis.
3. `ANONYMIZED_RESEARCH`:
   - Permits aggregated heat exposure calculations in regional union policy reports subject to $k \ge 5$ anonymity.
4. `ORGANISATION_REPORT_SHARING`:
   - Authorizes specific approved worker organisations to review individual evidence reports for 30 days.

---

## 2. Right to Data Portability (Export)

- **Endpoint:** `GET /api/v1/profiles/me/export`
- **Output:** Machine-readable JSON package containing:
  - User profile and contact details.
  - Complete consent grant and revocation history.
  - All shift records, pause/resume logs, and declared breaks.
  - Extracted earnings entries and upload metadata.
  - Generated evidence reports and active sharing grants.

---

## 3. Right to Erasure & Deletion Workflow

- **Endpoint:** `DELETE /api/v1/profiles/me/delete`
- **Procedure:**
  1. Authenticates requesting worker.
  2. Revokes all active organisation share grants instantly.
  3. Deactivates user account and sets `is_active = False`.
  4. Deletes uploaded source slips and generated PDF dossiers from private storage.
  5. Queues database identifiers for pseudonymization or deletion in accordance with legal requirements.
