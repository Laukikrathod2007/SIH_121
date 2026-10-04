"""
Evidence/PDF delivery -- replaces the standalone evidence-server/ Node
process (retired from the startup path, not deleted from disk). This is
genuinely NEW code (not harvested), since the task is to retire the Node
process, not wrap it -- but it reimplements the exact same safety
behavior evidence-server/index.js already had after its own Pass 2
hardening: substring blocklist + path-resolution containment check
(defense in depth), generic 404 (no directory-listing leak), a /health
check.

Mounted at /api/evidence/* (vs. the Node version's bare /evidence) to
fit the unified app's namespace scheme.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import EVIDENCE_PDF_DIR

router = APIRouter(prefix="/api/evidence", tags=["Evidence"])

_PDF_DIR_RESOLVED = EVIDENCE_PDF_DIR.resolve()


@router.get("/health")
async def evidence_health():
    try:
        count = sum(1 for _ in EVIDENCE_PDF_DIR.iterdir())
        return {"status": "healthy", "pdf_dir_reachable": True, "pdf_count": count}
    except OSError:
        return {"status": "degraded", "pdf_dir_reachable": False, "pdf_count": None}


@router.get("")
async def get_evidence(name: str = Query(..., description="PDF filename, e.g. DDR_WELL-NHK-001_1221m.pdf")):
    if not name or ".." in name or "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid document name")

    resolved = (EVIDENCE_PDF_DIR / name).resolve()
    # Defense in depth on top of the substring blocklist above -- verify
    # the resolved path still falls strictly inside EVIDENCE_PDF_DIR.
    if resolved != _PDF_DIR_RESOLVED and _PDF_DIR_RESOLVED not in resolved.parents:
        raise HTTPException(status_code=400, detail="Invalid document name")

    if not resolved.is_file():
        # Generic message -- no directory-listing leak (the pre-Pass-2
        # Node version's bug; already fixed there too, not reintroduced here).
        raise HTTPException(status_code=404, detail="Document not found.")

    return FileResponse(
        resolved,
        media_type="application/pdf",
        filename=name,
        content_disposition_type="inline",
    )
