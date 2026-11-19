# AI Financial Extraction & OCR Pipeline

HeatLedger extracts platform earnings from delivery slips (Swiggy, Zomato, Porter, Uber) using a dual-engine architecture:
1. **Deterministic RegEx / Heuristic Classifier:** Fast, local, reliable for structured text and CSV statements.
2. **LLM / Gemini 1.5 Structured Output:** Multimodal extraction for complex scanned or photographic statements.

---

## 1. Safety & Prevention of Financial Double-Counting (EARN-04)

Previous implementations risked counting duplicate line items when aggregating earnings statements. The production pipeline implements:

1. **Strict Single-Classification per Line:**
   - Every text line or JSON token is classified into exactly ONE category:
     - `gross_pay` (Base delivery fees + distance pay)
     - `tip` (Direct customer gratuity)
     - `bonus_incentive` (Peak rain surge, midnight bonus, heat incentive)
     - `deduction` (Penalty, insurance, gear charge)
2. **Exact Reconciliation Formula:**
   $$\text{Calculated Net} = \text{Gross Pay} + \text{Tips} + \text{Incentives} - \text{Deductions}$$
   $$\text{Discrepancy} = |\text{Platform Claimed Net} - \text{Calculated Net}|$$
3. **Audit Trail & Discrepancy Logging:**
   - If the platform-stated net payout differs from the sum of components by > ₹0.01, a discrepancy warning is logged with detailed line-item attribution.

---

## 2. File Ingestion & Security Validation

1. **Magic Byte Verification:**
   - Rejects malicious file extension spoofing:
     - PDF: `%PDF-`
     - PNG: `\x89PNG\r\n\x1a\n`
     - JPEG: `\xff\xd8\xff`
2. **Size Limits & Path Traversal Prevention:**
   - Max file size: 10MB (`MAX_UPLOAD_SIZE_BYTES`).
   - Storage filenames use SHA-256 digests (`{sha256}.{ext}`) with strict sanitization of user directory paths.
3. **Pre-Extraction Worker Consent Check:**
   - Before processing files, `ConsentService` verifies that the worker has not revoked `EARNINGS_PROCESSING` consent.
