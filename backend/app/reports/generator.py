import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.core.logging import logger
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

class ReportGeneratorService:
    @staticmethod
    def generate_report(
        db: Session,
        worker_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> EvidenceReport:
        # 1. Fetch shifts in window
        shifts = (
            db.query(Shift)
            .filter(
                Shift.worker_id == worker_id,
                Shift.started_at >= period_start,
                Shift.started_at <= period_end,
            )
            .all()
        )
        total_shifts = len(shifts)
        total_hours_worked = sum(s.total_working_minutes for s in shifts) / 60.0

        # 2. Fetch exposure intervals
        shift_ids = [s.id for s in shifts]
        exposures = (
            db.query(ExposureInterval)
            .filter(ExposureInterval.shift_id.in_(shift_ids))
            .all()
            if shift_ids else []
        )
        
        # Calculate extreme heat hours (intervals in DANGER or EXTREME_DANGER)
        extreme_heat_intervals = [
            e for e in exposures if e.risk_category in ["DANGER", "EXTREME_DANGER"]
        ]
        total_extreme_heat_hours = len(extreme_heat_intervals) * 1.0 # Each interval is 1 hour

        # 3. Fetch earnings entries
        earnings = (
            db.query(EarningEntry)
            .filter(
                EarningEntry.worker_id == worker_id,
                EarningEntry.statement_period_start >= period_start,
                EarningEntry.statement_period_start <= period_end,
            )
            .all()
        )
        net_earnings_recorded = sum(e.net_amount for e in earnings)

        report_number = f"HL-HYD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{worker_id[:6].upper()}"

        # 4. Prepare data structure for PDF generator
        shifts_summary = []
        for s in shifts:
            s_exposures = [e for e in exposures if e.shift_id == s.id]
            max_hi = max((e.heat_index_celsius for e in s_exposures), default=32.0)
            max_risk = "LOW"
            if max_hi >= 39.0:
                max_risk = "DANGER"
            elif max_hi >= 32.0:
                max_risk = "EXTREME_CAUTION"
            elif max_hi >= 27.0:
                max_risk = "CAUTION"

            shifts_summary.append({
                "id": s.id,
                "started_at": s.started_at,
                "total_working_minutes": s.total_working_minutes,
                "max_heat_index": max_hi,
                "risk_category": max_risk,
            })

        earnings_summary = [
            {
                "platform": e.platform_name,
                "period": e.statement_period_start,
                "base": e.base_earnings,
                "incentives": e.incentives,
                "deductions": e.deductions,
                "net": e.net_amount,
                "confirmed": e.is_confirmed_by_worker,
            }
            for e in earnings
        ]

        report_data = {
            "report_number": report_number,
            "worker_id": worker_id,
            "period_start": period_start,
            "period_end": period_end,
            "total_shifts": total_shifts,
            "total_hours_worked": total_hours_worked,
            "total_extreme_heat_hours": total_extreme_heat_hours,
            "net_earnings_recorded": net_earnings_recorded,
            "shifts_summary": shifts_summary,
            "earnings_summary": earnings_summary,
            "limitations_disclaimer": LIMITATIONS_DISCLAIMER,
            "integrity_sha256": "PENDING_FINALIZATION",
        }

        # 5. Build preliminary PDF & calculate actual SHA-256
        pdf_bytes = HeatLedgerPDFBuilder.build_report_pdf(report_data)
        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        # Rebuild PDF with final embedded hash for exact self-consistency
        report_data["integrity_sha256"] = pdf_sha256
        final_pdf_bytes = HeatLedgerPDFBuilder.build_report_pdf(report_data)
        final_sha256 = hashlib.sha256(final_pdf_bytes).hexdigest()

        # 6. Save PDF to private storage
        reports_dir = os.path.join(settings.LOCAL_STORAGE_DIR, worker_id, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        pdf_path = os.path.join(reports_dir, f"{report_number}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(final_pdf_bytes)

        # 7. Persist EvidenceReport entity
        report = EvidenceReport(
            worker_id=worker_id,
            report_number=report_number,
            period_start=period_start,
            period_end=period_end,
            total_shifts=total_shifts,
            total_hours_worked=round(total_hours_worked, 1),
            total_extreme_heat_hours=round(total_extreme_heat_hours, 1),
            net_earnings_recorded=round(net_earnings_recorded, 2),
            integrity_sha256=final_sha256,
            pdf_storage_path=pdf_path,
            limitations_disclaimer=LIMITATIONS_DISCLAIMER,
            generation_version="1.0.0",
            created_at=utc_now(),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # 8. Record report sources for auditability
        for s in shifts:
            db.add(ReportSource(
                report_id=report.id,
                source_type="SHIFT",
                source_id=s.id,
                attribution_metadata={"started_at": s.started_at.isoformat()},
            ))
        for e in earnings:
            db.add(ReportSource(
                report_id=report.id,
                source_type="EARNING_ENTRY",
                source_id=e.id,
                attribution_metadata={"platform": e.platform_name, "net": e.net_amount},
            ))
        db.commit()
        return report

    @staticmethod
    def get_report_pdf(db: Session, report_id: str, worker_id: Optional[str] = None) -> bytes:
        query = db.query(EvidenceReport).filter(EvidenceReport.id == report_id)
        if worker_id:
            query = query.filter(EvidenceReport.worker_id == worker_id)
        report = query.first()
        if not report or not report.pdf_storage_path or not os.path.exists(report.pdf_storage_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report PDF not found")
        with open(report.pdf_storage_path, "rb") as f:
            return f.read()
