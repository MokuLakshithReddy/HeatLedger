"""PDF Generation Service for HeatLedger Evidence Reports
Uses ReportLab to generate verifiable, tamper-evident documents with embedded SHA-256 hashes.
"""
import io
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

class HeatLedgerPDFBuilder:
    @staticmethod
    def build_report_pdf(report_data: Dict[str, Any]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        
        # Custom palette & styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        )

        elements = []

        # 1. Header
        elements.append(Paragraph("HEATLEDGER", title_style))
        elements.append(Paragraph("Worker Climate Exposure & Earnings Evidence Dossier", subtitle_style))
        elements.append(Paragraph("<i>Your work. Your conditions. Your evidence.</i>", disclaimer_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#e2e8f0")))
        elements.append(Spacer(1, 10))

        # 2. Metadata Grid
        meta_table_data = [
            [
                Paragraph("<b>Report Number:</b>", body_style),
                Paragraph(report_data.get("report_number", "N/A"), body_style),
                Paragraph("<b>Generated (UTC):</b>", body_style),
                Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), body_style),
            ],
            [
                Paragraph("<b>Worker ID:</b>", body_style),
                Paragraph(report_data.get("worker_id", "N/A")[:12] + "...", body_style),
                Paragraph("<b>Jurisdiction:</b>", body_style),
                Paragraph("Hyderabad, Telangana, India", body_style),
            ],
            [
                Paragraph("<b>Period Start:</b>", body_style),
                Paragraph(str(report_data.get("period_start", ""))[:16], body_style),
                Paragraph("<b>Period End:</b>", body_style),
                Paragraph(str(report_data.get("period_end", ""))[:16], body_style),
            ],
        ]
        meta_table = Table(meta_table_data, colWidths=[110, 160, 110, 160])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 12))

        # 3. Key Findings Summary
        elements.append(Paragraph("1. Executive Summary & Aggregate Metrics", section_style))
        summary_data = [
            ["Total Shifts Recorded", f"{report_data.get('total_shifts', 0)} shifts"],
            ["Total Cumulative Hours Worked", f"{report_data.get('total_hours_worked', 0.0):.1f} hrs"],
            ["Extreme Heat Exposure Hours (>=39°C HI)", f"{report_data.get('total_extreme_heat_hours', 0.0):.1f} hrs"],
            ["Recorded Net Platform Earnings", f"₹{report_data.get('net_earnings_recorded', 0.0):,.2f}"],
        ]
        summary_table = Table(summary_data, colWidths=[270, 270])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 14))

        # 4. Shifts and Environmental Exposure
        elements.append(Paragraph("2. Climate Exposure & Shift Records", section_style))
        shifts_summary = report_data.get("shifts_summary", [])
        if shifts_summary:
            shift_rows = [["Shift ID", "Started (UTC)", "Duration", "Heat Index", "Risk Category"]]
            for s in shifts_summary[:6]:
                shift_rows.append([
                    s.get("id", "")[:8],
                    str(s.get("started_at", ""))[:16],
                    f"{s.get('total_working_minutes', 0)}m",
                    f"{s.get('max_heat_index', 0.0)}°C",
                    s.get("risk_category", "LOW"),
                ])
            shift_table = Table(shift_rows, colWidths=[90, 130, 80, 100, 140])
            shift_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ])
            )
            elements.append(shift_table)
        else:
            elements.append(Paragraph("No shift records in reporting window.", body_style))
        elements.append(Spacer(1, 14))

        # 5. Earnings Breakdown
        elements.append(Paragraph("3. Platform Earnings Evidence", section_style))
        earnings_summary = report_data.get("earnings_summary", [])
        if earnings_summary:
            earn_rows = [["Platform", "Period", "Base Pay", "Incentives", "Deductions", "Net Pay", "Status"]]
            for e in earnings_summary[:5]:
                earn_rows.append([
                    e.get("platform", "Platform"),
                    str(e.get("period", ""))[:10],
                    f"₹{e.get('base', 0):.0f}",
                    f"₹{e.get('incentives', 0):.0f}",
                    f"₹{e.get('deductions', 0):.0f}",
                    f"₹{e.get('net', 0):.0f}",
                    "Confirmed" if e.get("confirmed") else "Unreviewed",
                ])
            earn_table = Table(earn_rows, colWidths=[80, 80, 70, 70, 70, 80, 90])
            earn_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ])
            )
            elements.append(earn_table)
        else:
            elements.append(Paragraph("No confirmed earnings statements recorded.", body_style))
        elements.append(Spacer(1, 14))

        # 6. Integrity Hash & Legal Disclaimer
        elements.append(KeepTogether([
            Paragraph("4. Data Integrity & Scientific Caveats", section_style),
            Paragraph(
                report_data.get(
                    "limitations_disclaimer",
                    "HeatLedger compiles worker declarations, meteorological feeds, and earnings files. "
                    "This report is not certified government proof or direct medical causation.",
                ),
                disclaimer_style,
            ),
            Spacer(1, 8),
            Paragraph(
                f"<b>Document Integrity SHA-256 (Self-Referential Target):</b> "
                f"<font color='#0284c7'>{report_data.get('integrity_sha256', 'PENDING_FINALIZATION')}</font>",
                body_style,
            ),
            Spacer(1, 4),
            Paragraph(
                "<i>Verification Notice: A SHA-256 hash confirms the document has not been altered since generation. "
                "It verifies file integrity, but does not independently prove the truth of external platform inputs.</i>",
                disclaimer_style,
            ),
        ]))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
