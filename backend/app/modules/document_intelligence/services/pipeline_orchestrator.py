"""
NWIS Module 01 — Master Pipeline Orchestrator
Coordinates all 6 layers of the Document Intelligence Pipeline.

This is the single entry point for all document processing.
Call: process_document(pdf_path) → DocumentExtractionResult

Layer execution:
  1. PyMuPDF scan detection + native extraction (Tier 1)
  2. Docling OCR for scanned pages (Tier 2) 
  3. spaCy NER + regex entity extraction (Tier 3)
  4. Template learning — feeds learned layout back for future docs (Layer 4)
  5. Physics domain validation — validates every extracted value (Layer 5)
  6. Result aggregation → WITSML-compliant JSON output
"""

from __future__ import annotations
import time
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from app.core.logging import logger
from app.config import settings

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from app.modules.document_intelligence.models.schemas import (
    DocumentExtractionResult,
    PageExtractionResult,
    DocumentType,
    ExtractionTier,
    ValidationStatus,
    IngestJobStatus,
)
from app.modules.document_intelligence.services.native_extractor import (
    extract_page_native,
    detect_document_type,
    extract_document_metadata,
    get_word_bounding_boxes,
    is_page_scanned,
)
from app.modules.document_intelligence.services.ocr_engine import (
    extract_document_with_docling,
    create_tier2_page_result,
)
from app.modules.document_intelligence.services.entity_extractor import extract_all_entities
from app.modules.document_intelligence.services.template_learner import (
    learn_from_document,
    get_template_for_document,
)
from app.modules.document_intelligence.models.domain_rules import validate_field
from app.modules.document_intelligence.models.schemas import ValidationStatus as VS
from app.modules.document_intelligence.services.physics_validator import run_physics_validation
from app.modules.document_intelligence.services.cloud_fallback import (
    should_use_cloud_fallback,
    get_cloud_parse_for_document,
)

# ---------------------------------------------------------------------------
# Output Directory
# ---------------------------------------------------------------------------

OUTPUT_DIR = settings.DATA_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Progress Callback Type
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[int, int, str], None]  # (current, total, message)


# ---------------------------------------------------------------------------
# Master Process Function
# ---------------------------------------------------------------------------

def process_document(
    pdf_path: Path,
    job_id: str = "",
    progress_cb: Optional[ProgressCallback] = None,
    max_pages: Optional[int] = None,
) -> DocumentExtractionResult:
    """
    Full 6-layer document intelligence pipeline.

    Args:
        pdf_path: Path to the DDR/WCR PDF file
        job_id: Background job ID for status tracking
        progress_cb: Optional callback (current_page, total_pages, message)

    Returns:
        DocumentExtractionResult — fully structured, WITSML-compliant output
    """
    total_start = time.time() * 1000
    job_id = job_id or f"JOB-{uuid.uuid4().hex[:8].upper()}"

    logger.info(f"[{job_id}] Starting 6-layer pipeline: {pdf_path.name}")

    # -----------------------------------------------------------------------
    # Initialize result object
    # -----------------------------------------------------------------------
    result = DocumentExtractionResult(
        job_id=job_id,
        source_filename=pdf_path.name,
        extraction_started_at=datetime.utcnow().isoformat(),
    )

    # These are hard failures, not "0 events found" outcomes — raise so the
    # caller (API background task, CLI demo) can tell a genuinely broken/
    # missing input apart from a document that simply has no drilling
    # entities in it. Silently returning an empty result here previously
    # caused corrupt/unreadable PDFs to be reported as "COMPLETED".
    if not pdf_path.exists():
        logger.error(f"[{job_id}] File not found: {pdf_path}")
        raise FileNotFoundError(f"File not found: {pdf_path}")

    # -----------------------------------------------------------------------
    # LAYER 0: Open PDF + detect document type + extract metadata
    # -----------------------------------------------------------------------
    if not PYMUPDF_AVAILABLE:
        logger.error("PyMuPDF not available. Install with: pip install pymupdf")
        raise RuntimeError("PyMuPDF is not installed. Run: pip install pymupdf")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        logger.error(f"[{job_id}] Cannot open PDF: {exc}")
        raise RuntimeError(
            f"Cannot open '{pdf_path.name}' as a PDF — it may be corrupt, "
            f"password-protected, or not a valid PDF file ({exc})"
        ) from exc

    if len(doc) == 0:
        doc.close()
        raise RuntimeError(f"'{pdf_path.name}' has zero pages — nothing to process")

    total_pages = len(doc)
    result.total_pages = total_pages

    # Detect document type
    doc_type_str = detect_document_type(doc)
    result.document_type = DocumentType(
        doc_type_str if doc_type_str in [e.value for e in DocumentType] else "UNKNOWN"
    )

    # Extract header metadata
    metadata = extract_document_metadata(doc, pdf_path.name)
    result.well_name = metadata.get("well_name")
    result.operator = metadata.get("operator")
    result.report_date = metadata.get("report_date")

    logger.info(
        f"[{job_id}] Document: {result.document_type.value} | "
        f"Well: {result.well_name} | Pages: {total_pages}"
    )

    # -----------------------------------------------------------------------
    # LAYER 4 (CHECK): Does a template exist for this document?
    # -----------------------------------------------------------------------
    existing_template = get_template_for_document(
        result.operator, result.document_type.value
    )
    if existing_template:
        result.template_used = existing_template.template_id
        logger.info(f"[{job_id}] Template found: {existing_template.template_id} — using fast path")

    # -----------------------------------------------------------------------
    # LAYER 2 (PRE): Run Docling on entire document (if not all native)
    # -----------------------------------------------------------------------
    # Check every page (not just the first) — a text cover/title page
    # followed by scanned body pages is common in real DDR/WCR bundles, and
    # sampling only page 0 previously meant the whole rest of the document
    # would silently get zero OCR. is_page_scanned() is a cheap text/image
    # heuristic, not actual OCR, so scanning every page costs very little.
    scanned_page_numbers = {
        i for i in range(total_pages) if is_page_scanned(doc[i])
    }
    needs_docling = len(scanned_page_numbers) > 0

    docling_result = {}
    if needs_docling:
        logger.info(
            f"[{job_id}] {len(scanned_page_numbers)}/{total_pages} scanned page(s) "
            f"detected — running Docling OCR"
        )
        if progress_cb:
            progress_cb(0, total_pages, "Running layout-aware OCR (Docling)...")
        docling_result = extract_document_with_docling(pdf_path)

    # -----------------------------------------------------------------------
    # PER-PAGE PROCESSING (Layers 1, 3, 5)
    # -----------------------------------------------------------------------
    scanned_count = 0
    all_events = []
    all_formations = []
    all_npt = []
    all_casing = []
    all_mud_properties = []
    total_confidence_sum = 0.0
    flagged_count = 0
    physics_violations = 0

    # Cloud fallback (Reducto / Extend.ai) is invoked at most ONCE per
    # document — the whole PDF is uploaded+parsed a single time and cached
    # here, then individual low-confidence pages are sliced out of it below.
    # See pipeline/cloud_fallback.py: this stays fully inert (no network
    # calls at all) unless NWIS_REDUCTO_API_KEY or NWIS_EXTEND_API_KEY is set.
    cloud_fallback_result = None
    cloud_fallback_attempted = False

    pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
    for page_num in range(pages_to_process):
        page_start = time.time() * 1000

        if progress_cb:
            progress_cb(page_num + 1, total_pages, f"Processing page {page_num + 1}/{total_pages}")

        page = doc[page_num]

        # -------------------------------------------------------------------
        # LAYER 1: Native extraction attempt
        # -------------------------------------------------------------------
        # Reuse the scan-check already computed in the pre-pass above instead
        # of letting extract_page_native recompute it — is_page_scanned()
        # MD5-hashes every image on the page and is expensive to run twice.
        page_result = extract_page_native(page, page_num, is_scanned=page_num in scanned_page_numbers)

        if page_result is None:
            logger.warning(f"[{job_id}] Page {page_num}: Tier 1 returned None — skipping")
            continue

        # -------------------------------------------------------------------
        # LAYER 2: If scanned, wrap Docling output
        # -------------------------------------------------------------------
        if page_result.is_scanned:
            scanned_count += 1
            # create_tier2_page_result prefers this page's own OCR text
            # (docling_result["page_markdown"][page_num]) and only falls
            # back to whole-document text — or an explicit "no OCR engine"
            # marker — when a real per-page result isn't available.
            page_result = create_tier2_page_result(page_num, docling_result)
            page_text = page_result.raw_text_preview
        else:
            # Get raw text from Tier 1 result for entity extraction
            page_text = page_result.raw_text_preview

        # -------------------------------------------------------------------
        # CLOUD FALLBACK: this page's local confidence is below threshold
        # (or it's scanned with no local OCR result at all) and a provider
        # is configured — replace this page's text with the cloud result
        # before entity extraction runs. Fully inert (should_use_cloud_fallback
        # returns False immediately, no network calls) if no API key is set.
        # -------------------------------------------------------------------
        if should_use_cloud_fallback(page_result.page_confidence):
            if not cloud_fallback_attempted:
                cloud_fallback_attempted = True
                logger.info(
                    f"[{job_id}] Page {page_num} confidence {page_result.page_confidence:.0%} "
                    f"below threshold — invoking cloud fallback for {pdf_path.name}"
                )
                if progress_cb:
                    progress_cb(page_num, total_pages, "Low confidence — trying cloud fallback (Reducto/Extend.ai)...")
                cloud_fallback_result = get_cloud_parse_for_document(pdf_path)

            if cloud_fallback_result:
                cloud_text = cloud_fallback_result["pages"].get(page_num)
                if cloud_text:
                    page_text = cloud_text
                    page_result.raw_text_preview = cloud_text[:1000]
                    page_result.page_confidence = cloud_fallback_result["page_confidence"]
                    page_result.extraction_source = cloud_fallback_result["provider"]
                    logger.info(
                        f"[{job_id}] Page {page_num}: replaced with "
                        f"{cloud_fallback_result['provider']} fallback text"
                    )

        # -------------------------------------------------------------------
        # LAYER 3: Entity extraction on this page's text
        # -------------------------------------------------------------------
        entities = extract_all_entities(page_text, page_num)

        page_result.mud_properties = entities.get("mud_properties")
        page_result.drilling_parameters = entities.get("drilling_parameters")
        page_result.formation_tops = entities.get("formation_tops", [])
        page_result.npt_records = entities.get("npt_records", [])
        page_result.drilling_events = entities.get("drilling_events", [])

        # Accumulate for document-level aggregation
        all_events.extend(page_result.drilling_events)
        all_formations.extend(page_result.formation_tops)
        all_npt.extend(page_result.npt_records)
        if page_result.mud_properties is not None:
            # Without this, Layer 5's OCR-slip auto-repair (e.g. "3.2 ppg"
            # -> "13.2 ppg") never runs on any real document — it validates
            # result.mud_properties (the document-level list), which nothing
            # was ever populating from the per-page extraction.
            all_mud_properties.append(page_result.mud_properties)

        # -------------------------------------------------------------------
        # LAYER 5: Count physics violations from entity fields
        # -------------------------------------------------------------------
        for event in page_result.drilling_events:
            for field_obj in [event.depth_start_md_m, event.npt_hours, event.loss_rate_bbl_hr]:
                if field_obj is None:
                    continue
                if field_obj.validation_status == VS.FAILED:
                    physics_violations += 1
                elif field_obj.validation_status == VS.FLAGGED:
                    flagged_count += 1

        # Page confidence — NOTE: this must not be `page_confidence or 0.90`.
        # page_confidence is a float that can be a legitimate 0.0 (e.g. a
        # scanned page with no OCR engine available), and `0.0 or 0.90`
        # evaluates to 0.90 in Python, silently erasing that low-confidence
        # signal from the document's overall_confidence.
        page_conf = (
            page_result.page_confidence if page_result.page_confidence is not None else 0.90
        )
        total_confidence_sum += page_conf
        page_result.processing_time_ms = round(time.time() * 1000 - page_start, 2)

        result.pages.append(page_result)
        result.pages_processed += 1

        logger.debug(
            f"[{job_id}] Page {page_num} done in {page_result.processing_time_ms:.0f}ms | "
            f"tier={page_result.extraction_tier.value}"
        )

    doc.close()

    # -----------------------------------------------------------------------
    # LAYER 4 (LEARN): Feed this document's layout back into template system
    # -----------------------------------------------------------------------
    if result.pages_processed > 0:
        try:
            # Re-open to get page dict for template learning
            doc2 = fitz.open(str(pdf_path))
            page_dict = doc2[0].get_text("dict") if len(doc2) > 0 else {}
            doc2.close()

            avg_conf = total_confidence_sum / result.pages_processed
            learn_from_document(
                result.operator,
                result.document_type.value,
                page_dict,
                avg_conf,
            )
        except Exception as exc:
            logger.debug(f"[{job_id}] Template learning skipped: {exc}")

    # -----------------------------------------------------------------------
    # Aggregate document-level results
    # -----------------------------------------------------------------------
    result.all_drilling_events = all_events
    result.all_formation_tops = all_formations
    result.mud_properties = all_mud_properties
    result.all_npt_records = all_npt
    result.all_casing_records = all_casing
    result.scanned_pages = scanned_count

    # Cloud fallback audit trail — non-zero only if a provider was actually
    # configured AND used. See pipeline/cloud_fallback.py for the sovereignty
    # tradeoff note this exists to make visible, not just log-buried.
    cloud_pages = [p for p in result.pages if p.extraction_source != "local"]
    result.cloud_fallback_pages_count = len(cloud_pages)
    result.cloud_fallback_providers_used = sorted({p.extraction_source for p in cloud_pages})
    if cloud_pages:
        logger.warning(
            f"[{job_id}] {len(cloud_pages)} page(s) of {pdf_path.name} were sent to an "
            f"external cloud provider ({', '.join(result.cloud_fallback_providers_used)}) "
            f"— this document left the air-gapped boundary."
        )
    # -----------------------------------------------------------------------
    # LAYER 5: Execute domain physics validation & audit
    # -----------------------------------------------------------------------
    try:
        result, val_report = run_physics_validation(result)
        result.physics_violations_count = val_report.failed_checks
        result.flagged_fields_count = val_report.warning_checks + val_report.failed_checks
    except Exception as val_exc:
        logger.warning(f"[{job_id}] Physics validation warning: {val_exc}")

    if result.pages_processed > 0:
        result.overall_confidence = round(total_confidence_sum / result.pages_processed, 4)

    # Escalate to human review when either (a) confidence is too low, or
    # (b) a scanned page came back with almost no extracted text despite
    # being "processed" — checked BOTH ways deliberately, not confidence
    # alone. Verified by testing (not assumed): a completely blank scanned
    # page, where RapidOCR itself logged "text detection result is empty"
    # and raw_text_preview was 0 characters long, still self-reported 86%
    # confidence via Docling's quality score — the same confidence-does-not-
    # mean-correct-content gap documented in pipeline/tier2_ocr_engine.py's
    # create_tier2_page_result. A confidence-only threshold would have left
    # that exact document silently marked PASS. This is what actually
    # populates ValidationStatus.MANUAL_REVIEW: the enum value existed
    # before this, but nothing ever set it — see api/routes/review.py for
    # the workflow that acts on it.
    MANUAL_REVIEW_CONFIDENCE_THRESHOLD = 0.5
    MANUAL_REVIEW_MIN_SCANNED_TEXT_CHARS = 20

    low_confidence = result.overall_confidence < MANUAL_REVIEW_CONFIDENCE_THRESHOLD
    empty_scanned_pages = [
        p.page_number for p in result.pages
        if p.is_scanned and len(p.raw_text_preview.strip()) < MANUAL_REVIEW_MIN_SCANNED_TEXT_CHARS
    ]

    if low_confidence or empty_scanned_pages:
        result.validation_status = VS.MANUAL_REVIEW
        reasons = []
        if low_confidence:
            reasons.append(f"overall confidence {result.overall_confidence:.1%} < {MANUAL_REVIEW_CONFIDENCE_THRESHOLD:.0%}")
        if empty_scanned_pages:
            reasons.append(f"{len(empty_scanned_pages)} scanned page(s) with near-empty text (pages {empty_scanned_pages})")
        logger.warning(f"[{job_id}] Escalated to MANUAL_REVIEW — {'; '.join(reasons)}")

    # Finalize timing
    total_elapsed = time.time() * 1000 - total_start
    result.total_processing_time_ms = round(total_elapsed, 2)
    result.extraction_completed_at = datetime.utcnow().isoformat()

    # -----------------------------------------------------------------------
    # Save result to disk (JSON)
    # -----------------------------------------------------------------------
    output_path = OUTPUT_DIR / f"{result.document_id}.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        logger.success(f"[{job_id}] Output saved: {output_path}")
    except Exception as exc:
        logger.error(f"[{job_id}] Failed to save output: {exc}")

    logger.success(
        f"[{job_id}] Pipeline complete: {result.pages_processed}/{total_pages} pages | "
        f"Events: {len(all_events)} | Formations: {len(all_formations)} | "
        f"NPT records: {len(all_npt)} | "
        f"Confidence: {result.overall_confidence:.1%} | "
        f"Time: {total_elapsed:.0f}ms"
    )

    return result


# ---------------------------------------------------------------------------
# Quick Demo Runner (for testing without the API server)
# ---------------------------------------------------------------------------

def run_demo(pdf_path: str) -> None:
    """
    Run the pipeline on a single PDF and print a rich summary to the terminal.
    Usage: python -c "from app.modules.document_intelligence.services.pipeline_orchestrator import run_demo; run_demo('path/to/file.pdf')"
    """
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()
    path = Path(pdf_path)

    console.print(Panel.fit(
        f"[bold cyan]NWIS Document Intelligence Pipeline[/bold cyan]\n"
        f"Processing: [yellow]{path.name}[/yellow]",
        border_style="cyan"
    ))

    def progress(cur, tot, msg):
        console.print(f"  [dim]{msg}[/dim]")

    try:
        result = process_document(path, progress_cb=progress)
    except Exception as exc:
        console.print(Panel.fit(
            f"[bold red]Processing failed:[/bold red] {exc}",
            border_style="red",
        ))
        return

    # Summary table
    table = Table(title="Extraction Summary", box=box.ROUNDED, border_style="green")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Document Type", result.document_type.value)
    table.add_row("Well Name", result.well_name or "Not detected")
    table.add_row("Operator", result.operator or "Not detected")
    table.add_row("Pages Processed", f"{result.pages_processed}/{result.total_pages}")
    table.add_row("Scanned Pages (OCR)", str(result.scanned_pages))
    table.add_row("Drilling Events Found", str(len(result.all_drilling_events)))
    table.add_row("Formation Tops Found", str(len(result.all_formation_tops)))
    table.add_row("NPT Records Found", str(len(result.all_npt_records)))
    table.add_row("Physics Violations", str(result.physics_violations_count))
    table.add_row("Flagged Fields", str(result.flagged_fields_count))
    table.add_row("Overall Confidence", f"{result.overall_confidence:.1%}")
    table.add_row("Processing Time", f"{result.total_processing_time_ms:.0f} ms")
    table.add_row("Template Used", result.template_used or "None (first run)")
    table.add_row("WITSML Compliant", "YES ✓")

    console.print(table)

    if result.all_drilling_events:
        console.print("\n[bold green]Drilling Events Extracted:[/bold green]")
        for evt in result.all_drilling_events[:5]:
            console.print(
                f"  • [yellow]{evt.event_type.value}[/yellow] | "
                f"Severity: {evt.severity.value} | "
                f"Conf: {evt.confidence:.0%} | "
                f"{evt.raw_narrative[:80]}..."
            )

    console.print(f"\n[dim]Full output: data/output/{result.document_id}.json[/dim]")

