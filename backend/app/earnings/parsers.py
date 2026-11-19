"""Document parsers for PDF, Images, and CSV earnings statements.
EARN-01 & EARN-02: Real PDF stream parsing with PyPDF and optical character recognition with Tesseract/Pillow.
Never fabricates placeholder text or successful extraction on parse failures.
"""
import csv
import io
import os
import re
from typing import Optional, Tuple, List
from pypdf import PdfReader
from PIL import Image
from backend.app.core.logging import logger

def parse_csv_file(file_bytes: bytes) -> str:
    """Extracts structured text from CSV platform payout reports."""
    try:
        # Support UTF-8, UTF-8-sig (with BOM), and Latin-1 fallbacks
        try:
            decoded = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = file_bytes.decode("latin-1", errors="replace")

        reader = csv.reader(io.StringIO(decoded))
        lines = []
        for row in reader:
            if any(cell.strip() for cell in row):
                lines.append(" | ".join(cell.strip() for cell in row))
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"CSV parse error: {str(e)}")
        return f"[CSV_PARSE_ERROR: {str(e)}]"

def parse_pdf_file(file_bytes: bytes) -> str:
    """Extracts text stream from PDF statements using PyPDF page-by-page."""
    try:
        pdf_stream = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_stream)

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                return "[PDF_PARSE_ERROR: Document is password protected and cannot be extracted without the password.]"

        extracted_pages = []
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                extracted_pages.append(f"--- PAGE {page_idx + 1} ---\n{text.strip()}")

        if not extracted_pages:
            return "[PDF_PARSE_ERROR: Document contains no extractable text stream. It may be a rasterized or scanned document requiring OCR.]"

        return "\n\n".join(extracted_pages)
    except Exception as e:
        logger.error(f"PyPDF extraction error: {str(e)}")
        return f"[PDF_PARSE_ERROR: Corrupted or invalid PDF structure: {str(e)}]"

def parse_image_file(file_bytes: bytes) -> str:
    """
    EARN-01: Extracts text from image files (PNG, JPG, JPEG) using Optical Character Recognition (OCR).
    Uses Tesseract via pytesseract with image verification.
    If OCR engine is not locally installed or fails, reports honest extraction failure.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Verify valid image structure
        image.verify()
        
        # Re-open after verify() closes the stream
        image = Image.open(io.BytesIO(file_bytes))

        # Convert palette/RGBA images to RGB for optimal OCR contrast
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")

        import pytesseract
        text = pytesseract.image_to_string(image)
        if not text or not text.strip():
            return "[OCR_NOTICE: Image processed successfully but no textual characters were detected. Please ensure image is well-lit and legible.]"
        return text.strip()
    except ImportError:
        logger.warning("pytesseract package not installed.")
        return "[OCR_UNAVAILABLE: Optical Character Recognition engine is not configured on this host. Please upload a PDF or CSV statement.]"
    except Exception as e:
        err_str = str(e)
        logger.warning(f"OCR processing failed: {err_str}")
        if "tesseract is not installed" in err_str.lower() or "not found" in err_str.lower():
            return "[OCR_UNAVAILABLE: Tesseract OCR binary not found in system PATH. Please provide a digital text-based PDF or CSV payout slip.]"
        return f"[OCR_ERROR: Failed to process image: {err_str}]"

def validate_magic_bytes(file_bytes: bytes, declared_type: str) -> bool:
    """EARN-07: Validates magic bytes signature against declared file type to prevent extension spoofing."""
    dt = declared_type.lower().replace(".", "")
    if dt == "pdf":
        return file_bytes.startswith(b"%PDF-")
    elif dt == "png":
        return file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    elif dt in ["jpg", "jpeg"]:
        return file_bytes.startswith(b"\xff\xd8\xff")
    elif dt == "csv":
        # Check that CSV is printable ASCII/UTF-8 text without binary null bytes
        return b"\x00" not in file_bytes[:1024]
    return True

def extract_raw_text(file_bytes: bytes, file_type: str) -> str:
    f_type = file_type.lower().replace(".", "")
    if f_type == "csv":
        return parse_csv_file(file_bytes)
    elif f_type == "pdf":
        return parse_pdf_file(file_bytes)
    elif f_type in ["jpg", "jpeg", "png"]:
        return parse_image_file(file_bytes)
    else:
        return file_bytes.decode("utf-8", errors="replace")[:4000]
