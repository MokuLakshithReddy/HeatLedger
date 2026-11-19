"""PDF Generation Service for HeatLedger Evidence Reports
Uses ReportLab to generate verifiable, tamper-evident documents.
EVID-01: Displays the Canonical Payload Digest in the document body.
The final PDF byte-level SHA-256 is calculated after generation and stored in the database.
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

        # 1. Header & Title Banner
        elements.append(Paragraph("HeatLedger — Climate Exposure & Earnings Dossier", title_style))
        elements.append(Paragraph("Worker-Owned Environmental Hardship & Labor Record", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#e2e8f0"), spaceAfter=12))

        # 2. Metadata Box
        meta_data = [
            [
                Paragraph(f"<b>Dossier Number:</b> {report_data.get('report_number')}", body_style),
                Paragraph(f"<b>Worker ID:</b> {report_data.get('worker_id')[:8]}...", body_style),
            ],
            [
                Paragraph(f"<b>Reporting Window:</b> {str(report_data.get('period_start'))[:10]} to {str(report_data.get('period_end'))[:10]}", body_style),
                Paragraph(f"<b>Canonical Digest:</b> {report_data.get('canonical_payload_sha256', 'N/A')[:16]}...", body_style),
            ],
            [
                Paragraph(f"<b>Total Shifts Logged:</b> {report_data.get('total_shifts', 0)}", body_style),
                Paragraph(f"<b>Working Duration:</b> {report_data.get('total_hours_worked', 0.0):.1f} hrs", body_style),
            ],
            [
                Paragraph(f"<b>Danger Heat Hours:</b> <font color='#dc2626'><b>{report_data.get('total_extreme_heat_hours', 0.0):.1f} hrs</b></font>", body_style),
                Paragraph(f"<b>Verified Net Earnings:</b> ₹{report_data.get('net_earnings_recorded', 0.0):.2f}", body_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[270, 270])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # 3. Working Shifts & Heat Summary
        elements.append(Paragraph("1. Recorded Working Shifts & Ambient Heat Exposure", section_style))
        shifts_summary = report_data.get("shifts_summary", [])
        if shifts_summary:
            shift_rows = [["Shift Start", "Duration", "Max Heat Index", "Risk Category", "Quality"]]
            for s in shifts_summary[:8]:
                hi_display = f"{s.get('max_heat_index'):.1f}°C" if s.get('max_heat_index') is not None else "N/A"
                shift_rows.append([
                    str(s.get("started_at", ""))[:16],
                    f"{s.get('total_working_minutes', 0)} mins",
                    hi_display,
                    s.get("risk_category", "LOW"),
                    s.get("quality_grade", "STANDARD"),
                ])
            shift_table = Table(shift_rows, colWidths=[120, 90, 100, 120, 110])
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
            elements.append(Paragraph("No working shifts recorded in this reporting period.", body_style))
        elements.append(Spacer(1, 14))

        # 4. Platform Earnings Evidence (EVID-05: Confirmed vs Unconfirmed)
        elements.append(Paragraph("2. Platform Earnings Evidence (Worker Verified)", section_style))
        earnings_summary = report_data.get("earnings_summary", [])
        if earnings_summary:
            earn_rows = [["Platform", "Period", "Base Pay", "Incentives", "Deductions", "Net Pay", "Verification"]]
            for e in earnings_summary[:6]:
                earn_rows.append([
                    e.get("platform", "Platform"),
                    str(e.get("period", ""))[:10],
                    f"₹{e.get('base', 0):.0f}",
                    f"₹{e.get('incentives', 0):.0f}",
                    f"₹{e.get('deductions', 0):.0f}",
                    f"₹{e.get('net', 0):.0f}",
                    "Worker Confirmed" if e.get("confirmed") else "Unconfirmed (Pending)",
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

        # 5. Integrity Hash & Legal Disclaimer
        elements.append(KeepTogether([
            Paragraph("3. Data Integrity & Scientific Caveats", section_style),
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
                f"<b>Canonical Evidence Payload Digest:</b> "
                f"<font color='#0284c7'>{report_data.get('canonical_payload_sha256', 'N/A')}</font>",
                body_style,
            ),
            Spacer(1, 4),
            Paragraph(
                "<i>Verification Notice: A SHA-256 hash confirms the document has not been altered since generation. "
                "It verifies file integrity, but does not independently prove the truth of external platform inputs. "
                "Verify this PDF by uploading it to the HeatLedger Verification API.</i>",
                disclaimer_style,
            ),
        ]))

        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
