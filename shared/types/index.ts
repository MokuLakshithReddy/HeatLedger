/**
 * HeatLedger - Shared Types & Domain Contracts
 * "Your work. Your conditions. Your evidence."
 */

export type UserRole = 'worker' | 'organisation_admin' | 'organisation_viewer' | 'system_admin';

export type SupportedLanguage = 'en' | 'te' | 'hi';

export type ShiftStatus = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';

export type BreakType = 'REST' | 'HYDRATION' | 'MEAL' | 'SHELTER' | 'OTHER';

export type EvidenceCategory =
  | 'WORKER_ACTION'
  | 'LOCATION_OBSERVATION'
  | 'WEATHER_OBSERVATION'
  | 'HISTORICAL_ENVIRONMENTAL_DATA'
  | 'ESTIMATED_EXPOSURE'
  | 'WORKER_DECLARED_BREAK'
  | 'DOCUMENT_UPLOAD'
  | 'AI_EXTRACTED_VALUE'
  | 'WORKER_CONFIRMED_VALUE'
  | 'ANALYTICAL_FLAG';

export type ConsentPurpose =
  | 'LOCATION_TRACKING_DURING_SHIFT'
  | 'EARNINGS_DOCUMENT_EXTRACTION'
  | 'ANONYMIZED_CLIMATE_RESEARCH'
  | 'ORGANISATION_REPORT_SHARING';

export type HeatIndexRiskCategory = 'LOW' | 'CAUTION' | 'EXTREME_CAUTION' | 'DANGER' | 'EXTREME_DANGER';

export interface LocationSample {
  id: string;
  shift_id: string;
  latitude: number;
  longitude: number;
  accuracy_meters: number;
  altitude_meters?: number | null;
  speed_mps?: number | null;
  recorded_at: string; // ISO 8601 UTC
}

export interface BreakEvent {
  id: string;
  shift_id: string;
  started_at: string;
  ended_at?: string | null;
  break_type: BreakType;
  worker_notes?: string | null;
  is_worker_declared: true;
}

export interface Shift {
  id: string;
  worker_id: string;
  status: ShiftStatus;
  started_at: string;
  ended_at?: string | null;
  total_working_minutes: number;
  total_break_minutes: number;
  location_tracking_enabled: boolean;
  manual_correction_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnvironmentalObservation {
  id: string;
  provider_name: 'IMD' | 'ERA5_LAND' | 'LOCAL_SENSOR' | 'DEMO_HYDERABAD';
  source_identifier: string;
  latitude: number;
  longitude: number;
  spatial_resolution_km?: number | null;
  observed_at: string;
  temperature_celsius: number;
  relative_humidity_pct: number;
  heat_index_celsius?: number | null;
  wbgt_estimated_celsius?: number | null;
  wind_speed_mps?: number | null;
  solar_radiation_wm2?: number | null;
  confidence_score: number;
  data_freshness_status: 'REALTIME' | 'HOURLY' | 'HISTORICAL_REANALYSIS' | 'DEMO_SAMPLE';
  validation_status: 'VALIDATED' | 'PROVISIONAL' | 'FALLBACK';
}

export interface EarningEntry {
  id: string;
  upload_id: string;
  worker_id: string;
  platform_name: string; // Swiggy, Zomato, Uber, Ola, Porter, Zepto, Blinkit, etc.
  statement_period_start: string;
  statement_period_end: string;
  base_earnings: number;
  order_payments: number;
  incentives: number;
  bonuses: number;
  deductions: number;
  penalties: number;
  taxes: number;
  net_amount: number;
  payment_date?: string | null;
  is_confirmed_by_worker: boolean;
  worker_confirmed_at?: string | null;
  worker_adjusted_notes?: string | null;
  extraction_confidence: number;
}

export interface EvidenceTimelineEvent {
  id: string;
  event_category: EvidenceCategory;
  timestamp: string;
  title: string;
  description: string;
  provenance_source: string;
  metadata: Record<string, any>;
  anomaly_flag?: string | null;
}

export interface EvidenceReport {
  id: string;
  worker_id: string;
  report_number: string;
  period_start: string;
  period_end: string;
  total_shifts: number;
  total_hours_worked: number;
  total_extreme_heat_hours: number;
  net_earnings_recorded: number;
  integrity_sha256: string;
  created_at: string;
  pdf_storage_path?: string | null;
  limitations_disclaimer: string;
}

export interface ShareGrant {
  id: string;
  worker_id: string;
  organisation_id: string;
  report_id: string;
  purpose: string;
  granted_at: string;
  expires_at: string;
  is_revoked: boolean;
  revoked_at?: string | null;
}
