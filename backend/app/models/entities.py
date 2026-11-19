import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, ForeignKey, Text, JSON, CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# 1. Users / Profiles
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="worker") # worker, organisation_admin, organisation_viewer, system_admin
    preferred_language = Column(String(10), nullable=False, default="en") # en, te, hi
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    consents = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    shifts = relationship("Shift", back_populates="worker", cascade="all, delete-orphan")
    earnings_uploads = relationship("EarningsUpload", back_populates="worker", cascade="all, delete-orphan")
    reports = relationship("EvidenceReport", back_populates="worker", cascade="all, delete-orphan")
    share_grants = relationship("ShareGrant", back_populates="worker", cascade="all, delete-orphan")

# 2. Worker Profiles
class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    worker_badge_id = Column(String(50), nullable=True)
    primary_platforms = Column(JSON, default=list) # e.g. ["Swiggy", "Zomato", "Uber"]
    vehicle_type = Column(String(50), nullable=True) # motorcycle, bicycle, ev, auto, car
    city = Column(String(100), default="Hyderabad")
    state = Column(String(100), default="Telangana")
    country = Column(String(50), default="India")
    consented_location_tracking = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="worker_profile")

# 3. Organisations
class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=False)
    org_type = Column(String(50), nullable=False, default="union") # union, ngo, welfare_board, research
    is_approved = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    members = relationship("OrganisationMember", back_populates="organisation", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="organisation", cascade="all, delete-orphan")
    share_grants = relationship("ShareGrant", back_populates="organisation", cascade="all, delete-orphan")

# 4. Organisation Members
class OrganisationMember(Base):
    __tablename__ = "organisation_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False, default="caseworker") # admin, analyst, caseworker
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    organisation = relationship("Organisation", back_populates="members")
    user = relationship("User")

# 5. Consent Records (Purpose-specific, DPDP compliant)
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(100), nullable=False) # LOCATION_TRACKING_DURING_SHIFT, EARNINGS_DOCUMENT_EXTRACTION, etc.
    consent_text_version = Column(String(50), nullable=False, default="1.0")
    is_granted = Column(Boolean, nullable=False)
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    ip_address_hash = Column(String(64), nullable=True)
    user_agent_summary = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="consents")

# 6. Shifts
class Shift(Base):
    __tablename__ = "shifts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="ACTIVE") # ACTIVE, PAUSED, COMPLETED, CANCELLED
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    total_working_minutes = Column(Integer, default=0, nullable=False)
    total_break_minutes = Column(Integer, default=0, nullable=False)
    location_tracking_enabled = Column(Boolean, default=False, nullable=False)
    manual_correction_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    worker = relationship("User", back_populates="shifts")
    breaks = relationship("BreakEvent", back_populates="shift", cascade="all, delete-orphan")
    location_samples = relationship("LocationSample", back_populates="shift", cascade="all, delete-orphan")
    exposure_intervals = relationship("ExposureInterval", back_populates="shift", cascade="all, delete-orphan")

# 7. Location Samples
class LocationSample(Base):
    __tablename__ = "location_samples"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shift_id = Column(String(36), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=False)
    altitude_meters = Column(Float, nullable=True)
    speed_mps = Column(Float, nullable=True)
    recorded_at = Column(DateTime, nullable=False, index=True)
    is_valid = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    shift = relationship("Shift", back_populates="location_samples")
    worker = relationship("User")

# 8. Break Events
class BreakEvent(Base):
    __tablename__ = "break_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shift_id = Column(String(36), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    break_type = Column(String(50), nullable=False, default="REST") # REST, HYDRATION, MEAL, SHELTER, OTHER
    started_at = Column(DateTime, nullable=False, index=True)
    ended_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=0, nullable=False)
    worker_notes = Column(Text, nullable=True)
    is_worker_declared = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    shift = relationship("Shift", back_populates="breaks")
    worker = relationship("User")

# 9. Weather Observations
class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_name = Column(String(50), nullable=False) # IMD, ERA5_LAND, LOCAL_SENSOR, DEMO_HYDERABAD
    source_identifier = Column(String(100), nullable=False) # station_id or grid_cell
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    spatial_resolution_km = Column(Float, nullable=True)
    observed_at = Column(DateTime, nullable=False, index=True)
    ingested_at = Column(DateTime, default=utc_now, nullable=False)
    temperature_celsius = Column(Float, nullable=False)
    relative_humidity_pct = Column(Float, nullable=False)
    heat_index_celsius = Column(Float, nullable=True)
    wbgt_estimated_celsius = Column(Float, nullable=True)
    wind_speed_mps = Column(Float, nullable=True)
    solar_radiation_wm2 = Column(Float, nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=False) # 0.0 to 1.0
    data_freshness_status = Column(String(50), default="REALTIME", nullable=False) # REALTIME, HOURLY, HISTORICAL_REANALYSIS, DEMO_SAMPLE
    validation_status = Column(String(50), default="VALIDATED", nullable=False) # VALIDATED, PROVISIONAL, FALLBACK
    raw_data_payload = Column(JSON, nullable=True)

# 10. Exposure Intervals
class ExposureInterval(Base):
    __tablename__ = "exposure_intervals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    shift_id = Column(String(36), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    mean_temperature_celsius = Column(Float, nullable=False)
    mean_relative_humidity_pct = Column(Float, nullable=False)
    heat_index_celsius = Column(Float, nullable=False)
    risk_category = Column(String(50), nullable=False) # LOW, CAUTION, EXTREME_CAUTION, DANGER, EXTREME_DANGER
    wbgt_proxy_celsius = Column(Float, nullable=True)
    source_observation_id = Column(String(36), ForeignKey("weather_observations.id"), nullable=True)
    distance_to_source_km = Column(Float, nullable=True)
    temporal_offset_minutes = Column(Integer, nullable=True)
    quality_grade = Column(String(20), default="HIGH", nullable=False) # HIGH, MEDIUM, ESTIMATED
    created_at = Column(DateTime, default=utc_now, nullable=False)

    shift = relationship("Shift", back_populates="exposure_intervals")
    worker = relationship("User")

# 11. Earnings Uploads
class EarningsUpload(Base):
    __tablename__ = "earnings_uploads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filepath = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False) # pdf, jpg, jpeg, png, csv
    file_size_bytes = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    upload_status = Column(String(30), default="UPLOADED", nullable=False) # UPLOADED, PROCESSING, PARSED, FAILED, CONFIRMED
    processing_error = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)

    worker = relationship("User", back_populates="earnings_uploads")
    entries = relationship("EarningEntry", back_populates="upload", cascade="all, delete-orphan")

# 12. Earning Entries
class EarningEntry(Base):
    __tablename__ = "earning_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    upload_id = Column(String(36), ForeignKey("earnings_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_name = Column(String(100), nullable=False) # Swiggy, Zomato, Uber, Ola, etc.
    statement_period_start = Column(DateTime, nullable=False)
    statement_period_end = Column(DateTime, nullable=False)
    base_earnings = Column(Float, default=0.0, nullable=False)
    order_payments = Column(Float, default=0.0, nullable=False)
    incentives = Column(Float, default=0.0, nullable=False)
    bonuses = Column(Float, default=0.0, nullable=False)
    deductions = Column(Float, default=0.0, nullable=False)
    penalties = Column(Float, default=0.0, nullable=False)
    taxes = Column(Float, default=0.0, nullable=False)
    net_amount = Column(Float, default=0.0, nullable=False)
    payment_date = Column(DateTime, nullable=True)
    extraction_confidence = Column(Float, default=1.0, nullable=False)
    is_confirmed_by_worker = Column(Boolean, default=False, nullable=False)
    worker_confirmed_at = Column(DateTime, nullable=True)
    worker_adjusted_notes = Column(Text, nullable=True)
    raw_extracted_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    upload = relationship("EarningsUpload", back_populates="entries")
    worker = relationship("User")

# 13. Analysis Runs
class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(String(36), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    run_type = Column(String(50), nullable=False) # SHIFT_EXPOSURE, EARNINGS_CORRELATION, TIMELINE_AGGREGATE
    status = Column(String(30), default="PENDING", nullable=False) # PENDING, RUNNING, COMPLETED, FAILED
    input_parameters = Column(JSON, nullable=True)
    results_summary = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

# 14. Evidence Reports
class EvidenceReport(Base):
    __tablename__ = "evidence_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_number = Column(String(100), unique=True, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_shifts = Column(Integer, default=0, nullable=False)
    total_hours_worked = Column(Float, default=0.0, nullable=False)
    total_extreme_heat_hours = Column(Float, default=0.0, nullable=False)
    net_earnings_recorded = Column(Float, default=0.0, nullable=False)
    integrity_sha256 = Column(String(64), nullable=False)
    pdf_storage_path = Column(String(500), nullable=True)
    limitations_disclaimer = Column(Text, nullable=False)
    generation_version = Column(String(20), default="1.0.0", nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    worker = relationship("User", back_populates="reports")
    sources = relationship("ReportSource", back_populates="report", cascade="all, delete-orphan")
    share_grants = relationship("ShareGrant", back_populates="report", cascade="all, delete-orphan")

# 15. Report Sources
class ReportSource(Base):
    __tablename__ = "report_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("evidence_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False) # SHIFT, BREAK, LOCATION_SAMPLE, WEATHER_OBSERVATION, EARNING_ENTRY
    source_id = Column(String(36), nullable=False)
    attribution_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    report = relationship("EvidenceReport", back_populates="sources")

# 16. Share Grants (Worker-authorized, scoped, revocable)
class ShareGrant(Base):
    __tablename__ = "share_grants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    worker_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(String(36), ForeignKey("evidence_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    granted_at = Column(DateTime, default=utc_now, nullable=False)
    access_count = Column(Integer, default=0, nullable=False)

    worker = relationship("User", back_populates="share_grants")
    organisation = relationship("Organisation", back_populates="share_grants")
    report = relationship("EvidenceReport", back_populates="share_grants")

# 17. Cases
class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    organisation_id = Column(String(36), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(String(36), ForeignKey("evidence_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    case_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(String(50), default="OPEN", nullable=False) # OPEN, UNDER_REVIEW, ACTION_TAKEN, RESOLVED, CLOSED
    priority = Column(String(30), default="MEDIUM", nullable=False) # LOW, MEDIUM, HIGH, URGENT
    worker_pseudonym = Column(String(100), nullable=False) # Protects direct identity on case overview
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    organisation = relationship("Organisation", back_populates="cases")
    report = relationship("EvidenceReport")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")

# 18. Case Notes
class CaseNote(Base):
    __tablename__ = "case_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    author_user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    case = relationship("Case", back_populates="notes")
    author = relationship("User")

# 19. Audit Logs
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True) # CONSENT_GRANTED, SHARE_REVOKED, REPORT_DOWNLOADED, etc.
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    ip_hash = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

# 20. Processing Jobs
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_type = Column(String(50), nullable=False) # DOCUMENT_OCR, REPORT_PDF_GEN, ERA5_SYNC, EXPOSURE_COMPUTE
    status = Column(String(30), default="QUEUED", nullable=False) # QUEUED, RUNNING, COMPLETED, FAILED
    payload = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    last_error = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, default=utc_now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
