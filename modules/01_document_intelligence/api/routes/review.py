"""
NWIS API Route: Human Curation / Review Workflow

Closes a real gap found while researching OpenEI's Geothermal Data Repository
(gdr.openei.org — the actual source of this project's one real test document,
the Utah FORGE DDR): GDR states its metadata "undergoes curation review for
relevance, appropriateness, and completeness before publication." This
project already had the schema hook for that — ValidationStatus.MANUAL_REVIEW
— but nothing ever set it, and there was no endpoint for a human to act on a
flagged document. Both gaps are closed here.

Endpoints:
  GET  /api/v1/review/queue           → Documents awaiting human review
  GET  /api/v1/review/{doc_id}        → Full detail for one document under review
  POST /api/v1/review/{doc_id}/decision  → Approve or reject a document
  POST /api/v1/review/{doc_id}/annotate  → Attach a field-level correction note

Design note: /annotate stores a human-readable note, not an automatic
in-place patch of the extracted value — see models/schemas.py's
field_annotations docstring for why a generic deep-path JSON patcher was
deliberately not built (the risk of silently corrupting data on a slightly
wrong path is worse than requiring a human to write "the real value is X").
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from models.schemas import ValidationStatus

router = APIRouter()

# Injected by server.py, same pattern as results.py
OUTPUT_DIR: Path = Path("data/output")

# Everything except a clean PASS is something a human might want to look at
NEEDS_REVIEW_STATUSES = {
    ValidationStatus.FLAGGED.value,
    ValidationStatus.FAILED.value,
    ValidationStatus.MANUAL_REVIEW.value,
}


def _result_path(doc_id: str) -> Path:
    path = OUTPUT_DIR / f"{doc_id}.json"
    if not path.exists():
        matches = list(OUTPUT_DIR.glob(f"*{doc_id}*.json"))
        if not matches:
            raise HTTPException(404, f"Result for document '{doc_id}' not found")
        path = matches[0]
    return path


def _load(doc_id: str) -> dict:
    with open(_result_path(doc_id), "r", encoding="utf-8") as f:
        return json.load(f)


def _save(doc_id: str, data: dict) -> None:
    with open(_result_path(doc_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


@router.get("/review/queue")
async def review_queue():
    """
    Every document not yet reviewed whose validation_status isn't a clean
    PASS — sorted worst-first (MANUAL_REVIEW, then FAILED, then FLAGGED) so
    the documents most likely to contain wrong data surface at the top.
    """
    if not OUTPUT_DIR.exists():
        return {"total": 0, "queue": []}

    severity_order = {
        ValidationStatus.MANUAL_REVIEW.value: 0,
        ValidationStatus.FAILED.value: 1,
        ValidationStatus.FLAGGED.value: 2,
    }

    queue = []
    for path in OUTPUT_DIR.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            logger.warning(f"Skipping unreadable result file {path}: {exc}")
            continue

        status = data.get("validation_status")
        if status not in NEEDS_REVIEW_STATUSES or data.get("reviewed"):
            continue

        queue.append({
            "document_id": data.get("document_id"),
            "source_filename": data.get("source_filename"),
            "well_name": data.get("well_name"),
            "operator": data.get("operator"),
            "validation_status": status,
            "overall_confidence": data.get("overall_confidence"),
            "physics_violations_count": data.get("physics_violations_count"),
            "cloud_fallback_pages_count": data.get("cloud_fallback_pages_count"),
            "extraction_completed_at": data.get("extraction_completed_at"),
        })

    queue.sort(key=lambda d: severity_order.get(d["validation_status"], 99))
    return {"total": len(queue), "queue": queue}


@router.get("/review/{doc_id}")
async def review_detail(doc_id: str):
    """Full extraction result for one document, for the reviewer to inspect
    before deciding — identical payload to GET /results/{doc_id}, exposed
    under /review too so a reviewer UI doesn't need two different base paths."""
    return _load(doc_id)


class ReviewDecision(BaseModel):
    reviewer: str
    decision: str  # "approved" | "rejected"
    notes: Optional[str] = None


@router.post("/review/{doc_id}/decision")
async def submit_review_decision(doc_id: str, body: ReviewDecision):
    """
    A human confirms a flagged/low-confidence/manual-review document is
    either trustworthy as-is (approved -> validation_status becomes PASS)
    or should not be relied on (rejected -> validation_status becomes
    FAILED, e.g. "re-scan this document" or "re-key it by hand").
    """
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be 'approved' or 'rejected'")

    data = _load(doc_id)
    data["reviewed"] = True
    data["reviewed_by"] = body.reviewer
    data["reviewed_at"] = datetime.utcnow().isoformat()
    data["review_decision"] = body.decision
    data["review_notes"] = body.notes
    data["validation_status"] = (
        ValidationStatus.PASS.value if body.decision == "approved" else ValidationStatus.FAILED.value
    )
    _save(doc_id, data)

    logger.info(f"Review decision on {doc_id}: {body.decision} by {body.reviewer}")
    return {
        "document_id": doc_id,
        "reviewed": True,
        "decision": body.decision,
        "validation_status": data["validation_status"],
    }


class FieldAnnotation(BaseModel):
    reviewer: str
    field_path: str  # e.g. "mud_properties[0].mud_weight_ppg" — descriptive, not machine-applied
    note: str


@router.post("/review/{doc_id}/annotate")
async def annotate_field(doc_id: str, body: FieldAnnotation):
    """
    Attach a human correction note to a specific field without automatically
    rewriting the extracted value in place — see module docstring for why.
    Multiple annotations accumulate; nothing is ever silently overwritten.
    """
    data = _load(doc_id)
    annotations = data.get("field_annotations") or []
    annotations.append({
        "field_path": body.field_path,
        "note": body.note,
        "annotated_by": body.reviewer,
        "annotated_at": datetime.utcnow().isoformat(),
    })
    data["field_annotations"] = annotations
    _save(doc_id, data)

    logger.info(f"Field annotation on {doc_id} ({body.field_path}) by {body.reviewer}")
    return {"document_id": doc_id, "total_annotations": len(annotations)}
