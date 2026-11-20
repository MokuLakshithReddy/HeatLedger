"""AI Document Extraction Engine
Uses Gemini API or deterministic layout intelligence to parse multi-platform gig payout statements
into validated Pydantic structures.
EARN-03, EARN-04, EARN-05: Eliminates double counting, uses Decimal-safe arithmetic, and validates totals.
"""
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.earnings import ExtractionStructuredResult

def round_money(val: float) -> float:
    d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(d)

class EarningsExtractor:
    @staticmethod
    def parse_with_heuristics(raw_text: str, filename: str) -> ExtractionStructuredResult:
        """
        Deterministic, platform-independent extraction heuristics for Indian delivery statements:
        Swiggy, Zomato, Uber, Ola, Porter, Zepto, Blinkit.
        Strictly prevents double-counting by classifying each line item at most once.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Check if parser returned an error or unreadable notice
        if raw_text.startswith("[") and ("ERROR" in raw_text or "UNAVAILABLE" in raw_text or "NOTICE" in raw_text):
            raise ValueError(f"Document extraction failed due to unreadable content or OCR unavailability: {raw_text}")

        lower = raw_text.lower()
        
        # 1. Identify platform
        platform = "Gig Platform"
        for candidate in ["Swiggy", "Zomato", "Uber", "Ola", "Porter", "Zepto", "Blinkit", "Amazon Flex"]:
            if candidate.lower() in lower or candidate.lower() in filename.lower():
                platform = candidate
                break

        # 2. Extract dates (YYYY-MM-DD or DD/MM/YYYY)
        dates = re.findall(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", raw_text)
        start_date = dates[0] if len(dates) > 0 else today
        end_date = dates[1] if len(dates) > 1 else start_date

        # 3. Line-by-line single classification to prevent double counting (EARN-04)
        base_earnings = Decimal("0.0")
        order_pay = Decimal("0.0")
        incentives = Decimal("0.0")
        bonuses = Decimal("0.0")
        deductions = Decimal("0.0")
        penalties = Decimal("0.0")
        taxes = Decimal("0.0")
        explicit_net = Decimal("0.0")

        lines = raw_text.splitlines()
        
        # Regex to find currency amounts on a line
        amount_regex = re.compile(r"[:\s\-₹Rs\.]*([\d,]+\.?\d*)")

        def extract_first_num(line_str: str) -> Optional[Decimal]:
            m = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+\.?\d+)", line_str, re.IGNORECASE)
            if m:
                try:
                    cleaned = m.group(1).replace(",", "")
                    val = Decimal(cleaned)
                    return val if val > Decimal("0") else None
                except Exception:
                    return None
            return None

        classified_lines = set()

        for idx, line in enumerate(lines):
            l = line.lower().strip()
            if not l or len(l) < 3:
                continue

            num = extract_first_num(l)
            if not num:
                continue

            # Classify into exact category in priority order (EARN-04)
            if any(k in l for k in ["net payout", "net amount", "total payout", "transferred to bank", "take home", "final amount", "net pay"]):
                explicit_net = num
                classified_lines.add(idx)
            elif any(k in l for k in ["cancellation penalty", "complaint penalty", "fine", "penalty"]) and "no penalty" not in l:
                penalties += num
                classified_lines.add(idx)
            elif any(k in l for k in ["tds", "tcs", "gst", "tax deduction"]):
                taxes += num
                classified_lines.add(idx)
            elif any(k in l for k in ["insurance deduction", "bag fee", "uniform fee", "loan deduction", "deduction"]):
                deductions += num
                classified_lines.add(idx)
            elif any(k in l for k in ["joining bonus", "referral bonus", "milestone bonus", "bonus"]):
                bonuses += num
                classified_lines.add(idx)
            elif any(k in l for k in ["incentive", "daily incentive", "weekly incentive", "surge pay", "rain surge", "peak incentive"]):
                incentives += num
                classified_lines.add(idx)
            elif any(k in l for k in ["order pay", "order payments", "ride fares", "per order fee", "drop pay", "trip pay"]):
                order_pay += num
                classified_lines.add(idx)
            elif any(k in l for k in ["base pay", "base earnings", "trip earnings", "delivery fee", "standard earnings"]):
                base_earnings += num
                classified_lines.add(idx)

        # Fallback keyword search across entire document if line-by-line found nothing
        if base_earnings == Decimal("0") and order_pay == Decimal("0") and incentives == Decimal("0"):
            def find_global(keywords: list) -> Decimal:
                for kw in keywords:
                    pattern = rf"{kw}[:\s\-₹Rs\.]*([\d,]+\.?\d*)"
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        try:
                            return Decimal(match.group(1).replace(",", ""))
                        except Exception:
                            continue
                return Decimal("0.0")

            base_earnings = find_global(["base pay", "base earnings", "trip earnings", "delivery fee"])
            order_pay = find_global(["per order", "order payments", "ride fares"])
            incentives = find_global(["daily incentive", "weekly incentive", "surge pay", "incentive"])
            bonuses = find_global(["joining bonus", "referral bonus", "bonus"])
            deductions = find_global(["bag fee", "uniform fee", "insurance deduction", "deductions"])
            penalties = find_global(["cancellation penalty", "complaint penalty", "penalty"])
            taxes = find_global(["tds", "tcs", "gst", "tax"])
            explicit_net = find_global(["net payout", "net amount", "total payout", "transferred to bank", "net pay"])

        # EARN-05: Decimal calculation of net earnings
        calculated_net = base_earnings + order_pay + incentives + bonuses - deductions - penalties - taxes
        if explicit_net > Decimal("0.0"):
            final_net = explicit_net
        else:
            final_net = max(Decimal("0.0"), calculated_net)

        discrepancy_note = ""
        if explicit_net > Decimal("0.0") and abs(explicit_net - calculated_net) > Decimal("1.0"):
            discrepancy_note = (
                f" Note: Stated net (₹{explicit_net}) differs from sum of components (₹{calculated_net}). "
                f"Worker review and confirmation is recommended."
            )

        has_any_earnings = (
            base_earnings > Decimal("0.0")
            or order_pay > Decimal("0.0")
            or incentives > Decimal("0.0")
            or bonuses > Decimal("0.0")
            or explicit_net > Decimal("0.0")
        )

        if not has_any_earnings:
            confidence = 0.10
            discrepancy_note += " Warning: No recognized monetary amounts found in statement."
        else:
            confidence = 0.90 if platform != "Gig Platform" and final_net > Decimal("0.0") else 0.65

        date_inferred = len(dates) == 0

        return ExtractionStructuredResult(
            platform_name=platform,
            statement_period_start=start_date,
            statement_period_end=end_date,
            base_earnings=round_money(float(base_earnings)),
            order_payments=round_money(float(order_pay)),
            incentives=round_money(float(incentives)),
            bonuses=round_money(float(bonuses)),
            deductions=round_money(float(deductions)),
            penalties=round_money(float(penalties)),
            taxes=round_money(float(taxes)),
            net_amount=round_money(float(final_net)),
            payment_date=end_date,
            confidence_score=confidence,
            source_attribution_notes=(
                f"Extracted deterministically from document text ({filename})."
                f"{discrepancy_note}"
                f"{' Note: Dates were inferred.' if date_inferred else ''} Worker verification required."
            ),
        )

    @classmethod
    async def extract(cls, raw_text: str, filename: str) -> ExtractionStructuredResult:
        """
        Extracts structured earnings data. Uses Google Gemini API if configured,
        falling back seamlessly to robust heuristic classification.
        """
        if settings.GEMINI_API_KEY and settings.LLM_PROVIDER in ["gemini", "google"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"
                prompt = (
                    "Extract structured financial payout fields from this Indian gig worker earnings statement into JSON. "
                    "Fields required: platform_name (Swiggy, Zomato, Uber, Ola, etc.), statement_period_start (YYYY-MM-DD), "
                    "statement_period_end (YYYY-MM-DD), base_earnings (float), order_payments (float), incentives (float), "
                    "bonuses (float), deductions (float), penalties (float), taxes (float), net_amount (float). "
                    "Ensure no double counting. Return pure JSON object only."
                )
                payload = {
                    "contents": [{"parts": [{"text": f"{prompt}\n\nDocument Text:\n{raw_text[:4000]}"}]}],
                    "generationConfig": {"response_mime_type": "application/json"}
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(text_resp)
                        return ExtractionStructuredResult(
                            platform_name=parsed.get("platform_name", "Gig Platform"),
                            statement_period_start=parsed.get("statement_period_start", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                            statement_period_end=parsed.get("statement_period_end", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                            base_earnings=round_money(float(parsed.get("base_earnings", 0.0))),
                            order_payments=round_money(float(parsed.get("order_payments", 0.0))),
                            incentives=round_money(float(parsed.get("incentives", 0.0))),
                            bonuses=round_money(float(parsed.get("bonuses", 0.0))),
                            deductions=round_money(float(parsed.get("deductions", 0.0))),
                            penalties=round_money(float(parsed.get("penalties", 0.0))),
                            taxes=round_money(float(parsed.get("taxes", 0.0))),
                            net_amount=round_money(float(parsed.get("net_amount", 0.0))),
                            payment_date=parsed.get("statement_period_end"),
                            confidence_score=0.95,
                            source_attribution_notes=f"Extracted with Gemini AI model ({settings.LLM_MODEL_NAME}). Worker verification required.",
                        )
            except Exception as e:
                logger.warning(f"Gemini API extraction failed, falling back to heuristics: {e}")

        return cls.parse_with_heuristics(raw_text, filename)
