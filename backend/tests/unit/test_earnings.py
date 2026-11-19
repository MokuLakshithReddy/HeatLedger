import pytest
import io
from fastapi import UploadFile
from backend.app.earnings.extractor import EarningsExtractor
from backend.app.earnings.parsers import parse_csv_file
from backend.app.earnings.pipeline import EarningsPipeline
from backend.app.schemas.earnings import EarningEntryConfirmRequest

def test_earnings_csv_text_parser():
    csv_bytes = b"Date,Platform,Order Earnings,Incentives,Deductions,Net Payout\n2026-05-10,Swiggy,3200,800,100,3900\n"
    text = parse_csv_file(csv_bytes)
    assert "Swiggy" in text
    assert "3900" in text

def test_deterministic_earnings_extraction():
    sample_text = (
        "SWIGGY WEEKLY DELIVERY REPORT\n"
        "Period: 2026-05-01 to 2026-05-07\n"
        "Trip Earnings: Rs. 4,500.00\n"
        "Weekly Incentive: Rs. 1,200.00\n"
        "Deductions: Rs. 200.00\n"
        "Total Transferred to Bank: Rs. 5,500.00\n"
    )
    result = EarningsExtractor.parse_with_heuristics(sample_text, "swiggy_payout.pdf")
    assert result.platform_name == "Swiggy"
    assert result.base_earnings == 4500.0
    assert result.incentives == 1200.0
    assert result.deductions == 200.0
    assert result.net_amount == 5500.0
    assert result.confidence_score >= 0.80

@pytest.mark.asyncio
async def test_earnings_upload_and_worker_confirmation(db_session, worker_user):
    file_content = b"Date | Platform | Base Pay | Incentives | Net Pay\n2026-05-12 | Zomato | 3000 | 500 | 3500\n"
    upload_file = UploadFile(
        filename="zomato_statement.csv",
        file=io.BytesIO(file_content),
    )

    upload, entry = await EarningsPipeline.process_upload(db_session, worker_user.id, upload_file)
    assert upload.upload_status == "PARSED"
    assert upload.sha256_hash is not None
    assert entry.is_confirmed_by_worker is False # Must require worker review

    # Worker reviews and confirms with custom notes
    confirm_req = EarningEntryConfirmRequest(
        is_confirmed=True,
        adjusted_net_amount=3500.0,
        worker_adjusted_notes="Verified with Bank UPI transaction ref #998877",
    )
    confirmed_entry = EarningsPipeline.confirm_earning_entry(
        db_session, entry.id, worker_user.id, confirm_req
    )
    assert confirmed_entry.is_confirmed_by_worker is True
    assert confirmed_entry.worker_confirmed_at is not None
    assert "Bank UPI" in confirmed_entry.worker_adjusted_notes
