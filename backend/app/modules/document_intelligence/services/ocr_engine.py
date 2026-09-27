"""
NWIS Module: Tier 2 Layout-Aware OCR Engine.
Uses IBM Research Docling for scanned/raster PDF pages.
"""

from __future__ import annotations
import time
from pathlib import Path
from typing import Optional
from app.core.logging import logger

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    DOCLING_AVAILABLE = True
    logger.info("Docling available — using layout-aware OCR (Tier 2 primary)")
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning(
        "Docling not available. Run: pip install docling. "
        "Falling back to basic text extraction."
    )

from app.modules.document_intelligence.models.schemas import PageExtractionResult, ExtractionTier

_docling_converter: Optional["DocumentConverter"] = None


def _get_docling_converter() -> Optional["DocumentConverter"]:
    global _docling_converter
    if _docling_converter is not None:
        return _docling_converter

    if not DOCLING_AVAILABLE:
        return None

    try:
        logger.info("Initializing Docling converter...")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.do_cell_matching = True

        _docling_converter = DocumentConverter()
        logger.success("Docling converter ready")
        return _docling_converter
    except Exception as exc:
        logger.error(f"Failed to initialize Docling: {exc}")
        return None


def extract_document_with_docling(pdf_path: Path) -> dict:
    converter = _get_docling_converter()
    if converter is None:
        logger.warning("Docling unavailable — returning empty extraction")
        return {}

    if not pdf_path.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return {}

    start_ms = time.time() * 1000
    logger.info(f"Tier 2 Docling OCR starting: {pdf_path.name}")

    try:
        result = converter.convert(str(pdf_path))
        elapsed = time.time() * 1000 - start_ms

        full_markdown = result.document.export_to_markdown()

        page_count = len(result.document.pages) if hasattr(result.document, "pages") else 0
        page_markdown: dict[int, str] = {}
        if page_count > 0:
            for page_no in range(1, page_count + 1):
                try:
                    page_markdown[page_no - 1] = result.document.export_to_markdown(page_no=page_no)
                except TypeError:
                    break
                except Exception as pe:
                    logger.debug(f"Per-page markdown export failed for page {page_no}: {pe}")

        tables_data = []
        for table in result.document.tables:
            try:
                table_md = table.export_to_markdown()
                rows = _parse_markdown_table(table_md)
                tables_data.append({
                    "markdown": table_md,
                    "rows": rows,
                    "num_rows": len(rows),
                    "num_cols": len(rows[0]) if rows else 0,
                })
            except Exception as te:
                logger.debug(f"Table parsing error: {te}")
                continue

        logger.success(
            f"Tier 2 Docling completed: {pdf_path.name} in {elapsed:.0f}ms. "
            f"Tables found: {len(tables_data)}"
        )

        if page_count > 0 and len(page_markdown) < page_count:
            logger.warning(
                f"Per-page markdown split incomplete ({len(page_markdown)}/{page_count} pages). "
                "Affected scanned pages will fall back to full-document markdown."
            )

        return {
            "full_markdown": full_markdown,
            "page_markdown": page_markdown,
            "tables": tables_data,
            "processing_time_ms": round(elapsed, 2),
            "page_count": page_count,
        }

    except Exception as exc:
        elapsed = time.time() * 1000 - start_ms
        logger.error(f"Docling extraction failed: {exc}")
        return {
            "full_markdown": "",
            "page_markdown": {},
            "tables": [],
            "processing_time_ms": round(elapsed, 2),
            "error": str(exc),
        }


def _parse_markdown_table(markdown_table: str) -> list[list[str]]:
    rows = []
    for line in markdown_table.strip().splitlines():
        line = line.strip()
        if not line or set(line.replace("|", "").replace("-", "").replace(" ", "")) == set():
            continue
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            if cells:
                rows.append(cells)
    return rows


def extract_text_from_markdown(markdown: str) -> str:
    import re
    cleaned = re.sub(r"\|[-: ]+\|[-: |]+", "", markdown)
    cleaned = re.sub(r"\|", " ", cleaned)
    cleaned = re.sub(r"\s{3,}", "\n", cleaned)
    return cleaned.strip()


def create_tier2_page_result(
    page_number: int,
    docling_result: dict,
    page_text_fallback: str = "",
) -> PageExtractionResult:
    page_specific = docling_result.get("page_markdown", {}).get(page_number)

    if page_specific is not None:
        plain_text = extract_text_from_markdown(page_specific)
        confidence = 0.95
    elif docling_result.get("full_markdown"):
        plain_text = extract_text_from_markdown(docling_result["full_markdown"])
        confidence = 0.55
        logger.debug(f"Page {page_number}: using whole-document OCR text as fallback")
    else:
        plain_text = page_text_fallback or (
            "[NO OCR ENGINE AVAILABLE — this page is a scanned image and could not "
            "be read. Install `docling` to enable OCR for scanned pages.]"
        )
        confidence = 0.0

    proc_time = docling_result.get("processing_time_ms", 0.0)

    return PageExtractionResult(
        page_number=page_number,
        is_scanned=True,
        extraction_tier=ExtractionTier.TIER2_OCR,
        processing_time_ms=proc_time,
        raw_text_preview=plain_text[:1000],
        page_confidence=confidence,
    )
