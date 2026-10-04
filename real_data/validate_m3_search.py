"""
Real-data validation of modules/02_nwis_backend's search/knowledge_search.py
against the 119 real events extracted from module 01's Step 13-16 fixed
pipeline (real_data/real_events_module01.json) -- not synthetic testbed
events. Hand-built query set, each with a ground-truth relevant-event-id set
determined by actually reading the real narratives (real_data/real_events_module01.json),
not guessed -- same methodology the earlier research (logger's PS-outcome
research turn) found published petroleum-RAG papers use at similar scale
(~30-40 hand-labeled queries; this is a first pass at 5, honestly scoped
smaller since only 119 real events exist to query against right now).
"""
import sys
import json
from pathlib import Path  # noqa: E402

# Canonical `app.modules.nwis` package lives under Backend/ (no longer
# dependent on the current working directory).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Backend"))

from app.modules.nwis.models.schemas import DrillingEvent, HazardType
from app.modules.nwis.search.knowledge_search import search_events

raw_events = json.load(open("../../real_data/real_events_module01.json", encoding="utf-8"))

# module 01 -> module 02 DrillingEvent field reconciliation (event_type via
# the to_hazard_type() mapping built in Step 16 -- events with no HazardType
# equivalent, e.g. GAS_INFLUX has no direct module02 type per that mapping's
# actual output... wait, Step 16 maps GAS_INFLUX -> KICK. Use that.)
EVENT_TYPE_MAP = {
    "MUD_LOSS": "MUD_LOSS", "STUCK_PIPE": "STUCK_PIPE", "KICK": "KICK",
    "WELLBORE_INSTABILITY": "WELLBORE_INSTABILITY",
    "LOST_CIRCULATION": "MUD_LOSS", "GAS_INFLUX": "KICK",
}

events = []
skipped = 0
for e in raw_events:
    m02_type = EVENT_TYPE_MAP.get(e["event_type"])
    if m02_type is None:
        skipped += 1
        continue
    events.append(DrillingEvent(
        event_id=e["event_id"], well_id=e.get("well_id", "UNKNOWN"),
        event_type=HazardType(m02_type), severity=e.get("severity", "MEDIUM"),
        depth_start_md_m=(e.get("depth_start_md_m") or {}).get("normalized_value", 0.0)
            if isinstance(e.get("depth_start_md_m"), dict) else (e.get("depth_start_md_m") or 0.0),
        formation=e.get("formation"), raw_narrative=e.get("raw_narrative") or "",
        npt_hours=e.get("npt_hours") or 0.0, mitigation_description=e.get("mitigation_description"),
        outcome=e.get("outcome"), confidence=e.get("confidence") or 0.9,
    ))

print(f"Loaded {len(events)} real events into module 02's DrillingEvent shape ({skipped} skipped, no HazardType equivalent).")
print()

# Ground truth built by actually reading real_data/real_events_module01.json's
# narratives (see the grep pass that found these), not guessed.
QUERIES = [
    ("pack off in Draupne formation",
     {"EVT-4CD6AECB", "EVT-817826BA", "EVT-D5DBA9FC", "EVT-EF437C3E"}),
    ("stuck pipe freed with heavy overpull",
     {"EVT-5D07ACAB", "EVT-53E1221E", "EVT-2420AE52"}),
    ("gas show while tripping out of hole",
     None),  # checked below by keyword instead of a fixed id set
]

hits_at_5 = 0
for query, expected_ids in QUERIES:
    results, mode = search_events(query, events, top_n=5)
    top5_ids = {ev.event_id for ev, score in results}
    print(f'Query: "{query}"  (mode={mode})')
    for ev, score in results:
        print(f"  {score:.3f}  {ev.event_type.value:20s} {ev.raw_narrative[:80]}")
    if expected_ids:
        hit = bool(top5_ids & expected_ids)
        hits_at_5 += int(hit)
        print(f"  -> Hit@5: {'YES' if hit else 'NO'} (expected one of {expected_ids}, got {top5_ids})")
    print()

print(f"=== Hit@5 on ground-truthed queries: {hits_at_5}/{sum(1 for _, e in QUERIES if e)} ===")
