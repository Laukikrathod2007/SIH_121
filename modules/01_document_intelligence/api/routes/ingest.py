"""
NWIS API Route: Document Ingestion
POST /api/v1/ingest — Upload a DDR/WCR PDF for background processing
"""

from __future__ import annotations
import asyncio
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from loguru import logger

from app.modules.document_intelligence.models.schemas import IngestJobResponse, IngestJobStatus

router = APIRouter()

# Injected by server.py — a SQLiteJobStore instance (see api/job_store.py).
# Persists across restarts, unlike a plain in-memory dict.
JOB_STORE = None
UPLOAD_DIR: Path = Path("data/uploads")

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE_MB = 100

_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9._-]")


def _sanitize_filename(raw_name: str, required_suffix: str) -> str:
    """Reduce a client-supplied filename to a safe basename before it is
    ever joined into a filesystem path. `raw_name` is fully attacker-
    controlled (it's the multipart Content-Disposition filename) -- a prior
    version of this function concatenated it into a write path unchanged
    (despite being named "safe_name"), which let a crafted filename
    containing '..' segments write outside UPLOAD_DIR.

    Strips directory components from BOTH '/' and '\\' (Path(...).name
    alone only understands the current OS's separator -- on a POSIX
    deployment a Windows-style '..\\..\\x.pdf' payload would otherwise
    pass through untouched), then allowlist-filters to a conservative
    charset, then re-asserts the already-validated extension."""
    name = raw_name.replace("\\", "/")
    name = Path(name).name  # drops any directory parts, including '..'
    name = _UNSAFE_CHARS_RE.sub("_", name).strip("._- ")
    if not name:
        name = "upload"
    if not name.lower().endswith(required_suffix):
        name = f"{name}{required_suffix}"
    return name[:120]  # bound filesystem-unfriendly length


@router.post("/ingest", response_model=IngestJobResponse, status_code=202)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="DDR or WCR PDF file"),
):
    """
    Upload a Daily Drilling Report (DDR) or Well Completion Report (WCR) PDF.

    The document is queued for background processing through the 6-layer pipeline:
    1. PyMuPDF native extraction (Tier 1)
    2. Docling OCR for scanned pages (Tier 2)
    3. Domain entity extraction: mud properties, drilling events, NPT (Tier 3)
    4. Template coordinate learning (Layer 4)
    5. Physics domain validation — OISD-157 + IADC standards (Layer 5)
    6. WITSML-compliant JSON output (Layer 6)

    Poll GET /api/v1/jobs/{job_id} for progress.
    """
    # --- Validate file ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Only PDF files are accepted."
        )

    # --- Read and size-check ---
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f} MB. Maximum is {MAX_FILE_SIZE_MB} MB."
        )

    # --- Save to upload dir ---
    job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"
    safe_name = f"{job_id}_{_sanitize_filename(file.filename, suffix)}"
    upload_path = (UPLOAD_DIR / safe_name).resolve()

    upload_root = UPLOAD_DIR.resolve()
    if upload_root != upload_path and upload_root not in upload_path.parents:
        # Defensive — should be unreachable now that safe_name is sanitized,
        # but never write outside the upload root even if that assumption
        # is ever violated (mirrors the same check in results.py's
        # get_document_file()).
        logger.error(f"Refusing to write file outside UPLOAD_DIR: {upload_path}")
        raise HTTPException(status_code=400, detail="Invalid filename.")

    with open(upload_path, "wb") as f:
        f.write(content)

    logger.info(f"[{job_id}] File saved: {upload_path} ({size_mb:.2f} MB)")

    # --- Initialize job record ---
    JOB_STORE.create(job_id, {
        "job_id": job_id,
        "filename": file.filename,
        "upload_path": str(upload_path),
        "status": IngestJobStatus.QUEUED,
        "progress_percent": 0,
        "current_page": 0,
        "total_pages": 0,
        "message": "Document queued for processing",
        "document_id": None,
        "error": None,
        "submitted_at": datetime.utcnow().isoformat(),
    })

    # --- Queue background task ---
    background_tasks.add_task(_run_pipeline_background, job_id, upload_path)

    return IngestJobResponse(
        job_id=job_id,
        filename=file.filename,
        status=IngestJobStatus.QUEUED,
        message=f"Document queued. Poll /api/v1/jobs/{job_id} for progress.",
    )


async def _run_pipeline_background(job_id: str, upload_path: Path):
    """
    Background task: runs the full 6-layer pipeline asynchronously.
    Updates JOB_STORE with progress so the polling endpoint can report live status.
    """
    from app.modules.document_intelligence.pipeline.orchestrator import process_document

    JOB_STORE.update(job_id, status=IngestJobStatus.PROCESSING, message="Pipeline started")

    def progress_callback(current: int, total: int, message: str):
        JOB_STORE.update(
            job_id,
            current_page=current,
            total_pages=total,
            progress_percent=int((current / max(total, 1)) * 100),
            message=message,
        )

    try:
        # Run CPU-intensive pipeline in thread pool (don't block event loop)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: process_document(upload_path, job_id=job_id, progress_cb=progress_callback),
        )

        # A malformed/corrupt/encrypted PDF, or one that yields zero readable
        # pages, is a failure — not a success with an empty result. The
        # orchestrator raises for the hard failure cases (missing file,
        # unopenable PDF); this is a defensive backstop for anything that
        # slips through as a "successful" zero-page result.
        if result.total_pages == 0 or result.pages_processed == 0:
            raise RuntimeError(
                "No readable pages were extracted from this document. "
                "It may be corrupt, empty, or password-protected."
            )

        JOB_STORE.update(
            job_id,
            status=IngestJobStatus.COMPLETED,
            progress_percent=100,
            document_id=result.document_id,
            message=(
                f"Completed: {result.pages_processed} pages | "
                f"{len(result.all_drilling_events)} events | "
                f"Confidence: {result.overall_confidence:.1%}"
            ),
        )
        logger.success(f"[{job_id}] Background processing complete")

    except Exception as exc:
        # Log the real exception server-side only. The client-visible
        # error/message fields must never contain raw exception text (class
        # name, internal file paths, stack frames) — every other module's
        # error path already follows this rule (Backend/app/core/errors.py,
        # modules/02_nwis_backend/server.py's route handlers); this was the
        # one place that didn't.
        logger.exception(f"[{job_id}] Pipeline failed: {exc}")
        JOB_STORE.update(
            job_id,
            status=IngestJobStatus.FAILED,
            error="Document processing failed. See server logs for details.",
            message=(
                "Processing failed. This document could not be processed — "
                "it may be corrupt, password-protected, or in an unsupported format."
            ),
        )
