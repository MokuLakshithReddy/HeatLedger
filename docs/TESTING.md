# Automated Testing & Verification Suite

HeatLedger maintains a comprehensive automated testing suite covering unit math formulas, integration permissions, security regressions, and end-to-end user journeys.

---

## 1. Running the Test Suites

Execute the test suite from the root directory using the virtual environment:

```bash
# Run all tests with verbose output
backend/venv/Scripts/python.exe -m pytest backend/tests -v

# Run security regression tests specifically
backend/venv/Scripts/python.exe -m pytest backend/tests/security/test_security_regressions.py -v

# Run climate unit tests
backend/venv/Scripts/python.exe -m pytest backend/tests/unit/test_climate.py -v
```

---

## 2. Test Coverage Breakdown

### Security Regressions (`backend/tests/security/test_security_regressions.py`):
- `test_sec_01`: Prevents public registration of `system_admin`.
- `test_sec_02`: Prevents public registration of `org_admin`.
- `test_sec_03`: Prevents ordinary workers from approving organisations.
- `test_sec_04`: Unapproved organisations are blocked from worker dossiers.
- `test_sec_05`: Worker cross-tenant isolation (IDOR protection).
- `test_sec_06`: Organisation cross-tenant isolation.
- `test_sec_07`: Unshared reports are inaccessible to third parties.
- `test_sec_08`: Expired sharing grants are denied immediately.
- `test_sec_09`: Revoked sharing grants are denied immediately.
- `test_sec_10`: Revoked location consent stops active shift GPS collection.
- `test_sec_11`: Revoked earnings consent rejects document extraction.
- `test_sec_12`: Invalid production secrets prevent application startup.
- `test_sec_13`: Demo data seeding is strictly blocked in production.
- `test_sec_14`: Path traversal attempts are sanitized.

### Climate & Calculation Units (`backend/tests/unit/test_climate.py`):
- Rothfusz regression heat index benchmarks verified against NOAA standards.
- Australian Bureau of Meteorology (BOM) simplified WBGT proxy formula validated.
- Haversine geodesic distance accuracy verified.

### Earnings & Parsing (`backend/tests/unit/test_earnings.py`):
- CSV parsing and line-item extraction.
- Deterministic heuristic extraction without double-counting.
- Upload lifecycle and worker confirmation.

### Shifts & Lifecycle (`backend/tests/unit/test_shifts.py`):
- Active shift start and overlapping shift prevention.
- Break recording and pause/resume duration deduction.
- Manual shift correction requires descriptive reason (minimum 5 chars).

### Full End-to-End Scenarios (`backend/tests/e2e/test_full_e2e_scenarios.py`):
- Complete worker journey from shift start to PDF evidence dossier generation and union sharing.
