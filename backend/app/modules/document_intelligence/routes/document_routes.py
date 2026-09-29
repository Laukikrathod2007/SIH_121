"""
Document Intelligence API Routes.
Exposes endpoints for PDF ingestion, status polling, WITSML results, and coordinate templates.
"""

from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.modules.document_intelligence.models.schemas import (
    IngestJobResponse,
    JobStatusResponse,
)
from app.modules.document_intelligence.controllers.document_controller import document_controller

router = APIRouter(prefix="/documents", tags=["Document Intelligence"])


@router.post("/ingest", response_model=IngestJobResponse, status_code=202)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="DDR or WCR PDF file"),
):
    """
    Upload a Daily Drilling Report (DDR) or Well Completion Report (WCR) PDF.
    Queues the document for background processing through the 6-layer pipeline.
    """
    return await document_controller.ingest_document(file, background_tasks)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll progress and outcome for a document ingestion job."""
    return document_controller.get_job_status(job_id)


@router.get("/jobs")
async def list_jobs(limit: int = Query(default=50, ge=1, le=500)):
    """List recent document ingestion jobs."""
    return document_controller.list_jobs(limit=limit)


@router.get("/results")
async def list_results():
    """List every processed document with summary counts and review status."""
    return document_controller.list_results()


@router.get("/results/{doc_id}")
async def get_full_result(doc_id: str):
    """Retrieve the full WITSML-compliant extraction result."""
    return document_controller.get_full_result(doc_id)


@router.get("/results/{doc_id}/events")
async def get_drilling_events(doc_id: str):
    """Retrieve drilling hazard events extracted from document."""
    return document_controller.get_drilling_events(doc_id)


@router.get("/results/{doc_id}/formations")
async def get_formation_tops(doc_id: str):
    """Retrieve formation tops extracted from document."""
    return document_controller.get_formation_tops(doc_id)


@router.get("/results/{doc_id}/npt")
async def get_npt_records(doc_id: str):
    """Retrieve IADC NPT records extracted from document."""
    return document_controller.get_npt_records(doc_id)


@router.get("/templates")
async def list_templates():
    """List learned coordinate templates (Layer 4)."""
    return document_controller.list_templates()


@router.get("/results/{doc_id}/benchmark")
async def get_quality_report(doc_id: str):
    """Extraction quality metrics for one document."""
    return document_controller.get_quality_report(doc_id)


@router.get("/{doc_id}/file")
async def get_document_file(doc_id: str):
    """Stream the original uploaded PDF (powers the PDF evidence viewer; open with #page=N)."""
    path = document_controller.get_document_file_path(doc_id)
    return FileResponse(
        path=path,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{path.name}"'},
    )


# --- Human curation / review workflow ---------------------------------------

class ReviewDecision(BaseModel):
    reviewer: str
    decision: str  # "approved" | "rejected"
    notes: Optional[str] = None


class FieldAnnotation(BaseModel):
    reviewer: str
    field_path: str
    note: str


@router.get("/review/queue")
async def review_queue():
    """Documents whose validation status needs a human (worst first)."""
    return document_controller.review_queue()


@router.post("/review/{doc_id}/decision")
async def review_decision(doc_id: str, body: ReviewDecision):
    """Approve (-> PASS) or reject (-> FAILED, events withdrawn on next load) a document."""
    return document_controller.submit_review_decision(doc_id, body.reviewer, body.decision, body.notes)


@router.post("/review/{doc_id}/annotate")
async def review_annotate(doc_id: str, body: FieldAnnotation):
    """Attach a field-level correction note (never silently rewrites the value)."""
    return document_controller.annotate_field(doc_id, body.reviewer, body.field_path, body.note)
