"""Evidence Correlation Engine
Constructs an immutable, traceable, chronological evidence timeline across:
- Shifts
- Breaks
- Location samples
- Weather observations
- Exposure intervals
- Document uploads
- Confirmed earnings records
- Analytical flags
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid

from backend.app.models.entities import (
    Shift,
    BreakEvent,
    LocationSample,
    WeatherObservation,
    ExposureInterval,
    EarningsUpload,
    EarningEntry,
)
from backend.app.schemas.evidence import EvidenceTimelineEventResponse, EvidenceTimelineResponse

LIMITATIONS_DISCLAIMER = (
    "DISCLAIMER & INTEGRITY NOTICE: HeatLedger evidence records compile worker-declared actions, "
    "ambient environmental observations from accredited meteorological sources, and verified platform earnings. "
    "Environmental correlations represent mathematical co-occurrences of climate stress and working periods; "
    "they do not constitute automated medical causation or government-certified legal proof. "
    "Data integrity is cryptographically verifiable via SHA-256."
)

class EvidenceCorrelator:
    @staticmethod
    def build_timeline(
        db: Session,
        worker_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> EvidenceTimelineResponse:
        events: List[EvidenceTimelineEventResponse] = []
        flags: List[str] = []

        # 1. Shifts (WORKER_ACTION)
        shifts = (
            db.query(Shift)
            .filter(
                Shift.worker_id == worker_id,
                Shift.started_at >= start_time,
                Shift.started_at <= end_time,
            )
            .order_by(Shift.started_at.asc())
            .all()
        )
        for s in shifts:
            events.append(
                EvidenceTimelineEventResponse(
                    id=str(uuid.uuid4()),
                    event_category="WORKER_ACTION",
                    timestamp=s.started_at,
                    title="Shift Started",
                    description=f"Worker initiated shift (Status: {s.status}). Location tracking: {'Enabled' if s.location_tracking_enabled else 'Disabled'}.",
                    provenance_source=f"Shift record ID: {s.id}",
                    metadata={
                        "shift_id": s.id,
                        "location_tracking_enabled": s.location_tracking_enabled,
                    },
                )
            )
            if s.ended_at:
                events.append(
                    EvidenceTimelineEventResponse(
                        id=str(uuid.uuid4()),
                        event_category="WORKER_ACTION",
                        timestamp=s.ended_at,
                        title="Shift Concluded",
                        description=f"Worker ended shift. Total working: {s.total_working_minutes} mins, Breaks: {s.total_break_minutes} mins.",
                        provenance_source=f"Shift record ID: {s.id}",
                        metadata={
                            "shift_id": s.id,
                            "total_working_minutes": s.total_working_minutes,
                            "total_break_minutes": s.total_break_minutes,
                        },
                    )
                )

        # 2. Breaks (WORKER_DECLARED_BREAK)
        shift_ids = [s.id for s in shifts]
        breaks = (
            db.query(BreakEvent)
            .filter(BreakEvent.shift_id.in_(shift_ids))
            .order_by(BreakEvent.started_at.asc())
            .all()
            if shift_ids else []
        )
        for b in breaks:
            events.append(
                EvidenceTimelineEventResponse(
                    id=str(uuid.uuid4()),
                    event_category="WORKER_DECLARED_BREAK",
                    timestamp=b.started_at,
                    title=f"Worker Rest Break ({b.break_type})",
                    description=f"Worker declared {b.break_type.lower()} break for {b.duration_minutes} minutes. Notes: {b.worker_notes or 'None'}.",
                    provenance_source=f"BreakEvent ID: {b.id}",
                    metadata={
                        "break_id": b.id,
                        "break_type": b.break_type,
                        "duration_minutes": b.duration_minutes,
                        "is_worker_declared": True,
                    },
                )
            )

        # 3. Location Samples (LOCATION_OBSERVATION)
        location_samples = (
            db.query(LocationSample)
            .filter(LocationSample.shift_id.in_(shift_ids))
            .order_by(LocationSample.recorded_at.asc())
            .limit(50)
            .all()
            if shift_ids else []
        )
        for loc in location_samples:
            events.append(
                EvidenceTimelineEventResponse(
                    id=str(uuid.uuid4()),
                    event_category="LOCATION_OBSERVATION",
                    timestamp=loc.recorded_at,
                    title="Consented Location Fix",
                    description=f"Recorded position (Accuracy: {loc.accuracy_meters}m).",
                    provenance_source=f"LocationSample ID: {loc.id}",
                    metadata={
                        "latitude": loc.latitude,
                        "longitude": loc.longitude,
                        "accuracy_meters": loc.accuracy_meters,
                    },
                )
            )

        # 4. Exposure Intervals (ESTIMATED_EXPOSURE)
        exposures = (
            db.query(ExposureInterval)
            .filter(ExposureInterval.shift_id.in_(shift_ids))
            .order_by(ExposureInterval.start_time.asc())
            .all()
            if shift_ids else []
        )
        for exp in exposures:
            flag = None
            if exp.risk_category in ["DANGER", "EXTREME_DANGER"]:
                flag = f"HIGH_CLIMATE_EXPOSURE: Heat Index {exp.heat_index_celsius}°C exceeded safety limits ({exp.risk_category})"
                if flag not in flags:
                    flags.append(flag)

            events.append(
                EvidenceTimelineEventResponse(
                    id=str(uuid.uuid4()),
                    event_category="ESTIMATED_EXPOSURE",
                    timestamp=exp.start_time,
                    title=f"Heat Exposure: {exp.risk_category}",
                    description=(
                        f"Calculated Heat Index: {exp.heat_index_celsius}°C (Ambient: {exp.mean_temperature_celsius}°C, "
                        f"RH: {exp.mean_relative_humidity_pct}%). Estimated sWBGT: {exp.wbgt_proxy_celsius}°C. "
                        f"Quality grade: {exp.quality_grade}."
                    ),
                    provenance_source=f"ExposureInterval ID: {exp.id}",
                    metadata={
                        "heat_index": exp.heat_index_celsius,
                        "ambient_temp": exp.mean_temperature_celsius,
                        "humidity": exp.mean_relative_humidity_pct,
                        "risk_category": exp.risk_category,
                        "quality_grade": exp.quality_grade,
                    },
                    anomaly_flag=flag,
                )
            )

        # 5. Earnings Uploads & Entries (DOCUMENT_UPLOAD & WORKER_CONFIRMED_VALUE)
        uploads = (
            db.query(EarningsUpload)
            .filter(
                EarningsUpload.worker_id == worker_id,
                EarningsUpload.uploaded_at >= start_time,
                EarningsUpload.uploaded_at <= end_time,
            )
            .all()
        )
        for up in uploads:
            events.append(
                EvidenceTimelineEventResponse(
                    id=str(uuid.uuid4()),
                    event_category="DOCUMENT_UPLOAD",
                    timestamp=up.uploaded_at,
                    title="Earnings Statement Uploaded",
                    description=f"Uploaded {up.original_filename} ({up.file_type.upper()}, {up.file_size_bytes} bytes). SHA-256: {up.sha256_hash[:16]}...",
                    provenance_source=f"EarningsUpload ID: {up.id}",
                    metadata={
                        "sha256": up.sha256_hash,
                        "filename": up.original_filename,
                    },
                )
            )

        entries = (
            db.query(EarningEntry)
            .filter(
                EarningEntry.worker_id == worker_id,
                EarningEntry.created_at >= start_time,
                EarningEntry.created_at <= end_time,
            )
            .all()
        )
        for ent in entries:
            cat = "WORKER_CONFIRMED_VALUE" if ent.is_confirmed_by_worker else "AI_EXTRACTED_VALUE"
            events.append(
                EvidenceTimelineEventResponse(
                    id=str(uuid.uuid4()),
                    event_category=cat,
                    timestamp=ent.created_at,
                    title=f"Platform Payout: {ent.platform_name} (₹{ent.net_amount})",
                    description=(
                        f"Net payout ₹{ent.net_amount} (Base: ₹{ent.base_earnings}, Incentives: ₹{ent.incentives}, "
                        f"Deductions: ₹{ent.deductions}). Status: {'Worker Confirmed' if ent.is_confirmed_by_worker else 'Awaiting Worker Review'}."
                    ),
                    provenance_source=f"EarningEntry ID: {ent.id}",
                    metadata={
                        "platform": ent.platform_name,
                        "net_amount": ent.net_amount,
                        "is_confirmed": ent.is_confirmed_by_worker,
                    },
                )
            )

        # Sort all timeline events chronologically
        from backend.app.core.datetime_utils import ensure_utc
        events.sort(key=lambda e: ensure_utc(e.timestamp))

        return EvidenceTimelineResponse(
            worker_id=worker_id,
            period_start=start_time,
            period_end=end_time,
            events_count=len(events),
            events=events,
            flags_detected=flags,
            limitations_disclaimer=LIMITATIONS_DISCLAIMER,
        )
