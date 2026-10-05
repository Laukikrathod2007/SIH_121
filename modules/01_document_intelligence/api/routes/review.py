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

from app.modules.document_intelligence.models.schemas import ValidationStatus
from app.modules.document_intelligence.api.routes.results import _validate_doc_id

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
    """Exact match only -- see results.py's _validate_doc_id/_load_result
    docstring: the glob-based fuzzy fallback this used to fall back to
    accepted glob metacharacters straight from the client (doc_id="*"
    could match and return another document's file), so it was removed
    rather than sanitized."""
    _validate_doc_id(doc_id)
    path = OUTPUT_DIR / f"{doc_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Result for document '{doc_id}' not found")
    return path


def _load(doc_id: str) -> dict:
    with open(_result_path(doc_id), "r", encoding="utf-8") as f:
        return json.load(f)


def _save(doc_id: str, data: dict) -> None:
    with open(_result_path(doc_id), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


@router.get("/review/queue")
def review_queue():
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
def submit_review_decision(doc_id: str, body: ReviewDecision):
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

    # Pass 4/5: write-through the review decision, then (only on approval)
    # hand off this document's drilling events into the canonical
    # drilling_events table — see db/service.py's handoff_events docstring
    # for the exact, conservative eligibility rule. Best-effort: a database
    # outage here must not fail a review decision that's already saved.
    # The resulting sync status (closed enum, never a raw exception — see
    # db/service.py's SyncStatus) is persisted back onto this same file.
    handoff_result = {}
    sync_status = data.get("postgres_sync_status", "not_configured")
    try:
        from app.modules.document_intelligence.db import service as db_sync
        review_sync_result = db_sync.sync_review(doc_id, data)
        sync_status = review_sync_result.get("status", sync_status)
        handoff_result = db_sync.handoff_events(data)
        if handoff_result.get("migrated") or handoff_result.get("skipped"):
            logger.info(
                f"Event handoff for {doc_id}: {handoff_result.get('migrated', 0)} migrated, "
                f"{handoff_result.get('skipped', 0)} skipped"
            )
    except Exception as exc:
        sync_status = "error"
        logger.warning(f"Postgres review/handoff write-through for {doc_id} raised unexpectedly (non-fatal): {exc}")

    if sync_status != "not_configured":
        data["postgres_sync_status"] = sync_status
        _save(doc_id, data)

    return {
        "document_id": doc_id,
        "reviewed": True,
        "decision": body.decision,
        "validation_status": data["validation_status"],
        "events_migrated_to_knowledge_base": handoff_result.get("migrated", 0),
        "events_skipped": handoff_result.get("skipped", 0),
        "postgres_sync_status": sync_status,
    }


class FieldAnnotation(BaseModel):
    reviewer: str
    field_path: str  # e.g. "mud_properties[0].mud_weight_ppg" — descriptive, not machine-applied
    note: str


@router.post("/review/{doc_id}/annotate")
def annotate_field(doc_id: str, body: FieldAnnotation):
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

    sync_status = data.get("postgres_sync_status", "not_configured")
    try:
        from app.modules.document_intelligence.db import service as db_sync
        annotate_sync_result = db_sync.sync_review(doc_id, data)
        sync_status = annotate_sync_result.get("status", sync_status)
    except Exception as exc:
        sync_status = "error"
        logger.warning(f"Postgres annotation write-through for {doc_id} raised unexpectedly (non-fatal): {exc}")

    if sync_status != "not_configured":
        data["postgres_sync_status"] = sync_status
        _save(doc_id, data)

    return {"document_id": doc_id, "total_annotations": len(annotations), "postgres_sync_status": sync_status}


@router.post("/review/{doc_id}/resync")
def resync_document(doc_id: str):
    """
    Manually retry the Postgres write-through for one document — safe to
    call any number of times. Re-reads the existing JSON result (already
    on disk; the extracted work is never lost regardless of database
    state) and re-runs the same idempotent sync_document()/handoff_events()
    calls the original ingestion/review already made. UPSERT semantics
    throughout (see db/service.py and the Pass 4 tests that established
    this idempotency) mean re-syncing a document that already synced
    successfully is a safe no-op, not a duplicate write.

    Use this after a transient database outage (postgres_sync_status
    "unavailable") to bring a document's canonical-DB copy up to date
    without re-ingesting or re-reviewing it.
    """
    data = _load(doc_id)

    from app.modules.document_intelligence.db import service as db_sync
    sync_result = db_sync.sync_document(data)
    sync_status = sync_result.get("status", "error")

    handoff_result = {}
    if data.get("reviewed"):
        db_sync.sync_review(doc_id, data)
        handoff_result = db_sync.handoff_events(data)

    data["postgres_sync_status"] = sync_status
    _save(doc_id, data)

    return {
        "document_id": doc_id,
        "postgres_sync_status": sync_status,
        "events_migrated_to_knowledge_base": handoff_result.get("migrated", 0),
        "events_skipped": handoff_result.get("skipped", 0),
    }
