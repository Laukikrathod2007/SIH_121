"""
One-off real-data augmentation script (2026-10-04 remediation pass): pulls
genuinely usable depth-tagged events out of real_events_module01.json (a raw,
119-record intermediate extraction dump that was NEVER merged into
real_events_depth_tagged_fresh.json, the file the real-model trainer
actually reads) and appends them to that file, so train_hazard_models_real.py
can use the additional real examples -- specifically to raise KICK from its
current 1 real positive (statistically unusable) and MUD_LOSS from 7
(one short of MIN_POSITIVE_SAMPLES=8).

This is NOT a blind merge. real_events_module01.json's own schema stores
depth as a raw, unprocessed ExtractedField dict (ocr/regex output that was
never normalized or human-checked), and manual inspection this session found
real problems:

  1. well_id "15/9-F-11" (19 records, 4 with a depth tag) does not correspond
     to any real well in this project's well catalog. All 4 of its
     depth-tagged narratives were manually read and are garbled fragments of
     GEOLOGICAL/LOGGING descriptive text (MagTrak tool descriptions, lithology
     unit descriptions, a report page footer) -- the entity extractor's
     "thief zone" / "no returns" keyword matches fired on incidental phrases
     inside non-incident prose, not real drilling events. EXCLUDED ENTIRELY.

  2. Two records (one for "15/9-F-11", one for "15/9-F-1") have a
     depth_start_md_m.normalized_value of 262430.0m / 262060.0m -- physically
     impossible (Assam/Volve wells are a few thousand metres deep), and both
     are already flagged FAILED_PHYSICS_VALIDATION by module 01's own Layer 5
     validator. EXCLUDED.

  3. One record for "15/9-F-1" at 66m MD, narrative "Middle Hugin or Thief
     Zone unit (zone 2...)" is a geological zonation DESCRIPTION (naming a
     stratigraphic unit called "Thief Zone"), not a loss-of-circulation
     INCIDENT -- same false-positive keyword pattern as (1). EXCLUDED.

  4. Well-ID formatting is inconsistent in the source file (underscore vs
     slash: "15_9-19B" vs "15/9-19B", "15_9-F-1C" vs the canonical
     "15/9-F-1C") -- these are the SAME real wells already in the project's
     catalog, just inconsistently formatted by whatever extraction pass
     produced this file. Normalized to the canonical slash-form IDs used
     everywhere else in this project (real_events_depth_tagged_fresh.json,
     models/schemas.py Well records) before merging.

What survives, after all of the above exclusions (manually verified against
the full raw_narrative text, not just the event_type label):
  - 15/9-19B (-> matches existing well "15/9-19B"): 14 GAS_INFLUX + 1 KICK +
    1 LOST_CIRCULATION, all with coherent, real well-control narrative
    ("Trip gas from wellhead", "Well control incident (19B)") at real depths.
  - 15_9-F-1C (-> matches existing well "15/9-F-1C"): 2 STUCK_PIPE + 1 KICK,
    real overpull/cement-tagging/well-control narrative.

Checked for duplication against the EXISTING real_events_depth_tagged_fresh.json
before appending: one existing 15/9-19B MUD_LOSS event already sits at the
same depth (3220m) as some of the new GAS_INFLUX records. Read the
narratives side by side -- the MUD_LOSS one describes a casing/loss
decision, genuinely distinct from the GAS_INFLUX trip-gas readings. Kept.

5. WITHIN the new GAS_INFLUX/KICK records themselves: 4 records all claimed
   depth=3220.0m, with narrative text that is the SAME underlying table row
   OCR'd with different character-recognition noise ("weUhead" / "welUiead"
   / "wellhead" -- a classic OCR 'll'<->'U' confusion) and matching/near-
   matching leading percentages (0%, 0%, 0%, 2%). Every OTHER depth in this
   well's trip-gas series (2805m, 317m, 3360m, 3375m, 4031m x2, 4071m,
   4109m, 4148m) has a genuinely distinct leading percentage, consistent
   with a real end-of-well trip-gas log table extracted row by row -- so
   this is specifically a duplicate-OCR-pass artifact at ONE depth, not a
   reason to distrust the series as a whole. De-duplicated by
   (well_id, hazard_type, depth_m) before merging, keeping exactly one
   record per unique depth -- the model trains on depth, so a second
   identical-depth row adds no real signal and would only inflate the
   apparent positive count.

EventType -> HazardType reconciliation uses the EXACT SAME mapping already
defined and justified in modules/01_document_intelligence/models/schemas.py's
EVENT_TYPE_TO_HAZARD_TYPE (GAS_INFLUX -> KICK, LOST_CIRCULATION -> MUD_LOSS),
not a new one invented for this script.
"""
from __future__ import annotations
import json
from pathlib import Path

REAL_DATA = Path(__file__).parent
RAW_FILE = REAL_DATA / "real_events_module01.json"
TARGET_FILE = REAL_DATA / "real_events_depth_tagged_fresh.json"

WELL_ID_NORMALIZE = {
    "15_9-19B": "15/9-19B",
    "15_9-F-1": "15/9-F-1",
    "15_9-F-1C": "15/9-F-1C",
}

# Confirmed-garbled / unexplained well bucket -- see module docstring point 1.
EXCLUDED_WELL_IDS = {"15/9-F-11"}

EVENT_TYPE_TO_HAZARD = {
    "MUD_LOSS": "MUD_LOSS",
    "STUCK_PIPE": "STUCK_PIPE",
    "KICK": "KICK",
    "WELLBORE_INSTABILITY": "WELLBORE_INSTABILITY",
    "LOST_CIRCULATION": "MUD_LOSS",
    "GAS_INFLUX": "KICK",
    "EQUIPMENT_FAILURE": None,
}

# Specific (well_id after normalization, raw event_id) pairs manually
# confirmed to be false positives / impossible depths -- see docstring
# points 2 and 3. Excluded even though their well_id is not in
# EXCLUDED_WELL_IDS, because the well itself is otherwise legitimate.
EXCLUDED_EVENT_IDS = {
    "EVT-09C3F6A2",  # 15/9-F-11 (also excluded by well), 262430.0m impossible depth
    # the 15/9-F-1 262060.0m impossible-depth record and the 66m "Thief Zone"
    # geological-description record are identified by (well_id, narrative)
    # below since this raw file's event_id for them was not noted separately
    # during manual review; matched by content instead to be explicit about
    # what's being excluded and why.
}


def normalize_well_id(raw_well_id: str) -> str:
    return WELL_ID_NORMALIZE.get(raw_well_id, raw_well_id)


def main():
    raw = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    existing = json.loads(TARGET_FILE.read_text(encoding="utf-8"))
    existing_ids = {e["event_id"] for e in existing if "event_id" in e}

    added = []
    # Seeded with every EXISTING (well_id, hazard_type, depth_m) combination
    # too, not just ones within this new batch -- a new record that exactly
    # matches an already-stored real event's well/hazard/depth is presumed
    # to be the same real-world incident re-extracted, not a second one.
    seen_well_hazard_depth = {
        (e["well_id"], e.get("hazard_type"), round(float(e["depth_start_md_m"]), 1))
        for e in existing
        if e.get("depth_start_md_m") is not None
    }
    skipped_no_depth = 0
    skipped_excluded_well = 0
    skipped_bad_hazard_map = 0
    skipped_impossible_depth = 0
    skipped_geological_description = 0
    skipped_duplicate_depth = 0

    for r in raw:
        raw_well_id = r.get("well_id")
        norm_well_id = normalize_well_id(raw_well_id)

        if raw_well_id in EXCLUDED_WELL_IDS:
            skipped_excluded_well += 1
            continue

        depth_field = r.get("depth_start_md_m")
        if not isinstance(depth_field, dict):
            skipped_no_depth += 1
            continue  # no real depth extracted for this record at all

        depth_m = depth_field.get("normalized_value")
        if depth_m is None or depth_m > 8000:
            # 8000m is a generous upper bound for this project's real wells
            # (deepest real well here is ~4000m) -- catches the two confirmed
            # impossible 262,xxx.0m records without hand-listing event_ids.
            skipped_impossible_depth += 1
            continue

        narrative = (r.get("raw_narrative") or "")
        if norm_well_id == "15/9-F-1" and abs(depth_m - 66.0) < 0.1 and "zone" in narrative.lower():
            # the one manually-confirmed geological-description false
            # positive for this well (see docstring point 3)
            skipped_geological_description += 1
            continue

        hazard_type = EVENT_TYPE_TO_HAZARD.get(r.get("event_type"))
        if hazard_type is None:
            skipped_bad_hazard_map += 1
            continue

        event_id = r.get("event_id")
        if event_id in existing_ids or event_id in EXCLUDED_EVENT_IDS:
            continue

        dedup_key = (norm_well_id, hazard_type, round(float(depth_m), 1))
        if dedup_key in seen_well_hazard_depth:
            skipped_duplicate_depth += 1
            continue
        seen_well_hazard_depth.add(dedup_key)

        added.append({
            "event_id": event_id,
            "source_file": "volve (real_events_module01.json augmentation)",
            "well_guess": norm_well_id,
            "event_type": r.get("event_type"),
            "hazard_type": hazard_type,
            "depth_start_md_m": float(depth_m),
            "severity": r.get("severity") or "MEDIUM",
            "well_id": norm_well_id,
        })

    print(f"Raw records: {len(raw)}")
    print(f"Skipped (no usable depth field): {skipped_no_depth}")
    print(f"Skipped (excluded well 15/9-F-11): {skipped_excluded_well}")
    print(f"Skipped (impossible depth >8000m): {skipped_impossible_depth}")
    print(f"Skipped (confirmed geological-description false positive): {skipped_geological_description}")
    print(f"Skipped (duplicate well/hazard/depth -- same real event re-extracted): {skipped_duplicate_depth}")
    print(f"Skipped (no HazardType mapping, e.g. EQUIPMENT_FAILURE): {skipped_bad_hazard_map}")
    print(f"NEW events to add: {len(added)}")
    for a in added:
        print(f"  {a['well_id']:12s} {a['hazard_type']:16s} depth={a['depth_start_md_m']:.1f}m  ({a['event_id']})")

    if added:
        merged = existing + added
        TARGET_FILE.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        print(f"\nWrote {len(merged)} total events to {TARGET_FILE} (was {len(existing)}).")
    else:
        print("\nNothing to add -- target file left unchanged.")


if __name__ == "__main__":
    main()
