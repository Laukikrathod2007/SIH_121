"""
Document Intelligence API Routes.
Exposes endpoints for PDF ingestion, status polling, WITSML results, and coordinate templates.
"""

from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Query

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
