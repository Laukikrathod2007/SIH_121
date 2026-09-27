"""
NWIS Module: Tier 1 Native Digital PDF Extractor.
PyMuPDF direct text and visual bounding box extraction.
"""

from __future__ import annotations
import time
from pathlib import Path
from typing import Optional
from app.core.logging import logger

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed. Run: pip install pymupdf")

from app.modules.document_intelligence.models.schemas import (
    PageExtractionResult,
    ExtractionTier,
    BoundingBox,
)

SCANNED_PAGE_THRESHOLD = 0.10


def is_page_scanned(page: "fitz.Page") -> bool:
    if not PYMUPDF_AVAILABLE:
        return True

    text = page.get_text("text").strip()
    char_count = len(text)

    page_area = page.rect.width * page.rect.height
    image_list = page.get_images(full=True)

    total_image_area = 0.0
    for img in image_list:
        img_rects = page.get_image_rects(img[0])
        for rect in img_rects:
            total_image_area += rect.width * rect.height

    image_coverage = total_image_area / page_area if page_area > 0 else 0
    is_scanned = (char_count < 50) and (image_coverage > 0.6)

    logger.debug(
        f"Page scan detection: chars={char_count}, "
        f"image_coverage={image_coverage:.2%}, is_scanned={is_scanned}"
    )
    return is_scanned


def extract_page_native(
    page: "fitz.Page",
    page_number: int,
) -> Optional[PageExtractionResult]:
    if not PYMUPDF_AVAILABLE:
        return None

    start_ms = time.time() * 1000

    try:
        scanned = is_page_scanned(page)

        if scanned:
            elapsed = time.time() * 1000 - start_ms
            return PageExtractionResult(
                page_number=page_number,
                is_scanned=True,
                extraction_tier=ExtractionTier.TIER2_OCR,
                processing_time_ms=elapsed,
                raw_text_preview="[SCANNED PAGE — Routing to Tier 2 Docling OCR]",
            )

        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        all_text_parts = []
        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            all_text_parts.append(text)

        raw_text = " | ".join(all_text_parts)
        elapsed = time.time() * 1000 - start_ms

        result = PageExtractionResult(
            page_number=page_number,
            is_scanned=False,
            extraction_tier=ExtractionTier.TIER1_NATIVE,
            processing_time_ms=round(elapsed, 2),
            raw_text_preview=raw_text[:1000],
            page_confidence=0.99,
        )

        logger.success(
            f"Tier 1 extracted page {page_number} in {elapsed:.1f}ms "
            f"({len(raw_text)} chars)"
        )
        return result

    except Exception as exc:
        logger.error(f"Tier 1 extraction failed on page {page_number}: {exc}")
        return None


def get_word_bounding_boxes(page: "fitz.Page") -> list[dict]:
    if not PYMUPDF_AVAILABLE:
        return []

    words = page.get_text("words")
    result = []
    for w in words:
        x0, y0, x1, y1, word_text, *_ = w
        result.append({
            "text": word_text.strip(),
            "bbox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
            "page": page.number,
        })
    return result


def detect_document_type(doc: "fitz.Document") -> str:
    if not PYMUPDF_AVAILABLE or len(doc) == 0:
        return "UNKNOWN"

    text_sample = ""
    for i in range(min(2, len(doc))):
        text_sample += doc[i].get_text("text").upper()

    keywords = {
        "DAILY_DRILLING_REPORT": [
            "DAILY DRILLING REPORT", "DDR", "DAILY REPORT", "MORNING REPORT",
        ],
        "WELL_COMPLETION_REPORT": [
            "WELL COMPLETION REPORT", "WCR", "COMPLETION REPORT",
            "FINAL WELL REPORT",
        ],
        "MUD_LOG": [
            "MUD LOG", "MUDLOG", "LITHOLOGY LOG", "FORMATION EVALUATION",
        ],
    }

    for doc_type, kws in keywords.items():
        if any(kw in text_sample for kw in kws):
            logger.info(f"Document type detected: {doc_type}")
            return doc_type

    return "UNKNOWN"


def extract_document_metadata(doc: "fitz.Document", filename: str) -> dict:
    if not PYMUPDF_AVAILABLE:
        return {}

    import re
    meta = doc.metadata or {}
    first_page_text = doc[0].get_text("text") if len(doc) > 0 else ""

    well_match = (
        re.search(r"WELL\s*(?:NAME|NO|NUMBER|#)?[:\.\s]+([A-Z0-9\(\)\-_/]+)", first_page_text, re.IGNORECASE)
        or re.search(r"Well\s+([A-Z0-9\(\)\-_/]+)", filename, re.IGNORECASE)
    )
    op_match = (
        re.search(r"OPERATOR[:\.\s]+([A-Za-z0-9\s]+?)(?:\n|WELL|FIELD|—|–|\r)", first_page_text, re.IGNORECASE)
        or re.search(r"(?:Utah FORGE|Oil India|ONGC|Equinor|Shell|Chevron|BP)", first_page_text, re.IGNORECASE)
    )
    date_match = re.search(r"(?:DATE|REPORT\s*DATE)[:\.\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", first_page_text, re.IGNORECASE)

    extracted_well = well_match.group(1).strip() if (well_match and well_match.groups()) else (well_match.group(0).strip() if well_match else None)
    extracted_op = op_match.group(1).strip() if (op_match and op_match.groups()) else (op_match.group(0).strip() if op_match else None)

    return {
        "well_name": extracted_well,
        "operator": extracted_op,
        "report_date": date_match.group(1).strip() if date_match else None,
        "total_pages": len(doc),
        "pdf_title": meta.get("title", ""),
        "pdf_author": meta.get("author", ""),
        "source_filename": filename,
    }
