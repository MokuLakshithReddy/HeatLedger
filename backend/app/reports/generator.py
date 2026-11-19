import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.storage import get_storage_provider
from backend.app.models.entities import (
    Shift,
    ExposureInterval,
    EarningEntry,
    EvidenceReport,
    ReportSource,
    utc_now,
)
from backend.app.evidence.correlator import LIMITATIONS_DISCLAIMER
from backend.app.reports.pdf_builder import HeatLedgerPDFBuilder
from backend.app.core.datetime_utils import ensure_utc

class ReportGeneratorService:
    @staticmethod
    def generate_report(
        db: Session,
        worker_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> EvidenceReport:
        p_start = ensure_utc(period_start)
        p_end = ensure_utc(period_end)

        # 1. Fetch shifts in window
        shifts = (
            db.query(Shift)
            .filter(
                Shift.worker_id == worker_id,
                Shift.started_at >= p_start,
                Shift.started_at <= p_end,
            )
            .order_by(Shift.started_at.asc())
            .all()
        )
        total_shifts = len(shifts)
        total_hours_worked = round(sum(s.total_working_minutes for s in shifts) / 60.0, 2)

        # 2. Fetch exposure intervals
        shift_ids = [s.id for s in shifts]
        exposures = (
            db.query(ExposureInterval)
            .filter(ExposureInterval.shift_id.in_(shift_ids))
            .order_by(ExposureInterval.start_time.asc())
            .all()
            if shift_ids else []
        )
        
        # EVID-03: Real duration of extreme heat intervals based on duration_minutes
        extreme_heat_intervals = [
            e for e in exposures if e.risk_category in ["DANGER", "EXTREME_DANGER"]
        ]
        total_extreme_heat_hours = round(
            sum(e.duration_minutes for e in extreme_heat_intervals) / 60.0, 2
        )

        # 3. Fetch earnings entries
        earnings = (
            db.query(EarningEntry)
            .filter(
                EarningEntry.worker_id == worker_id,
                EarningEntry.statement_period_start >= p_start,
                EarningEntry.statement_period_start <= p_end,
            )
            .order_by(EarningEntry.statement_period_start.asc())
            .all()
        )

        # EVID-05: Exclude unconfirmed earnings from confirmed net totals
        confirmed_earnings = [e for e in earnings if e.is_confirmed_by_worker]
        unconfirmed_earnings = [e for e in earnings if not e.is_confirmed_by_worker]
        net_earnings_recorded = round(sum(e.net_amount for e in confirmed_earnings), 2)

        # EVID-02: Collision-resistant unique report identifier
        report_unique_suffix = uuid.uuid4().hex[:8].upper()
        report_number = f"HL-HYD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{report_unique_suffix}"

        # 4. Prepare shifts summary without fake default temperatures (EVID-04)
        shifts_summary = []
        for s in shifts:
            s_exposures = [e for e in exposures if e.shift_id == s.id]
            valid_his = [e.heat_index_celsius for e in s_exposures if e.heat_index_celsius is not None]
            max_hi = max(valid_his) if valid_his else None

            max_risk = "LOW"
            if max_hi is not None:
                if max_hi >= 51.0:
                    max_risk = "EXTREME_DANGER"
                elif max_hi >= 39.0:
                    max_risk = "DANGER"
                elif max_hi >= 32.0:
                    max_risk = "EXTREME_CAUTION"
                elif max_hi >= 27.0:
                    max_risk = "CAUTION"
            else:
                max_risk = "NO_OBSERVATIONS"

            shifts_summary.append({
                "id": s.id,
                "started_at": str(s.started_at),
                "total_working_minutes": s.total_working_minutes,
                "max_heat_index": max_hi,
                "risk_category": max_risk,
                "quality_grade": "HIGH" if s.location_tracking_enabled else "COARSE",
            })

        earnings_summary = [
            {
                "platform": e.platform_name,
                "period": str(e.statement_period_start),
                "base": e.base_earnings,
                "incentives": e.incentives,
                "deductions": e.deductions,
                "net": e.net_amount,
                "confirmed": e.is_confirmed_by_worker,
            }
            for e in earnings
        ]

        # 5. Construct Canonical Payload and compute Canonical Hash (EVID-01)
        canonical_dict = {
            "report_number": report_number,
            "worker_id": worker_id,
            "period_start": p_start.isoformat(),
            "period_end": p_end.isoformat(),
            "total_shifts": total_shifts,
            "total_hours_worked": total_hours_worked,
            "total_extreme_heat_hours": total_extreme_heat_hours,
            "net_earnings_recorded": net_earnings_recorded,
            "shifts_summary": shifts_summary,
            "earnings_summary": earnings_summary,
        }
        canonical_json = json.dumps(canonical_dict, sort_keys=True)
        canonical_payload_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        report_data = {
            **canonical_dict,
            "canonical_payload_sha256": canonical_payload_sha256,
            "limitations_disclaimer": LIMITATIONS_DISCLAIMER,
        }

        # 6. Build PDF document
        final_pdf_bytes = HeatLedgerPDFBuilder.build_report_pdf(report_data)

        # 7. Calculate exact SHA-256 over final generated PDF bytes (EVID-01)
        pdf_sha256 = hashlib.sha256(final_pdf_bytes).hexdigest()

        # 8. Save PDF to private storage
        storage = get_storage_provider()
        rel_pdf_path = f"{worker_id}/reports/{report_number}.pdf"
        pdf_path = storage.save_file(rel_pdf_path, final_pdf_bytes, content_type="application/pdf")

        # 9. Persist EvidenceReport entity with exact byte-level SHA-256 and required limitations_disclaimer
        report = EvidenceReport(
            worker_id=worker_id,
            report_number=report_number,
            period_start=p_start,
            period_end=p_end,
            total_shifts=total_shifts,
            total_hours_worked=total_hours_worked,
            total_extreme_heat_hours=total_extreme_heat_hours,
            net_earnings_recorded=net_earnings_recorded,
            integrity_sha256=pdf_sha256,
            pdf_storage_path=pdf_path,
            limitations_disclaimer=LIMITATIONS_DISCLAIMER,
            created_at=utc_now(),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # 10. Persist complete provenance linkages (EVID-06)
        for s in shifts:
            db.add(ReportSource(
                report_id=report.id,
                source_type="SHIFT",
                source_id=s.id,
                attribution_metadata={"description": f"Shift {s.id[:8]} started at {s.started_at}. Minutes: {s.total_working_minutes}"},
            ))
        for exp in exposures:
            db.add(ReportSource(
                report_id=report.id,
                source_type="WEATHER",
                source_id=exp.id,
                attribution_metadata={"description": f"Exposure interval HI {exp.heat_index_celsius}°C ({exp.risk_category})"},
            ))
        for ce in confirmed_earnings:
            db.add(ReportSource(
                report_id=report.id,
                source_type="EARNINGS",
                source_id=ce.id,
                attribution_metadata={"description": f"Confirmed earnings {ce.platform_name}: net ₹{ce.net_amount}"},
            ))
        db.commit()

        logger.info(f"Generated EvidenceReport {report.report_number}. PDF SHA-256: {pdf_sha256}")
        return report

    @staticmethod
    def get_report_pdf(db: Session, report_id: str, worker_id: Optional[str] = None) -> bytes:
        query = db.query(EvidenceReport).filter(EvidenceReport.id == report_id)
        if worker_id:
            query = query.filter(EvidenceReport.worker_id == worker_id)
        report = query.first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        
        if report.pdf_storage_path:
            # Check local file or use storage provider
            if os.path.exists(report.pdf_storage_path):
                with open(report.pdf_storage_path, "rb") as f:
                    return f.read()
            try:
                storage = get_storage_provider()
                return storage.read_file(report.pdf_storage_path)
            except Exception:
                pass
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report PDF file not found on storage")
