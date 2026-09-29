"""
Document Intelligence -> Well Intelligence bridge (institutional memory).

Pushes drilling events extracted from ingested DDR/WCR PDFs into the live
NWISDataStore, so they become searchable (/events/search), show up in the
per-well evidence views, and — when they carry a depth and belong to a known
well — feed the risk-corridor / DORS engines like any other offset event.

Type translation uses document_intelligence.models.schemas.EVENT_TYPE_TO_HAZARD_TYPE
(backend-working's explicit, per-case reconciliation). Event types with no
geological-hazard equivalent (equipment failure, deviation, NPT, unknown)
are not pushed.

Events without an extracted depth are still added to the searchable
repository, but NOT to events_by_well, so they can never distort the
depth-based corridor clustering. They are marked provenance_tier
"EXTRACTED_NO_DEPTH" so the UI can say "depth not stated in source".
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings
from app.core.logging import logger
from app.modules.document_intelligence.models.schemas import EVENT_TYPE_TO_HAZARD_TYPE, EventType
from app.modules.well_intelligence.models.schemas import DrillingEvent, HazardType
from app.modules.well_intelligence.services.data_store import NWISDataStore

OUTPUT_DIR = settings.DATA_DIR / "output"


def _num(value: Any) -> Optional[float]:
    """ExtractedField dict / plain number -> float, else None."""
    if isinstance(value, dict):
        value = value.get("normalized_value")
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _norm(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (name or "").upper())


def _resolve_well_id(store: NWISDataStore, well_name: Optional[str]) -> Optional[str]:
    """Match a document's well name against known wells (id or name, punctuation-insensitive)."""
    key = _norm(well_name or "")
    if not key:
        return None
    for w in store.all_wells:
        if key in (_norm(w.well_id), _norm(w.well_name)):
            return w.well_id
    return None


def ingest_document_result(data: Dict[str, Any], store: Optional[NWISDataStore] = None) -> int:
    """Add one extraction result's events to the store. Returns events added."""
    store = store or NWISDataStore()
    if not store.is_loaded() or data.get("review_decision") == "rejected":
        return 0

    doc_id = data.get("document_id") or ""
    source = data.get("source_filename") or doc_id
    known_well_id = _resolve_well_id(store, data.get("well_name"))
    well_id = known_well_id or (data.get("well_name") or f"DOC:{doc_id}")
    existing = {e.event_id for e in store.all_events}

    added = 0
    for page in data.get("pages", []):
        page_no = page.get("page_number")
        for ev in page.get("drilling_events", []):
            event_id = f"{doc_id}:{ev.get('event_id')}"
            if event_id in existing:
                continue
            try:
                hazard = EVENT_TYPE_TO_HAZARD_TYPE.get(EventType(ev.get("event_type", "UNKNOWN")))
            except ValueError:
                hazard = None
            if hazard is None:
                continue

            depth = _num(ev.get("depth_start_md_m"))
            event = DrillingEvent(
                event_id=event_id,
                well_id=well_id,
                event_type=HazardType(hazard),
                severity=str(ev.get("severity") or "MEDIUM"),
                depth_start_md_m=depth if depth is not None else 0.0,
                depth_end_md_m=_num(ev.get("depth_end_md_m")),
                formation=ev.get("formation"),
                raw_narrative=ev.get("raw_narrative") or "",
                npt_hours=_num(ev.get("npt_hours")) or 0.0,
                loss_rate_bbl_hr=_num(ev.get("loss_rate_bbl_hr")),
                mitigation_description=ev.get("mitigation_description"),
                outcome=ev.get("outcome"),
                confidence=min(1.0, max(0.0, float(ev.get("confidence") or 0.0))),
                provenance_tier="EXTRACTED" if depth is not None else "EXTRACTED_NO_DEPTH",
                source_document=f"{source} [{doc_id}]",
                source_page=page_no,
            )
            store.all_events.append(event)
            if depth is not None and known_well_id:
                store.events_by_well.setdefault(known_well_id, []).append(event)
            existing.add(event_id)
            added += 1

    if added:
        logger.info(f"Document bridge: {added} events from {doc_id} ({source}) -> well '{well_id}'")
    return added


def ingest_all_outputs(output_dir: Path = OUTPUT_DIR) -> int:
    """Startup: replay every stored extraction result into the store."""
    total = 0
    if not output_dir.exists():
        return 0
    for path in sorted(output_dir.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                total += ingest_document_result(json.load(f))
        except Exception as exc:
            logger.warning(f"Document bridge skipped {path.name}: {exc}")
    return total
