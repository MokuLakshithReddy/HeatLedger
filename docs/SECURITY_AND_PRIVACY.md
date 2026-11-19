# Security & Privacy Engineering Specification

## 1. Compliance with the Digital Personal Data Protection (DPDP) Act, 2023 (India)

HeatLedger is engineered specifically around worker data sovereignty and strict compliance with the Indian DPDP Act:

1. **Purpose-Specific Notice & Consent:**
   - Location collection is disabled by default.
   - Separate consent records are stored for:
     - `LOCATION_TRACKING_DURING_SHIFT`
     - `EARNINGS_DOCUMENT_EXTRACTION`
     - `ANONYMIZED_CLIMATE_RESEARCH`
     - `ORGANISATION_REPORT_SHARING`
   - Every consent record captures consent text version, timestamp, user IP hash, and grant/revocation state.
2. **Immediate Consent Revocation Enforcement:**
   - When a worker revokes location tracking consent during an ongoing shift, the system immediately updates the shift record to set `location_tracking_enabled = False`.
   - Any subsequent location sample sent to `/shifts/{id}/location-samples` is rejected with HTTP 403 Forbidden.
3. **Right to Data Portability (Export):**
   - Implemented at `/api/v1/profiles/me/export`.
   - Returns a complete machine-readable JSON archive of all profile records, consent history, shifts, breaks, earnings entries, and reports.
4. **Right to Erasure (Account Deletion):**
   - Implemented at `DELETE /api/v1/profiles/me/delete`.
   - Immediately deactivates account and queues personal identifiers for cryptographic deletion.

---

## 2. Cross-Tenant Isolation & Least Privilege Access

- **IDOR Prevention:**
  - Every resource endpoint (`/shifts/{id}`, `/earnings/uploads/{id}`, `/evidence/reports/{id}`) explicitly verifies that the requested entity belongs to the authenticated worker (`worker_id = current_user.id`).
  - Cross-user access attempts return HTTP 404/403.
- **Organisation Access Boundaries:**
  - An organisation can **never** browse or query worker location histories, private shift logs, or unshared documents.
  - Access to a report requires an explicit, active `ShareGrant` record where:
    - `share_grants.organisation_id = user_organisation_id`
    - `share_grants.is_revoked = False`
    - `share_grants.expires_at > NOW()`
  - When a worker revokes a share grant, the revocation takes effect instantly on the database layer.

---

## 3. Cohort Privacy Safeguard (k-Anonymity)

- Regional heat and wage analytics for organisations enforce a strict **minimum cohort size of k ≥ 5**.
- If fewer than 5 distinct consented workers form a regional cohort, individual metrics are suppressed and a privacy safeguard notice is returned to prevent platform retaliation or de-anonymization.

---

## 4. Cryptographic Integrity Verification

- Uploaded financial files and generated PDF reports are hashed with SHA-256 upon ingestion/creation.
- The hash is stored in the database and embedded directly into the report metadata.
- **Verification Note:** A SHA-256 hash proves that a document has not been altered or tampered with since generation. It verifies file integrity, but does not independently certify the truth of third-party platform claims.
