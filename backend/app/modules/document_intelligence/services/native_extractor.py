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

    # The final verdict is `(char_count < 50) AND (image_coverage > 0.6)` —
    # so whenever this page already has >=50 characters of extractable text,
    # the result is False no matter what image_coverage turns out to be.
    # get_image_rects() below renders and MD5-hashes every image on the page
    # (PyMuPDF's own implementation), which is by far the most expensive part
    # of this function — on an image-heavy real-world document this doubled
    # end-to-end pipeline time once every page started getting scan-checked
    # (previously only page 0 was sampled). Skip it entirely when it cannot
    # change the outcome.
    if char_count >= 50:
        logger.debug(f"Page scan detection: chars={char_count} (>=50) — native text page, is_scanned=False")
        return False

    # Check image coverage (only reached when char_count < 50)
    page_area = page.rect.width * page.rect.height
    image_list = page.get_images(full=True)

    total_image_area = 0.0
    for img in image_list:
        img_rects = page.get_image_rects(img[0])
        for rect in img_rects:
            total_image_area += rect.width * rect.height

    image_coverage = total_image_area / page_area if page_area > 0 else 0

    # Heuristic: scanned if very few chars AND high image coverage
    is_scanned = image_coverage > 0.6

    logger.debug(
        f"Page scan detection: chars={char_count}, "
        f"image_coverage={image_coverage:.2%}, is_scanned={is_scanned}"
    )
    return is_scanned


def extract_page_native(
    page: "fitz.Page",
    page_number: int,
    is_scanned: Optional[bool] = None,
) -> Optional[PageExtractionResult]:
    """
    Extract text and bounding boxes from a single native digital PDF page.

    Uses PyMuPDF's 'dict' extraction mode which returns:
    - Blocks → Lines → Spans → Characters
    - Each span has: text, font, size, color, bbox [x0, y0, x1, y1]

    This is Layer 1 of the 6-layer pipeline.

    Args:
        is_scanned: pass the already-computed is_page_scanned(page) result if
            the caller has one (e.g. from a document-wide pre-pass) to avoid
            recomputing it. is_page_scanned() renders and MD5-hashes every
            image on the page (PyMuPDF's get_image_rects), which is expensive
            on image-heavy pages — calling it twice per page nearly doubled
            this function's runtime on a 74-page real-world test document.
            Leave as None to compute it here (backward compatible).
    """
    if not PYMUPDF_AVAILABLE:
        return None

    start_ms = time.time() * 1000

    try:
        # Check if scanned — if so, signal caller to use Tier 2
        scanned = is_page_scanned(page) if is_scanned is None else is_scanned

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

    # Well-name extraction, in priority order, each candidate VALIDATED before
    # acceptance rather than taking the first regex hit blindly. Real-data
    # testing (Volve field documents) found the original single pattern —
    # `WELL\s*(?:NAME|NO|NUMBER|#)?[:\.\s]+(...)` with an OPTIONAL qualifier —
    # matched "WELL REPORT", "WELL CONTROL", "WELL EVALUATION" etc. just as
    # readily as an actual labeled well name, since any word after "WELL "
    # satisfied it. 13 of 14 real test documents got a garbage well name this
    # way (correct in only 1/14). A real well identifier always contains at
    # least one digit (15/9-F-1, NHK-001, F-12); a section heading generally
    # doesn't — used as the acceptance filter below rather than a fixed
    # blacklist, so it isn't tied to the specific bad words seen in this one
    # test set.
    _WELL_CANDIDATE_HAS_DIGIT = re.compile(r"\d")

    def _valid_well_candidate(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        candidate = raw.strip().strip(":.-_ ")
        if len(candidate) < 2 or len(candidate) > 40:
            return None
        if not _WELL_CANDIDATE_HAS_DIGIT.search(candidate):
            return None
        return candidate

    extracted_well = None

    # 1. Strict: an explicit "Well Name/No/Number/#" label (qualifier
    #    required, not optional) — the least ambiguous signal when present.
    #    Punctuation after the qualifier is OPTIONAL, not required: real
    #    documents (Volve field reports) use "Well NO 15/9-F-11..." with only
    #    whitespace, no colon. The qualifier requirement alone is what
    #    excludes false matches like "Final Well Report" (title text)
    #    elsewhere on the same page — "Report" isn't NAME/NO/NUMBER/#, so it
    #    can't satisfy this pattern regardless of punctuation.
    strict_match = re.search(
        r"WELL\s*(?:NAME|NO\.?|NUMBER|#)\s*[:\.]?\s*([A-Z0-9][A-Z0-9\(\)\-_/ ]{1,35}?)(?:\n|\r|,|$)",
        first_page_text, re.IGNORECASE,
    )
    extracted_well = _valid_well_candidate(strict_match.group(1) if strict_match else None)

    # 1b. A line-leading "Well:" label (colon required) — the common DDR
    #     header form ("Well: HGJ-011"). Checked before the filename so a
    #     report's own header wins over whatever the file happened to be named.
    if not extracted_well:
        label_match = re.search(r"^\s*WELL\s*:\s*([A-Z0-9][A-Z0-9\-_/]{1,30})\s*$", first_page_text, re.IGNORECASE | re.MULTILINE)
        extracted_well = _valid_well_candidate(label_match.group(1) if label_match else None)

    # 2. Filename: this project's own convention (and Volve's real filenames,
    #    e.g. "WELL-15_9-F-1C_DRILLING_REPORT.pdf") often names the well
    #    directly — a good source once the strict label isn't found.
    if not extracted_well:
        # api/routes/ingest.py saves uploads as "{job_id}_{original_filename}"
        # for storage-collision safety (job_id like "JOB-39858BE94E") — found
        # via real-data re-testing that this hex job-id prefix was itself
        # matching the well-ID shape below (e.g. "D59F2BC68F_WELL-15" was
        # extracted as the well name, the job ID mistaken for the well's first
        # segment). Strip that known prefix before matching rather than
        # trying to make the shape pattern guess around it.
        filename_for_match = re.sub(r"^JOB-[0-9A-F]+_", "", filename, flags=re.IGNORECASE)
        # Bounded to the well-ID shape itself (digits-separator-digits-hyphen-
        # letter[-digits]) rather than a generic greedy character class — the
        # latter swallowed trailing "_DOCTYPE" filename suffixes (e.g.
        # "15_9-F-1_BIOSTRAT" instead of "15_9-F-1") on this project's own
        # "WELL-<id>_<DOCTYPE>.pdf" naming convention.
        fn_match = re.search(
            r"(?:WELL[-_])?([A-Z0-9]+[_/][A-Z0-9]+-[A-Z0-9]+(?:-[A-Z0-9]+)?)",
            filename_for_match, re.IGNORECASE,
        )
        extracted_well = _valid_well_candidate(fn_match.group(1) if fn_match else None)

    # 3. Loose fallback: the original permissive "WELL <word>" pattern, but
    #    now filtered through the same digit-presence validity check instead
    #    of being accepted unconditionally.
    if not extracted_well:
        loose_match = re.search(r"WELL\s*(?:NAME|NO|NUMBER|#)?[:\.\s]+([A-Z0-9\(\)\-_/]+)", first_page_text, re.IGNORECASE)
        extracted_well = _valid_well_candidate(loose_match.group(1) if loose_match else None)
    op_match = (
        re.search(r"OPERATOR[:\.\s]+([A-Za-z0-9\s]+?)(?:\n|WELL|FIELD|—|–|\r)", first_page_text, re.IGNORECASE)
        or re.search(r"(?:Utah FORGE|Oil India|ONGC|Equinor|Shell|Chevron|BP)", first_page_text, re.IGNORECASE)
    )
    date_match = re.search(r"(?:DATE|REPORT\s*DATE)[:\.\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", first_page_text, re.IGNORECASE)

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
