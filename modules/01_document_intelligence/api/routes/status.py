"""
NWIS API Route: Job Status
GET /api/v1/jobs/{job_id} — Poll pipeline progress
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.modules.document_intelligence.models.schemas import JobStatusResponse, IngestJobStatus

router = APIRouter()

# Injected by server.py — a SQLiteJobStore instance (see api/job_store.py).
JOB_STORE = None


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Poll the status of a document ingestion job.

    Status lifecycle:
    QUEUED → PROCESSING → COMPLETED (or FAILED)

    When status is COMPLETED, the response includes document_id.
    Use document_id to fetch the full extraction results.
    """
    job = JOB_STORE.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may not exist, or its record may have been pruned."
        )

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress_percent=job.get("progress_percent", 0),
        current_page=job.get("current_page", 0),
        total_pages=job.get("total_pages", 0),
        message=job.get("message", ""),
        document_id=job.get("document_id"),
        error=job.get("error"),
    )


@router.get("/jobs", tags=["Job Status"])
async def list_jobs():
    """List all jobs in the current session."""
    return {
        "total_jobs": len(JOB_STORE),
        "jobs": [
            {
                "job_id": j["job_id"],
                "filename": j.get("filename"),
                "status": j["status"],
                "progress_percent": j.get("progress_percent", 0),
                "document_id": j.get("document_id"),
                "submitted_at": j.get("submitted_at"),
            }
            for j in JOB_STORE.values()
        ],
    }
