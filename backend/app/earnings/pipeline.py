import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from backend.app.core.config import settings
from backend.app.core.storage import get_storage_provider
from backend.app.core.logging import logger
from backend.app.models.entities import EarningsUpload, EarningEntry, ProcessingJob, ConsentRecord, utc_now
from backend.app.earnings.parsers import extract_raw_text, validate_magic_bytes
from backend.app.earnings.extractor import EarningsExtractor
from backend.app.schemas.earnings import EarningEntryConfirmRequest
from backend.app.services.consent_service import ConsentService

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "csv"}

class EarningsPipeline:
    @staticmethod
    def _ensure_storage_dir(worker_id: str) -> str:
        # Prevent path traversal in worker_id
        safe_worker_id = "".join(c for c in worker_id if c.isalnum() or c in "-_")
        target_dir = os.path.join(settings.LOCAL_STORAGE_DIR, safe_worker_id)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    @staticmethod
    async def process_upload(
        db: Session,
        worker_id: str,
        file: UploadFile,
    ) -> Tuple[EarningsUpload, EarningEntry]:
        # EARN-06: Check if worker has explicitly revoked consent for earnings processing
        latest_consent = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.user_id == worker_id,
                ConsentRecord.purpose.in_(["EARNINGS_DOCUMENT_EXTRACTION", "EARNINGS_PROCESSING"]),
            )
            .order_by(ConsentRecord.created_at.desc())
            .first()
        )
        if latest_consent and not latest_consent.is_granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Processing rejected: Worker has explicitly revoked consent for 'earnings_processing'.",
            )
        
        # If no consent record exists yet, record initial document processing consent
        if not latest_consent:
            ConsentService.grant_consent(
                db, worker_id, "EARNINGS_DOCUMENT_EXTRACTION", consent_text_version="1.0-upload"
            )

        # 1. Validate file extension
        raw_filename = file.filename or "statement.pdf"
        # Prevent path traversal
        filename = os.path.basename(raw_filename).replace("..", "")
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '.{ext}'. Allowed types: {sorted(list(ALLOWED_EXTENSIONS))}",
            )

        # 2. Read contents and validate size
        contents = await file.read()
        if len(contents) > settings.MAX_UPLOAD_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB",
            )
        if len(contents) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file upload: 0 bytes received.",
            )

        # EARN-07: Magic bytes verification to prevent MIME spoofing
        if not validate_magic_bytes(contents, ext):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: Magic byte header does not match declared '.{ext}' format.",
            )

        # 3. Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(contents).hexdigest()

        # 4. Save to private storage
        storage = get_storage_provider()
        safe_worker_id = "".join(c for c in worker_id if c.isalnum() or c in "-_")
        rel_path = f"{safe_worker_id}/{sha256_hash}.{ext}"
        storage_path = storage.save_file(rel_path, contents)

        # 5. Create upload record
        upload = EarningsUpload(
            worker_id=worker_id,
            original_filename=filename,
            stored_filepath=storage_path,
            file_type=ext,
            file_size_bytes=len(contents),
            sha256_hash=sha256_hash,
            upload_status="PROCESSING",
            uploaded_at=utc_now(),
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        # 6. Extract text & structured AI fields
        try:
            raw_text = extract_raw_text(contents, ext)
            extracted_data = EarningsExtractor.parse_with_heuristics(raw_text, filename)

            # Parse start and end dates
            try:
                start_dt = datetime.strptime(extracted_data.statement_period_start[:10], "%Y-%m-%d")
            except Exception:
                start_dt = utc_now()

            try:
                end_dt = datetime.strptime(extracted_data.statement_period_end[:10], "%Y-%m-%d")
            except Exception:
                end_dt = utc_now()

            entry = EarningEntry(
                upload_id=upload.id,
                worker_id=worker_id,
                platform_name=extracted_data.platform_name,
                statement_period_start=start_dt,
                statement_period_end=end_dt,
                base_earnings=extracted_data.base_earnings,
                order_payments=extracted_data.order_payments,
                incentives=extracted_data.incentives,
                bonuses=extracted_data.bonuses,
                deductions=extracted_data.deductions,
                penalties=extracted_data.penalties,
                taxes=extracted_data.taxes,
                net_amount=extracted_data.net_amount,
                payment_date=end_dt,
                extraction_confidence=extracted_data.confidence_score,
                is_confirmed_by_worker=False, # Mandatory worker review
                worker_confirmed_at=None,
                worker_adjusted_notes=extracted_data.source_attribution_notes,
                raw_extracted_json=extracted_data.model_dump(),
            )
            db.add(entry)

            upload.upload_status = "PARSED"
            db.commit()
            db.refresh(upload)
            db.refresh(entry)
            return upload, entry

        except Exception as e:
            logger.error(f"Extraction pipeline failed: {str(e)}")
            upload.upload_status = "FAILED"
            db.commit()
            db.refresh(upload)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process earnings document: {str(e)}",
            )

    @staticmethod
    def confirm_earning_entry(
        db: Session,
        entry_id: str,
        worker_id: str,
        confirm_req: EarningEntryConfirmRequest,
    ) -> EarningEntry:
        entry = (
            db.query(EarningEntry)
            .filter(EarningEntry.id == entry_id, EarningEntry.worker_id == worker_id)
            .first()
        )
        if not entry:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Earning entry not found")

        # Apply worker adjustments if supplied
        if confirm_req.adjusted_base_earnings is not None:
            entry.base_earnings = confirm_req.adjusted_base_earnings
        if confirm_req.adjusted_incentives is not None:
            entry.incentives = confirm_req.adjusted_incentives
        if confirm_req.adjusted_deductions is not None:
            entry.deductions = confirm_req.adjusted_deductions
        if confirm_req.adjusted_net_amount is not None:
            entry.net_amount = confirm_req.adjusted_net_amount
        if confirm_req.worker_adjusted_notes:
            entry.worker_adjusted_notes = confirm_req.worker_adjusted_notes

        entry.is_confirmed_by_worker = confirm_req.is_confirmed
        entry.worker_confirmed_at = utc_now() if confirm_req.is_confirmed else None

        # Update upload status
        upload = db.query(EarningsUpload).filter(EarningsUpload.id == entry.upload_id).first()
        if upload and confirm_req.is_confirmed:
            upload.upload_status = "CONFIRMED"

        db.commit()
        db.refresh(entry)
        return entry
