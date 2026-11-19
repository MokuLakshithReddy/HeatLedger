"""AI Document Extraction Engine
Uses Gemini API or deterministic layout intelligence to parse multi-platform gig payout statements
into validated Pydantic structures.
"""
import json
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.earnings import ExtractionStructuredResult

class EarningsExtractor:
    @staticmethod
    def parse_with_heuristics(raw_text: str, filename: str) -> ExtractionStructuredResult:
        """
        Deterministic, platform-independent extraction heuristics for Indian delivery statements:
        Swiggy, Zomato, Uber, Ola, Porter, Zepto, Blinkit.
        """
        lower = raw_text.lower()
        
        # 1. Identify platform
        platform = "Gig Platform"
        for candidate in ["Swiggy", "Zomato", "Uber", "Ola", "Porter", "Zepto", "Blinkit", "Amazon Flex"]:
            if candidate.lower() in lower or candidate.lower() in filename.lower():
                platform = candidate
                break

        # 2. Extract dates (YYYY-MM-DD or DD/MM/YYYY)
        dates = re.findall(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b", raw_text)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = dates[0] if len(dates) > 0 else today
        end_date = dates[1] if len(dates) > 1 else start_date

        # 3. Currency / number extraction
        def find_amount(keywords: list) -> float:
            for kw in keywords:
                pattern = rf"{kw}[:\s\-₹Rs\.]*([\d,]+\.?\d*)"
                match = re.search(pattern, raw_text, re.IGNORECASE)
                if match:
                    try:
                        val = float(match.group(1).replace(",", ""))
                        return val
                    except ValueError:
                        continue
            return 0.0

        base_earnings = find_amount(["base pay", "base earnings", "trip earnings", "order pay", "delivery fee"])
        order_pay = find_amount(["per order", "order payments", "ride fares"])
        incentives = find_amount(["incentives", "daily incentive", "weekly incentive", "surge"])
        bonuses = find_amount(["bonus", "joining bonus", "referral bonus"])
        deductions = find_amount(["deductions", "penalty", "tcs", "tds deduction", "bag fee"])
        penalties = find_amount(["penalty", "late cancellation", "complaint penalty"])
        taxes = find_amount(["tax", "tds", "gst"])
        net_amount = find_amount(["net pay", "net payout", "total earnings", "transferred to bank", "net amount"])

        # If net amount was not found, calculate from components
        if net_amount == 0.0 and (base_earnings > 0 or incentives > 0):
            net_amount = base_earnings + order_pay + incentives + bonuses - deductions - penalties - taxes

        confidence = 0.85 if platform != "Gig Platform" and net_amount > 0 else 0.60

        return ExtractionStructuredResult(
            platform_name=platform,
            statement_period_start=start_date,
            statement_period_end=end_date,
            base_earnings=round(base_earnings, 2),
            order_payments=round(order_pay, 2),
            incentives=round(incentives, 2),
            bonuses=round(bonuses, 2),
            deductions=round(deductions, 2),
            penalties=round(penalties, 2),
            taxes=round(taxes, 2),
            net_amount=round(net_amount, 2),
            payment_date=end_date,
            confidence_score=confidence,
            source_attribution_notes=f"Extracted deterministically from document text ({filename}). Requires worker verification.",
        )

    @staticmethod
    async def extract_structured_data(
        raw_text: str, filename: str
    ) -> ExtractionStructuredResult:
        # If Gemini API Key is available, invoke structured extraction
        if settings.GEMINI_API_KEY:
            try:
                prompt = f"""
                You are a senior financial document auditor extracting gig worker payout information from Indian delivery statements (e.g. Swiggy, Zomato, Uber, Zepto).
                Extract the fields into JSON matching this exact structure:
                {{
                    "platform_name": "String",
                    "statement_period_start": "YYYY-MM-DD",
                    "statement_period_end": "YYYY-MM-DD",
                    "base_earnings": 0.0,
                    "order_payments": 0.0,
                    "incentives": 0.0,
                    "bonuses": 0.0,
                    "deductions": 0.0,
                    "penalties": 0.0,
                    "taxes": 0.0,
                    "net_amount": 0.0,
                    "payment_date": "YYYY-MM-DD or null",
                    "confidence_score": 0.95,
                    "source_attribution_notes": "Summary of extracted line items"
                }}
                CRITICAL RULES:
                - Never invent missing amounts. If absent, set to 0.0.
                - Document: {filename}
                - Raw Text Content:
                {raw_text[:4000]}
                """
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL_NAME}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"response_mime_type": "application/json"},
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_json_str = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(raw_json_str)
                        return ExtractionStructuredResult(**parsed)
                    else:
                        logger.warning(f"Gemini API returned {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"Gemini LLM extraction failed: {e}. Falling back to deterministic heuristics.")

        # Fallback to deterministic regex parser
        return EarningsExtractor.parse_with_heuristics(raw_text, filename)
