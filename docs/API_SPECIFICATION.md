# HeatLedger API Specification (`/api/v1`)

All endpoints are versioned under `/api/v1/`. Timestamps are accepted and returned formatted in ISO 8601 UTC.

---

## 1. Authentication & Profiles

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new worker or organisation account | No |
| `POST` | `/api/v1/auth/login` | Authenticate with email/phone & password | No |
| `GET` | `/api/v1/profiles/me` | Fetch authenticated profile details | Yes |
| `PATCH` | `/api/v1/profiles/me/preferences` | Update language (`en`, `te`, `hi`) or name | Yes |
| `GET` | `/api/v1/profiles/me/consents` | List active purpose-specific consent records | Yes |
| `POST` | `/api/v1/profiles/me/consents` | Grant or update purpose-specific consent | Yes |
| `POST` | `/api/v1/profiles/me/consents/revoke` | Revoke consent immediately | Yes |
| `GET` | `/api/v1/profiles/me/export` | Export full personal portfolio (DPDP Act) | Yes |
| `DELETE` | `/api/v1/profiles/me/delete` | Request account deactivation and purging | Yes |

---

## 2. Shift & Break Management

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/shifts/active` | Get active shift and today's accumulated totals | Yes (Worker) |
| `POST` | `/api/v1/shifts/start` | Start new shift (Rejects overlapping shifts with 409) | Yes (Worker) |
| `POST` | `/api/v1/shifts/{id}/pause` | Transition shift to `PAUSED` | Yes (Worker) |
| `POST` | `/api/v1/shifts/{id}/resume` | Resume shift to `ACTIVE`, concluding open breaks | Yes (Worker) |
| `POST` | `/api/v1/shifts/{id}/end` | End shift, computing working & break minutes | Yes (Worker) |
| `POST` | `/api/v1/shifts/{id}/correct` | Manually correct timestamps with audited reason | Yes (Worker) |
| `GET` | `/api/v1/shifts` | List shift history | Yes (Worker) |
| `GET` | `/api/v1/shifts/{id}` | Get detailed shift record | Yes (Worker) |
| `POST` | `/api/v1/shifts/{id}/breaks` | Declare a rest/hydration/meal break | Yes (Worker) |
| `POST` | `/api/v1/breaks/{id}/end` | Conclude an ongoing break | Yes (Worker) |

---

## 3. Location Recording (Consented Shifts Only)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/shifts/{id}/location-samples` | Record GPS sample during consented active shift | Yes (Worker) |
| `POST` | `/api/v1/shifts/{id}/location-samples/batch` | Record batch of location fixes | Yes (Worker) |
| `GET` | `/api/v1/shifts/{id}/location-samples` | Retrieve shift location samples | Yes (Worker) |

---

## 4. Climate Intelligence

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/climate/observations` | Get current observation (lat, lon) | Yes |
| `GET` | `/api/v1/climate/shifts/{id}/exposure` | Compute hourly heat index & sWBGT exposure | Yes (Worker) |
| `GET` | `/api/v1/climate/providers/status` | Diagnostics of IMD, ERA5-Land, & Demo providers | Yes |

---

## 5. Earnings Intelligence

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/earnings/uploads` | Upload statement file (PDF/JPG/PNG/CSV) | Yes (Worker) |
| `GET` | `/api/v1/earnings/uploads` | List uploaded statements | Yes (Worker) |
| `GET` | `/api/v1/earnings/entries` | List extracted payout entries | Yes (Worker) |
| `POST` | `/api/v1/earnings/entries/{id}/confirm` | Worker reviews and confirms payout figures | Yes (Worker) |

---

## 6. Evidence Timeline & PDF Reports

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/evidence/timelines` | Retrieve chronological, categorized timeline | Yes (Worker) |
| `POST` | `/api/v1/evidence/reports` | Compile verifiable evidence dossier | Yes (Worker) |
| `GET` | `/api/v1/evidence/reports` | List generated evidence reports | Yes (Worker) |
| `GET` | `/api/v1/evidence/reports/{id}` | Get report metadata and SHA-256 hash | Yes (Worker) |
| `GET` | `/api/v1/evidence/reports/{id}/download` | Download verifiable PDF with hash header | Yes (Worker) |

---

## 7. Data Sharing & Organisation Advocacy

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/shares` | Worker grants scoped access to an organisation | Yes (Worker) |
| `GET` | `/api/v1/shares` | List worker's share grants | Yes (Worker) |
| `POST` | `/api/v1/shares/{id}/revoke` | Revoke organisation access immediately | Yes (Worker) |
| `GET` | `/api/v1/organisations` | List approved organisations | Yes |
| `GET` | `/api/v1/organisations/{id}/reports` | List worker-shared reports for org | Yes (Org Member) |
| `GET` | `/api/v1/organisations/{id}/reports/{rid}/download` | Download shared report PDF | Yes (Org Member) |
| `GET` | `/api/v1/organisations/{id}/cases` | List organisation casework records | Yes (Org Member) |
| `POST` | `/api/v1/organisations/{id}/cases` | Open case from a shared report | Yes (Org Member) |
| `POST` | `/api/v1/organisations/{id}/cases/{cid}/notes` | Add note to case | Yes (Org Member) |
| `GET` | `/api/v1/organisations/{id}/analytics` | Cohort heat analytics (k ≥ 5 safeguard) | Yes (Org Member) |
