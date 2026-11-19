"""Initial schema for HeatLedger

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-19 01:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
        sa.Column('phone', sa.String(20), unique=True, nullable=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='worker'),
        sa.Column('preferred_language', sa.String(10), nullable=False, server_default='en'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_phone', 'users', ['phone'])

    # 2. Worker profiles
    op.create_table(
        'worker_profiles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('worker_badge_id', sa.String(50), nullable=True),
        sa.Column('primary_platforms', sa.JSON(), nullable=True),
        sa.Column('vehicle_type', sa.String(50), nullable=True),
        sa.Column('city', sa.String(100), server_default='Hyderabad'),
        sa.Column('state', sa.String(100), server_default='Telangana'),
        sa.Column('country', sa.String(50), server_default='India'),
        sa.Column('consented_location_tracking', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # 3. Organisations
    op.create_table(
        'organisations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('org_type', sa.String(50), server_default='union', nullable=False),
        sa.Column('is_approved', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_organisations_slug', 'organisations', ['slug'])

    # 4. Organisation Members
    op.create_table(
        'organisation_members',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organisation_id', sa.String(36), sa.ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(50), server_default='caseworker', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # 5. Consent Records
    op.create_table(
        'consent_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purpose', sa.String(100), nullable=False),
        sa.Column('consent_text_version', sa.String(50), server_default='1.0', nullable=False),
        sa.Column('is_granted', sa.Boolean(), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address_hash', sa.String(64), nullable=True),
        sa.Column('user_agent_summary', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_consent_records_user_id', 'consent_records', ['user_id'])

    # 6. Shifts
    op.create_table(
        'shifts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(30), server_default='ACTIVE', nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('total_working_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_break_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('location_tracking_enabled', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('manual_correction_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_shifts_worker_id', 'shifts', ['worker_id'])
    op.create_index('ix_shifts_started_at', 'shifts', ['started_at'])

    # 7. Location Samples
    op.create_table(
        'location_samples',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('shift_id', sa.String(36), sa.ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy_meters', sa.Float(), nullable=False),
        sa.Column('altitude_meters', sa.Float(), nullable=True),
        sa.Column('speed_mps', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('is_valid', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_location_samples_shift_id', 'location_samples', ['shift_id'])
    op.create_index('ix_location_samples_recorded_at', 'location_samples', ['recorded_at'])

    # 8. Break Events
    op.create_table(
        'break_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('shift_id', sa.String(36), sa.ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('break_type', sa.String(50), server_default='REST', nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('worker_notes', sa.Text(), nullable=True),
        sa.Column('is_worker_declared', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_break_events_shift_id', 'break_events', ['shift_id'])

    # 9. Weather Observations
    op.create_table(
        'weather_observations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('source_identifier', sa.String(100), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('spatial_resolution_km', sa.Float(), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('ingested_at', sa.DateTime(), nullable=False),
        sa.Column('temperature_celsius', sa.Float(), nullable=False),
        sa.Column('relative_humidity_pct', sa.Float(), nullable=False),
        sa.Column('heat_index_celsius', sa.Float(), nullable=True),
        sa.Column('wbgt_estimated_celsius', sa.Float(), nullable=True),
        sa.Column('wind_speed_mps', sa.Float(), nullable=True),
        sa.Column('solar_radiation_wm2', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('data_freshness_status', sa.String(50), server_default='REALTIME', nullable=False),
        sa.Column('validation_status', sa.String(50), server_default='VALIDATED', nullable=False),
        sa.Column('raw_data_payload', sa.JSON(), nullable=True),
    )
    op.create_index('ix_weather_observations_observed_at', 'weather_observations', ['observed_at'])

    # 10. Exposure Intervals
    op.create_table(
        'exposure_intervals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('shift_id', sa.String(36), sa.ForeignKey('shifts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('mean_temperature_celsius', sa.Float(), nullable=False),
        sa.Column('mean_relative_humidity_pct', sa.Float(), nullable=False),
        sa.Column('heat_index_celsius', sa.Float(), nullable=False),
        sa.Column('risk_category', sa.String(50), nullable=False),
        sa.Column('wbgt_proxy_celsius', sa.Float(), nullable=True),
        sa.Column('source_observation_id', sa.String(36), sa.ForeignKey('weather_observations.id'), nullable=True),
        sa.Column('distance_to_source_km', sa.Float(), nullable=True),
        sa.Column('temporal_offset_minutes', sa.Integer(), nullable=True),
        sa.Column('quality_grade', sa.String(20), server_default='HIGH', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_exposure_intervals_shift_id', 'exposure_intervals', ['shift_id'])

    # 11. Earnings Uploads
    op.create_table(
        'earnings_uploads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('stored_filepath', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(20), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(64), nullable=False),
        sa.Column('upload_status', sa.String(30), server_default='UPLOADED', nullable=False),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_earnings_uploads_worker_id', 'earnings_uploads', ['worker_id'])

    # 12. Earning Entries
    op.create_table(
        'earning_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('upload_id', sa.String(36), sa.ForeignKey('earnings_uploads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform_name', sa.String(100), nullable=False),
        sa.Column('statement_period_start', sa.DateTime(), nullable=False),
        sa.Column('statement_period_end', sa.DateTime(), nullable=False),
        sa.Column('base_earnings', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('order_payments', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('incentives', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('bonuses', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('deductions', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('penalties', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('taxes', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('net_amount', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('payment_date', sa.DateTime(), nullable=True),
        sa.Column('extraction_confidence', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('is_confirmed_by_worker', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('worker_confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('worker_adjusted_notes', sa.Text(), nullable=True),
        sa.Column('raw_extracted_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_earning_entries_upload_id', 'earning_entries', ['upload_id'])
    op.create_index('ix_earning_entries_worker_id', 'earning_entries', ['worker_id'])

    # 13. Analysis Runs
    op.create_table(
        'analysis_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('shift_id', sa.String(36), sa.ForeignKey('shifts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('run_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), server_default='PENDING', nullable=False),
        sa.Column('input_parameters', sa.JSON(), nullable=True),
        sa.Column('results_summary', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # 14. Evidence Reports
    op.create_table(
        'evidence_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_number', sa.String(100), unique=True, nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('total_shifts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_hours_worked', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('total_extreme_heat_hours', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('net_earnings_recorded', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('integrity_sha256', sa.String(64), nullable=False),
        sa.Column('pdf_storage_path', sa.String(500), nullable=True),
        sa.Column('limitations_disclaimer', sa.Text(), nullable=False),
        sa.Column('generation_version', sa.String(20), server_default='1.0.0', nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_evidence_reports_worker_id', 'evidence_reports', ['worker_id'])

    # 15. Report Sources
    op.create_table(
        'report_sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('report_id', sa.String(36), sa.ForeignKey('evidence_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(36), nullable=False),
        sa.Column('attribution_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_report_sources_report_id', 'report_sources', ['report_id'])

    # 16. Share Grants
    op.create_table(
        'share_grants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('worker_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organisation_id', sa.String(36), sa.ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_id', sa.String(36), sa.ForeignKey('evidence_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('purpose', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('access_count', sa.Integer(), server_default='0', nullable=False),
    )
    op.create_index('ix_share_grants_worker_id', 'share_grants', ['worker_id'])
    op.create_index('ix_share_grants_organisation_id', 'share_grants', ['organisation_id'])

    # 17. Cases
    op.create_table(
        'cases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('organisation_id', sa.String(36), sa.ForeignKey('organisations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('report_id', sa.String(36), sa.ForeignKey('evidence_reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('case_number', sa.String(100), unique=True, nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='OPEN', nullable=False),
        sa.Column('priority', sa.String(30), server_default='MEDIUM', nullable=False),
        sa.Column('worker_pseudonym', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_cases_organisation_id', 'cases', ['organisation_id'])

    # 18. Case Notes
    op.create_table(
        'case_notes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('case_id', sa.String(36), sa.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
        sa.Column('author_user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_case_notes_case_id', 'case_notes', ['case_id'])

    # 19. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('ip_hash', sa.String(64), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])

    # 20. Processing Jobs
    op.create_table(
        'processing_jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), server_default='QUEUED', nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='3', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
    )

def downgrade() -> None:
    op.drop_table('processing_jobs')
    op.drop_table('audit_logs')
    op.drop_table('case_notes')
    op.drop_table('cases')
    op.drop_table('share_grants')
    op.drop_table('report_sources')
    op.drop_table('evidence_reports')
    op.drop_table('analysis_runs')
    op.drop_table('earning_entries')
    op.drop_table('earnings_uploads')
    op.drop_table('exposure_intervals')
    op.drop_table('weather_observations')
    op.drop_table('break_events')
    op.drop_table('location_samples')
    op.drop_table('shifts')
    op.drop_table('consent_records')
    op.drop_table('organisation_members')
    op.drop_table('organisations')
    op.drop_table('worker_profiles')
    op.drop_table('users')
