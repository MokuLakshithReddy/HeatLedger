/**
 * Authoritative DPDP Consent Resolution for HeatLedger
 * Rule: Evaluate the latest applicable consent record for each purpose.
 * A newer revocation must override an older grant.
 */

export interface ConsentRecordItem {
  id: string;
  purpose: string;
  is_granted: boolean;
  version?: string;
  granted_at?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
}

const PURPOSE_ALIASES: Record<string, string> = {
  EARNINGS_PROCESSING: "EARNINGS_DOCUMENT_EXTRACTION",
  EARNINGS_DOCUMENT_EXTRACTION: "EARNINGS_DOCUMENT_EXTRACTION",
  LOCATION_TRACKING: "LOCATION_TRACKING_DURING_SHIFT",
  LOCATION_TRACKING_DURING_SHIFT: "LOCATION_TRACKING_DURING_SHIFT",
  ORGANISATION_SHARING: "ORGANISATION_REPORT_SHARING",
  ORGANISATION_REPORT_SHARING: "ORGANISATION_REPORT_SHARING",
  ANONYMIZED_RESEARCH: "ANONYMIZED_CLIMATE_RESEARCH",
  ANONYMIZED_CLIMATE_RESEARCH: "ANONYMIZED_CLIMATE_RESEARCH",
};

export function normalizeConsentPurpose(rawPurpose: string): string {
  const key = rawPurpose.trim().toUpperCase().replace(/ /g, "_");
  return PURPOSE_ALIASES[key] || key;
}

export function isConsentActive(consents: ConsentRecordItem[] | null | undefined, targetPurpose: string): boolean {
  if (!Array.isArray(consents) || consents.length === 0) {
    return false;
  }

  const normalizedTarget = normalizeConsentPurpose(targetPurpose);

  // Sort latest first by date (created_at, granted_at, or revoked_at)
  const sorted = [...consents].sort((a, b) => {
    const timeA = new Date(a.created_at || a.granted_at || a.revoked_at || 0).getTime();
    const timeB = new Date(b.created_at || b.granted_at || b.revoked_at || 0).getTime();
    return timeB - timeA;
  });

  // Find the single latest record for this purpose
  const latestRecord = sorted.find((c) => normalizeConsentPurpose(c.purpose) === normalizedTarget);

  if (!latestRecord) {
    return false;
  }

  // Active only if explicitly granted AND not revoked
  return Boolean(latestRecord.is_granted && !latestRecord.revoked_at);
}
