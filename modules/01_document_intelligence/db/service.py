"""
Service layer for module 01's PostgreSQL write-through (Pass 4). Business
logic — well-name resolution, hazard-type mapping, ExtractedField
unwrapping — lives here, not in the repository's SQL or in the
orchestrator/review routes that call this.

Entry points:
  sync_document(result_dict)        -- called after orchestrator.py saves
                                        its JSON (best-effort, never raises)
  sync_review(doc_id, result_dict)  -- called after review.py's decision/
                                        annotate endpoints save their JSON
  handoff_events(result_dict)       -- the document -> canonical
                                        drilling_events handoff described
                                        below

Every function here is a no-op (returns a result that says so) when the
database isn't configured — callers never need an `if db_is_configured()`
guard of their own; this module absorbs that check so a DB-less dev
environment behaves exactly as before Pass 4.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from loguru import logger

from app.modules.nwis.db.connection import (
    is_configured as db_is_configured,
    get_connection,
)
from app.modules.document_intelligence.db.repositories import (
    DocumentRepository, EventHandoffRepository,
)

# Pass 5: closed, display-ready sync-status categories. The raw exception
# text (`f"{type(exc).__name__}: {exc}"`, the previous value of the
# "reason" field below) stayed internal-log-only even before this change
# — nothing in Pass 4 or Pass 5 ever routed it into a user-facing field —
# but the field itself was still an open-ended string, which is the wrong
# shape for a UI to render safely (a future caller could trivially start
# displaying "reason" verbatim without reintroducing this same leak). This
# enum is what a caller should surface; the full exception detail stays in
# the server log line right next to where it's raised, never copied here.
SyncStatus = Literal["synced", "not_configured", "unavailable", "error"]


def _is_connectivity_error(exc: Exception) -> bool:
    """True for "the database couldn't be reached" (connection refused,
    timeout, pool exhaustion — psycopg.OperationalError and its
    subclasses), False for everything else (a real constraint violation,
    a programming error, a malformed query) — the former is
    "unavailable" (retry later, not actionable by a human right now), the
    latter is "error" (something is actually wrong and retrying the exact
    same write will fail the exact same way)."""
    import psycopg
    return isinstance(exc, psycopg.OperationalError)

# M01's EventType values that have no equivalent in the canonical
# hazard_type table (database/schema.sql) today. Listed explicitly rather
# than inferred, so a future hazard_type addition is a one-line change
# here, not a silent new gap. Events with one of these types are not
# migrated into drilling_events — counted and logged, never dropped
# silently (task requirement: "document precisely rather than pretending
# it is database-backed").
UNMAPPED_EVENT_TYPES = {"GAS_INFLUX", "LOST_CIRCULATION", "EQUIPMENT_FAILURE", "DEVIATION_CONTROL", "NPT_OPERATIONAL", "UNKNOWN"}

# M01's EventType and M02's HazardType otherwise share identical string
# values (MUD_LOSS, STUCK_PIPE, KICK, WELLBORE_INSTABILITY,
# OVERPRESSURE_ZONE, FISHING_OPERATION) -- confirmed against both enums in
# models/schemas.py, not assumed -- so no translation table is needed for
# the mapped subset, only a membership check against UNMAPPED_EVENT_TYPES.

_WELL_NAME_NORMALIZE = re.compile(r"[_\s]+")

# modules/01_document_intelligence/pipeline/tier1_native_extractor.py's
# filename-fallback well-name regex has a known, confirmed-live bug: its
# optional "(?:WELL[-_])?" prefix lets the main capture group swallow a
# leading report-type token when the filename is "{TYPE}_WELL-{id}...pdf"
# (e.g. "DDR_WELL-NHK-001_2658m.pdf" -> well_name "DDR_WELL-NHK-001", not
# "WELL-NHK-001" / "NHK-001") — reproduced directly against a real
# ingestion in this pass, not hypothetical. Out of scope for this pass to
# fix in the extraction pipeline itself (task requirement: don't rewrite
# extraction algorithms), so this resolver strips the same well-known
# report-type prefixes before matching -- a data-interpretation step in
# THIS module, not a change to how module 01 extracts text.
_KNOWN_REPORT_TYPE_PREFIX = re.compile(r"^(?:DDR|WCR|DLR|MUD_LOG|MORNING_REPORT)[-_]", re.IGNORECASE)


def _normalize_well_token(s: str) -> str:
    s = _KNOWN_REPORT_TYPE_PREFIX.sub("", s.strip())
    return _WELL_NAME_NORMALIZE.sub("/", s).upper()


def resolve_well_id(well_name: Optional[str], known_well_ids: list[str]) -> Optional[str]:
    """
    Exact-match-only resolution from a document's free-text well_name to a
    canonical well_id. Deliberately conservative: module 01's OCR/regex
    extraction of well_name is frequently noise (e.g. "REPORT",
    "evaluation", a filename fragment like "11194EBA40_WELL-15" — observed
    directly in modules/01_document_intelligence/data/output/*.json, not
    hypothetical) or a near-miss that differs only in separator convention
    ("15_9-F-1" for the real well_id "15/9-F-1"). A fuzzy/substring matcher
    would resolve some of those correctly and some WRONG -- silently
    attributing a document (and its events) to the wrong well is worse
    than leaving well_id null, so this only ever returns a well_id for:
      (a) an exact, case-insensitive match against a known well_id, or
      (b) the same after normalizing underscores/whitespace to '/' (the
          one real, confirmed OCR variation — "15_9-F-1" <-> "15/9-F-1"),
          or
      (c) a known well_id's own well_name suffix after the "WELL-XXX-NNN"
          prefix is stripped (synthetic wells' well_name is the bare code,
          e.g. "BGJ-007" for well_id "WELL-BGJ-007" — confirmed via the
          live wells table, not assumed).
    Returns None (not a guess) when nothing matches exactly.
    """
    if not well_name or not well_name.strip():
        return None

    candidate = _KNOWN_REPORT_TYPE_PREFIX.sub("", well_name.strip())
    candidate_norm = _normalize_well_token(candidate)

    for well_id in known_well_ids:
        if candidate.upper() == well_id.upper():
            return well_id
        if candidate_norm == _normalize_well_token(well_id):
            return well_id
        # "WELL-BGJ-007" -> bare suffix "BGJ-007", matched against the
        # document's extracted well_name (which never carries the WELL-
        # prefix for the synthetic testbed's own wells).
        if well_id.upper().startswith("WELL-"):
            bare = well_id[len("WELL-"):]
            if candidate.upper() == bare.upper():
                return well_id
            if candidate_norm == _normalize_well_token(bare):
                return well_id

    return None


def _unwrap(field: Any) -> Any:
    """Module 01's ExtractedField wraps a value as
    {"normalized_value": ..., ...}; some fields are instead a bare float
    or None. Returns the usable scalar in all three cases."""
    if field is None:
        return None
    if isinstance(field, dict):
        return field.get("normalized_value")
    return field


def _parse_report_date(raw: Optional[str]) -> Optional[str]:
    """`report_date` is captured verbatim from the source document's own
    text by a regex (tier1_native_extractor.py's RE for "DATE: dd/mm/yyyy"
    style headers) -- genuinely ambiguous (DD/MM vs MM/DD) and NOT already
    normalized to ISO despite the Pydantic field's own comment claiming
    "ISO date string" (it was never actually enforced at the point of
    extraction). Passed straight through to a Postgres DATE column
    unchanged, this broke real documents: confirmed live with this
    project's own sample DDR ("15/03/2025" -- day 15 has no valid
    interpretation as a month under Postgres's default MDY datestyle, so
    the insert raised and sync_document/sync_review/handoff_events all
    failed non-fatally but silently for every such document).

    This project's source documents are Indian drilling reports (OIL
    India, Upper Assam) where DD/MM/YYYY is the standard convention, so
    that's tried first; MM/DD/YYYY is tried as a fallback for the rare
    document that genuinely uses it (distinguishable only when the first
    number is > 12, same ambiguity any DD/MM vs MM/DD parser has to
    accept). A date that parses under neither interpretation is honestly
    skipped (returns None) rather than guessed at or fabricated -- the
    rest of the document's extraction is unaffected either way, since
    report_date is metadata, not a drilling fact."""
    if not raw:
        return None
    raw = raw.strip()
    import datetime
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    logger.debug(f"report_date '{raw}' did not match any known format -- stored as NULL, not guessed")
    return None


def _document_row(result: dict[str, Any], well_id: Optional[str]) -> dict[str, Any]:
    return {
        "document_id": result["document_id"],
        "job_id": result.get("job_id") or None,
        "source_filename": result["source_filename"],
        "document_type": result.get("document_type") or "UNKNOWN",
        "well_id": well_id,
        "well_name": result.get("well_name"),
        "operator": result.get("operator"),
        "report_date": _parse_report_date(result.get("report_date")),
        "total_pages": result.get("total_pages", 0),
        "pages_processed": result.get("pages_processed", 0),
        "scanned_pages": result.get("scanned_pages", 0),
        "template_used": result.get("template_used"),
        "extraction_started_at": result.get("extraction_started_at"),
        "extraction_completed_at": result.get("extraction_completed_at"),
        "total_processing_time_ms": result.get("total_processing_time_ms", 0.0),
        "cloud_fallback_pages_count": result.get("cloud_fallback_pages_count", 0),
        "cloud_fallback_providers_used": result.get("cloud_fallback_providers_used") or [],
        "total_npt_hours": result.get("total_npt_hours", 0.0),
        "validation_status": result.get("validation_status", "PASS"),
        "overall_confidence": result.get("overall_confidence", 0.0),
        "flagged_fields_count": result.get("flagged_fields_count", 0),
        "physics_violations_count": result.get("physics_violations_count", 0),
        "witsml_compliant": result.get("witsml_compliant", True),
    }


def _extraction_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten formation_tops/npt_records/mud_properties ExtractedFields
    into the generic document_extractions table (schema.sql's "task
    requirement #7" table) — one row per named field actually extracted,
    skipping fields that are None (never attempted / not present)."""
    doc_id = result["document_id"]
    rows: list[dict[str, Any]] = []

    def add(field_name: str, field: Any, page_number: Optional[int] = None):
        if field is None:
            return
        if isinstance(field, dict):
            value = field.get("normalized_value")
            confidence = field.get("confidence")
            status = field.get("validation_status", "PASS")
            tier = field.get("extraction_tier", "")
        else:
            value, confidence, status, tier = field, None, "PASS", ""
        if value is None:
            return
        rows.append({
            "document_id": doc_id,
            "field_name": field_name,
            "field_value": str(value),
            "confidence": confidence,
            "extraction_method": "ocr" if "OCR" in str(tier).upper() else "regex",
            "page_number": page_number,
            "validation_status": status,
        })

    for top in result.get("all_formation_tops", []):
        add("formation_top.top_md_m", top.get("top_md_m"))
        add("formation_top.top_tvd_m", top.get("top_tvd_m"))
        add("formation_top.base_md_m", top.get("base_md_m"))

    for npt in result.get("all_npt_records", []):
        add("npt.npt_hours", npt.get("npt_hours"))
        add("npt.depth_md_m", npt.get("depth_md_m"))

    for mud in result.get("mud_properties", []):
        for key in ("mud_weight_ppg", "funnel_viscosity_sec", "plastic_viscosity_cp",
                    "yield_point_lbf_100sqft", "water_loss_ml_30min", "cake_thickness_mm",
                    "chloride_content_ppm", "ph"):
            add(f"mud_properties.{key}", mud.get(key))

    return rows


def sync_document(result: dict[str, Any]) -> dict[str, Any]:
    """
    Write-through a completed/updated extraction result into the canonical
    `documents` + `document_extractions` tables. Called right after
    orchestrator.py's own JSON save succeeds.

    Best-effort and NEVER raises: a database outage must not fail (or
    even log as an error) an ingestion that already succeeded and already
    has a durable JSON copy on disk. Returns a dict with a closed-enum
    "status" (SyncStatus — safe to show a user directly) plus whatever
    extra detail that status allows; the full exception text, when there
    is one, goes to the server log only, never into the returned dict.
    """
    if not db_is_configured():
        return {"synced": False, "status": "not_configured"}

    try:
        with get_connection() as conn:
            repo = DocumentRepository(conn)

            from app.modules.nwis.db.repositories import WellRepository
            well_repo = WellRepository(conn)
            known_ids = [r["well_id"] for r in well_repo.list_all()]
            well_id = resolve_well_id(result.get("well_name"), known_ids)

            repo.upsert_document(_document_row(result, well_id))
            n_extractions = repo.insert_extractions(result["document_id"], _extraction_rows(result))

            if result.get("reviewed"):
                repo.upsert_review(result["document_id"], result)

        return {"synced": True, "status": "synced", "well_id": well_id, "extractions_written": n_extractions}
    except Exception as exc:
        logger.warning(f"Postgres write-through for document {result.get('document_id')} failed (non-fatal, JSON copy is authoritative): {exc}")
        status: SyncStatus = "unavailable" if _is_connectivity_error(exc) else "error"
        return {"synced": False, "status": status}


def sync_review(doc_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Write-through after review.py's /decision or /annotate endpoints
    update data/output/{doc_id}.json. Same best-effort/never-raises
    contract as sync_document — the JSON file (already saved by the
    caller) remains authoritative for module 01's own routes regardless of
    whether this succeeds.

    document_review.document_id REFERENCES documents(document_id), so this
    first ensures a documents row exists (an idempotent UPSERT, same as
    sync_document's own) before writing the review state. Found live, not
    theoretical: a document opened from the review queue that was never
    successfully synced at ingest time (e.g. ingested before Pass 4, or an
    earlier sync_document() call that itself failed) has no documents row
    yet -- without this, every review decision on such a document would
    hit a foreign-key violation and report "error" even though nothing
    about the review itself was wrong."""
    if not db_is_configured():
        return {"synced": False, "status": "not_configured"}
    try:
        with get_connection() as conn:
            repo = DocumentRepository(conn)

            from app.modules.nwis.db.repositories import WellRepository
            known_ids = [r["well_id"] for r in WellRepository(conn).list_all()]
            well_id = resolve_well_id(result.get("well_name"), known_ids)
            repo.upsert_document(_document_row(result, well_id))

            repo.upsert_review(doc_id, result)
        return {"synced": True, "status": "synced"}
    except Exception as exc:
        logger.warning(f"Postgres review write-through for {doc_id} failed (non-fatal): {exc}")
        status: SyncStatus = "unavailable" if _is_connectivity_error(exc) else "error"
        return {"synced": False, "status": status}


def handoff_events(result: dict[str, Any]) -> dict[str, Any]:
    """
    The document -> canonical drilling_events handoff (task requirement:
    "accepted structured drilling facts reach the canonical NWIS data
    layer with provenance and evidence links... without inventing
    historical event records").

    Only reviewed+approved documents are eligible — an un-reviewed or
    rejected document's events are extraction candidates, not confirmed
    drilling facts, and PS 26121's own curation workflow (review.py) exists
    precisely to gate that distinction. Within an eligible document, an
    individual event is migrated only if BOTH:
      (a) its well_name resolves to a real well_id (resolve_well_id, exact-
          match only), and
      (b) its event_type exists in the canonical hazard_type table (not in
          UNMAPPED_EVENT_TYPES).
    Anything else is counted and returned as "skipped", never forced in
    with a fabricated well_id or an invented hazard_type. Idempotent:
    event_id is module 01's own stable business key, so re-running this
    for the same document twice re-upserts the same rows, not duplicates.

    drilling_events.source_document_id REFERENCES documents(document_id) —
    this function ensures that row exists (the same idempotent UPSERT
    sync_document/sync_review already do) before writing any event, rather
    than relying on every call site to have called one of those first.
    Found live as a real bug in sync_review() (see its own docstring);
    applied here too defensively, since every current caller (review.py)
    does call sync_review() first, but a future caller that didn't would
    hit the identical foreign-key violation otherwise.
    """
    if not db_is_configured():
        return {"migrated": 0, "skipped": 0, "status": "not_configured"}

    if result.get("validation_status") != "PASS" or result.get("review_decision") != "approved":
        # Not a sync failure — this is handoff_events()'s own eligibility
        # gate working as designed (see docstring). "status" here still
        # uses the shared SyncStatus vocabulary for consistency with
        # sync_document/sync_review, but "synced" is the right value: the
        # call itself completed normally, it just correctly migrated
        # nothing because the document isn't approved yet.
        return {"migrated": 0, "skipped": len(result.get("all_drilling_events", [])), "status": "synced", "reason": "not_approved"}

    events = result.get("all_drilling_events", [])
    if not events:
        return {"migrated": 0, "skipped": 0}

    try:
        with get_connection() as conn:
            from app.modules.nwis.db.repositories import WellRepository
            known_ids = [r["well_id"] for r in WellRepository(conn).list_all()]
            well_id = resolve_well_id(result.get("well_name"), known_ids)

            DocumentRepository(conn).upsert_document(_document_row(result, well_id))

            handoff_repo = EventHandoffRepository(conn)
            valid_hazards = handoff_repo.valid_hazard_codes()

            migrated, skipped, skip_reasons = 0, 0, []
            for ev in events:
                event_type = ev.get("event_type")
                if well_id is None:
                    skipped += 1
                    skip_reasons.append({"event_id": ev.get("event_id"), "reason": "unresolved_well_name", "well_name": result.get("well_name")})
                    continue
                if event_type not in valid_hazards or event_type in UNMAPPED_EVENT_TYPES:
                    skipped += 1
                    skip_reasons.append({"event_id": ev.get("event_id"), "reason": "unmapped_hazard_type", "event_type": event_type})
                    continue

                depth_start = _unwrap(ev.get("depth_start_md_m"))
                if depth_start is None:
                    skipped += 1
                    skip_reasons.append({"event_id": ev.get("event_id"), "reason": "missing_depth"})
                    continue

                handoff_repo.upsert_event({
                    "event_id": ev["event_id"],
                    "well_id": well_id,
                    "event_type": event_type,
                    "severity": ev.get("severity", "MEDIUM"),
                    "depth_start_md_m": depth_start,
                    "depth_end_md_m": _unwrap(ev.get("depth_end_md_m")),
                    "formation": ev.get("formation"),
                    "raw_narrative": ev.get("raw_narrative") or "",
                    "npt_hours": _unwrap(ev.get("npt_hours")) or 0.0,
                    "loss_rate_bbl_hr": _unwrap(ev.get("loss_rate_bbl_hr")),
                    "mitigation_description": ev.get("mitigation_description"),
                    "outcome": ev.get("outcome"),
                    "confidence": ev.get("confidence", 0.0),
                    "source_document_id": result["document_id"],
                    "source_page": None,
                    "extraction_confidence": ev.get("confidence", 0.0),
                    # REAL, not DERIVED: this is a human-approved extraction
                    # of an actual event narrated in an uploaded document
                    # (same provenance class as real_data/
                    # real_events_depth_tagged_fresh.json's EVT-REAL-xxx
                    # rows) — DERIVED is reserved for rows this project's
                    # own engines COMPUTE from other rows (DORS, risk
                    # corridors), which this is not.
                    "source_type": "REAL",
                })
                migrated += 1

        return {"migrated": migrated, "skipped": skipped, "skip_detail": skip_reasons, "well_id": well_id, "status": "synced"}
    except Exception as exc:
        logger.warning(f"Event handoff for document {result.get('document_id')} failed (non-fatal): {exc}")
        status: SyncStatus = "unavailable" if _is_connectivity_error(exc) else "error"
        return {"migrated": 0, "skipped": len(events), "status": status}
