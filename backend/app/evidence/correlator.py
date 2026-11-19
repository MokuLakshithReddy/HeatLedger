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
EVID-07: Uses stable deterministic event identifiers derived from underlying database entities.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import (
    Shift,
    BreakEvent,
    LocationSample,
    WeatherObservation,
    ExposureInterval,
    EarningsUpload,
    EarningEntry,
    EvidenceReport,
)
from backend.app.schemas.evidence import EvidenceTimelineEventResponse, EvidenceTimelineResponse
from backend.app.core.datetime_utils import ensure_utc

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

        st = ensure_utc(start_time)
        et = ensure_utc(end_time)

        # 1. Shifts (WORKER_ACTION)
        shifts = (
            db.query(Shift)
            .filter(
                Shift.worker_id == worker_id,
                Shift.started_at >= st,
                Shift.started_at <= et,
            )
            .order_by(Shift.started_at.asc())
            .all()
        )
        for s in shifts:
            events.append(
                EvidenceTimelineEventResponse(
                    id=f"shift-start-{s.id}",
                    event_category="WORKER_ACTION",
                    timestamp=ensure_utc(s.started_at),
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
                        id=f"shift-end-{s.id}",
                        event_category="WORKER_ACTION",
                        timestamp=ensure_utc(s.ended_at),
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
                    id=f"break-start-{b.id}",
                    event_category="WORKER_DECLARED_BREAK",
                    timestamp=ensure_utc(b.started_at),
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
                    id=f"location-{loc.id}",
                    event_category="LOCATION_OBSERVATION",
                    timestamp=ensure_utc(loc.recorded_at),
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
                    id=f"exposure-{exp.id}",
                    event_category="ESTIMATED_EXPOSURE",
                    timestamp=ensure_utc(exp.start_time),
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
                EarningsUpload.uploaded_at >= st,
                EarningsUpload.uploaded_at <= et,
            )
            .all()
        )
        for up in uploads:
            events.append(
                EvidenceTimelineEventResponse(
                    id=f"upload-{up.id}",
                    event_category="DOCUMENT_UPLOAD",
                    timestamp=ensure_utc(up.uploaded_at),
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
                EarningEntry.created_at >= st,
                EarningEntry.created_at <= et,
            )
            .all()
        )
        for ent in entries:
            cat = "WORKER_CONFIRMED_VALUE" if ent.is_confirmed_by_worker else "AI_EXTRACTED_VALUE"
            events.append(
                EvidenceTimelineEventResponse(
                    id=f"earning-{ent.id}",
                    event_category=cat,
                    timestamp=ensure_utc(ent.created_at),
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

        # 6. Generated Reports
        reports = (
            db.query(EvidenceReport)
            .filter(
                EvidenceReport.worker_id == worker_id,
                EvidenceReport.created_at >= st,
                EvidenceReport.created_at <= et,
            )
            .all()
        )
        for r in reports:
            events.append(
                EvidenceTimelineEventResponse(
                    id=f"report-{r.id}",
                    event_category="EVIDENCE_REPORT_GENERATED",
                    timestamp=ensure_utc(r.created_at),
                    title=f"Evidence Dossier Compiled ({r.report_number})",
                    description=f"Generated report covering {r.total_hours_worked} working hours, {r.total_extreme_heat_hours} danger heat hours. SHA-256: {r.integrity_sha256[:16]}...",
                    provenance_source=f"EvidenceReport ID: {r.id}",
                    metadata={
                        "report_number": r.report_number,
                        "integrity_sha256": r.integrity_sha256,
                    },
                )
            )

        # Sort all timeline events chronologically and deterministically
        events.sort(key=lambda e: (ensure_utc(e.timestamp), e.id))

        return EvidenceTimelineResponse(
            worker_id=worker_id,
            period_start=st,
            period_end=et,
            events_count=len(events),
            events=events,
            flags_detected=flags,
            limitations_disclaimer=LIMITATIONS_DISCLAIMER,
        )
