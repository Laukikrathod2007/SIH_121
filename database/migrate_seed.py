"""
Load the existing modules/02_nwis_backend synthetic testbed into the new
Postgres/PostGIS/pgvector schema (schema.sql).

This does NOT touch modules/01 or modules/02's own SQLite/JSON storage --
it's a one-way load into the new database layer so it's genuinely populated
rather than an empty shell. Run against local Docker after `docker compose
up -d` (the default DSN below), or against any other Postgres (e.g.
Supabase) by setting NWIS_DATABASE_URL first -- same env var
Backend/app/core/config.py reads, so one connection string works for both
the seed script and the running app:

    pip install -r requirements.txt
    python migrate_seed.py                              # local Docker default
    NWIS_DATABASE_URL=postgresql://... python migrate_seed.py   # any other Postgres
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# sentence-transformers pulls in TensorFlow if it's importable at all, which
# on this machine's shared environment hits a protobuf gencode/runtime
# version mismatch (unrelated to this project -- some other installed
# package's TF pin). We only need the PyTorch backend here, so tell
# transformers not to touch TF at all rather than fighting the version pin.
os.environ.setdefault("USE_TF", "0")

import psycopg

# NWIS_DATABASE_URL takes priority when set (the same env var the running
# app reads, Backend/app/core/config.py) -- this was previously a hardcoded
# local-Docker-only DSN that silently ignored NWIS_DATABASE_URL entirely,
# so pointing it at a remote Postgres (e.g. Supabase) had no effect; the
# script just re-seeded local Docker every time regardless of what was set.
DB_DSN = os.environ.get("NWIS_DATABASE_URL") or "host=localhost port=5433 dbname=nwis user=nwis password=nwis_dev_password"

SYNTH_DIR = Path(__file__).resolve().parent.parent / "modules" / "02_nwis_backend" / "data" / "synthetic"
REAL_DATA_DIR = Path(__file__).resolve().parent.parent / "real_data"

# Mirrors data_store.py's REAL_WELLS exactly -- the same two real Volve
# wells the live module 02 app actually serves. Rows in real_data/*.json
# for any OTHER well_id (e.g. "15/9-19B", present in real_formations_fresh
# /real_events_depth_tagged_fresh but never added to data_store.py's live
# well set) are intentionally skipped here too, so this seed script's
# database matches what the running application actually shows -- not a
# superset of it.
REAL_WELLS = [
    {
        "well_id": "15/9-F-12", "well_name": "15/9-F-12", "field": "Volve",
        "field_code": "VOLVE", "operator": "Equinor", "surface_lat": 58.441613,
        "surface_lon": 1.887480, "kb_elevation_m": 54.90, "total_depth_md_m": 3520.0,
        "well_type": "J-Type", "status": "COMPLETED", "witsml_uid": None,
    },
    {
        "well_id": "15/9-F-1", "well_name": "15/9-F-1", "field": "Volve",
        "field_code": "VOLVE", "operator": "Equinor", "surface_lat": 58.441641,
        "surface_lon": 1.887419, "kb_elevation_m": 54.90, "total_depth_md_m": 3632.0,
        "well_type": "J-Type", "status": "COMPLETED", "witsml_uid": None,
    },
]
REAL_WELL_IDS = {w["well_id"] for w in REAL_WELLS}
REAL_TRAJECTORY_KEY = {"15/9-F-12": "WELL-15_9-F-12", "15/9-F-1": "WELL-15_9-F-1"}
VOLVE_MAX_PLAUSIBLE_DEPTH_M = 6000.0  # mirrors data_store.py's known-bad-row filter

# Mirrors engines/dors_engine.py's ASSAM_FORMATION_GROUPS exactly.
ASSAM_FORMATION_GROUPS = {
    "UPPER_ASSAM": {"Alluvium", "Dihing", "Tipam Sandstone", "Girujan Clay"},
    "BARAIL": {"Barail Sandstone", "Barail Coal-Shale"},
    "EOCENE": {"Kopili", "Sylhet Limestone", "Langpar"},
    "BASEMENT": {"Basement"},
}


def formation_group(name: str) -> str:
    for group, members in ASSAM_FORMATION_GROUPS.items():
        if name in members:
            return group
    return "UNKNOWN"


def load_json(name: str):
    with open(SYNTH_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def get_embedder():
    """Same model as search/knowledge_search.py -- 384-dim, normalized."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as exc:
        print(f"[warn] sentence-transformers unavailable ({exc}); event_embeddings will be skipped.")
        return None


def searchable_text(evt: dict) -> str:
    """Same construction as knowledge_search.py's _searchable_text()."""
    parts = [
        evt.get("event_type", ""),
        evt.get("formation") or "",
        evt.get("raw_narrative", ""),
        evt.get("mitigation_description") or "",
        evt.get("outcome") or "",
    ]
    return " ".join(p for p in parts if p)


def load_real_json(name: str, default=None):
    path = REAL_DATA_DIR / name
    if not path.exists():
        print(f"[warn] real_data file missing, skipping: {path}")
        return default if default is not None else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    wells = load_json("wells.json")
    trajectories = load_json("trajectories.json")
    formation_tops = load_json("formation_tops.json")
    drilling_events = load_json("drilling_events.json")
    telemetry = load_json("telemetry_stream.json")

    print(f"Loaded: {len(wells)} wells, {len(trajectories)} trajectories, "
          f"{len(formation_tops)} formation tops, {len(drilling_events)} events, "
          f"{telemetry['total_records']} telemetry records for {telemetry['active_well_id']}")

    # --- Real Volve data (additive to the synthetic testbed above, exactly
    # as data_store.py loads it into the live in-memory store) ---
    real_casing_raw = load_real_json("real_casing_records_all.json")
    real_formations_raw = [
        t for t in load_real_json("real_formations_fresh.json")
        if t.get("well_id") in REAL_WELL_IDS
        and t.get("top_md_m") is not None
        and t["top_md_m"] <= VOLVE_MAX_PLAUSIBLE_DEPTH_M
    ]
    real_events_raw_all = [
        e for e in load_real_json("real_events_depth_tagged_fresh.json")
        if e.get("well_id") in REAL_WELL_IDS and e.get("hazard_type") is not None
    ]
    # Same dedupe as data_store.py: the same real event can be narrated in
    # more than one source document for the same well.
    seen_events, real_events_raw = set(), []
    for e in real_events_raw_all:
        key = (e["well_id"], e["hazard_type"], e["depth_start_md_m"])
        if key in seen_events:
            continue
        seen_events.add(key)
        real_events_raw.append(e)

    real_traj_raw = {t["well_id"]: t for t in load_real_json("real_trajectories_witsml.json")}
    real_trajectories = []
    for w in REAL_WELLS:
        traj_key = REAL_TRAJECTORY_KEY.get(w["well_id"])
        t = real_traj_raw.get(traj_key) if traj_key else None
        if t is not None:
            real_trajectories.append({"well_id": w["well_id"], "stations": t["stations"],
                                       "method": t.get("method", "MINIMUM_CURVATURE")})

    print(f"Loaded (real): {len(REAL_WELLS)} Volve wells, {len(real_trajectories)} trajectories, "
          f"{len(real_formations_raw)} formation tops, {len(real_events_raw)} events, "
          f"{len(real_casing_raw)} casing records")

    conn = psycopg.connect(DB_DSN, autocommit=False)
    try:
        with conn.cursor() as cur:
            # --- Tier 1: operators, fields (derived from the wells list) ---
            operators = sorted({w["operator"] for w in wells})
            for op in operators:
                cur.execute(
                    "INSERT INTO operators (operator_code, operator_name) VALUES (%s, %s) "
                    "ON CONFLICT (operator_code) DO NOTHING",
                    (op, op.replace("_", " ").title()),
                )

            fields = {(w["field_code"], w["field"]) for w in wells}
            for field_code, field_name in sorted(fields):
                cur.execute(
                    """INSERT INTO fields (field_code, field_name, operator_id)
                       SELECT %s, %s, o.operator_id FROM operators o
                       WHERE o.operator_code = (
                           SELECT operator FROM (SELECT %s::text AS operator) x
                       )
                       ON CONFLICT (field_code) DO NOTHING""",
                    (field_code, field_name, wells[0]["operator"]),
                )
            # Simpler, correct field->operator link (the above is best-effort
            # for a single-operator testbed): fix any NULL operator_id by
            # picking the operator of the first well seen in that field.
            field_operator = {}
            for w in wells:
                field_operator.setdefault(w["field_code"], w["operator"])
            for field_code, operator_code in field_operator.items():
                cur.execute(
                    """UPDATE fields SET operator_id = (
                           SELECT operator_id FROM operators WHERE operator_code = %s
                       ) WHERE field_code = %s AND operator_id IS NULL""",
                    (operator_code, field_code),
                )

            # --- Tier 1: formations reference table (derived from tops + group map) ---
            formation_names = sorted({t["formation_name"] for t in formation_tops})
            for name in formation_names:
                cur.execute(
                    "INSERT INTO formations (formation_name, stratigraphic_group) VALUES (%s, %s) "
                    "ON CONFLICT (formation_name) DO NOTHING",
                    (name, formation_group(name)),
                )

            # --- Tier 1: wells (PostGIS geography point) ---
            for w in wells:
                cur.execute(
                    """INSERT INTO wells
                        (well_id, well_name, field_id, operator_id, surface_location,
                         kb_elevation_m, total_depth_md_m, well_type, spud_date,
                         completion_date, status, witsml_uid, source_type)
                       VALUES (%s, %s,
                        (SELECT field_id FROM fields WHERE field_code = %s),
                        (SELECT operator_id FROM operators WHERE operator_code = %s),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s, %s, %s, %s, %s, %s, 'SYNTHETIC')
                       ON CONFLICT (well_id) DO NOTHING""",
                    (w["well_id"], w["well_name"], w["field_code"], w["operator"],
                     w["surface_lon"], w["surface_lat"], w["kb_elevation_m"],
                     w["total_depth_md_m"], w["well_type"], w.get("spud_date"),
                     w.get("completion_date"), w["status"], w["witsml_uid"]),
                )

            # --- Tier 2: trajectory_stations ---
            n_stations = 0
            for traj in trajectories:
                well_id = traj["well_id"]
                for s in traj["stations"]:
                    cur.execute(
                        """INSERT INTO trajectory_stations
                            (well_id, md_m, inclination_deg, azimuth_deg, tvd_m, ns_m, ew_m,
                             tvdss_m, method)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (well_id, md_m) DO NOTHING""",
                        (well_id, s["md_m"], s["inclination_deg"], s["azimuth_deg"],
                         s["tvd_m"], s["ns_m"], s["ew_m"], s["tvdss_m"],
                         traj.get("method", "MINIMUM_CURVATURE")),
                    )
                    n_stations += 1

            # --- Tier 2: formation_tops ---
            for t in formation_tops:
                cur.execute(
                    """INSERT INTO formation_tops
                        (well_id, formation_name, formation_id, top_md_m, top_tvd_m,
                         base_md_m, thickness_m, pore_pressure_gradient_ppg, lithology, confidence,
                         source_type)
                       VALUES (%s, %s, (SELECT formation_id FROM formations WHERE formation_name = %s),
                               %s, %s, %s, %s, %s, %s, %s, 'SYNTHETIC')
                       ON CONFLICT (well_id, formation_name, top_md_m) DO NOTHING""",
                    (t["well_id"], t["formation_name"], t["formation_name"],
                     t["top_md_m"], t["top_tvd_m"], t["base_md_m"], t.get("thickness_m"),
                     t.get("pore_pressure_gradient_ppg"), t.get("lithology"), t.get("confidence", 0.9)),
                )

            # --- Tier 2: drilling_events (+ Tier 3: event_embeddings) ---
            embedder = get_embedder()
            n_embedded = 0
            for e in drilling_events:
                cur.execute(
                    """INSERT INTO drilling_events
                        (event_id, well_id, event_type, severity, depth_start_md_m, depth_end_md_m,
                         formation, formation_id, raw_narrative, npt_hours, iadc_npt_code,
                         loss_rate_bbl_hr, mitigation_description, outcome, confidence,
                         witsml_mapping, source_document_id, source_page, source_type)
                       VALUES (%s, %s, %s, %s, %s, %s, %s,
                               (SELECT formation_id FROM formations WHERE formation_name = %s),
                               %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, 'SYNTHETIC')
                       ON CONFLICT (event_id) DO NOTHING""",
                    (e["event_id"], e["well_id"], e["event_type"], e["severity"],
                     e["depth_start_md_m"], e.get("depth_end_md_m"), e.get("formation"),
                     e.get("formation"), e["raw_narrative"], e.get("npt_hours", 0.0),
                     e.get("iadc_npt_code"), e.get("loss_rate_bbl_hr"),
                     e.get("mitigation_description"), e.get("outcome"),
                     e.get("confidence", 0.9), e.get("witsml_mapping", ""),
                     e.get("source_page")),
                )
                if embedder is not None:
                    text = searchable_text(e)
                    vec = embedder.encode(text, normalize_embeddings=True).tolist()
                    cur.execute(
                        """INSERT INTO event_embeddings (event_id, embedding, source_text_preview)
                           VALUES (%s, %s, %s) ON CONFLICT (event_id) DO NOTHING""",
                        (e["event_id"], vec, text[:200]),
                    )
                    n_embedded += 1

            # --- Tier 2: telemetry_records (TimescaleDB hypertable) ---
            n_telemetry = 0
            for r in telemetry["records"]:
                cur.execute(
                    """INSERT INTO telemetry_records
                        (time, well_id, depth_m, rop_m_hr, wob_klbs, rpm, torque_kn_m,
                         standpipe_pressure_psi, flow_in_lpm, flow_out_lpm, pit_volume_bbl,
                         mud_weight_ppg, d_exponent)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (well_id, time) DO NOTHING""",
                    (r["timestamp"], r["well_id"], r["depth_m"], r.get("rop_m_hr", 0),
                     r.get("wob_klbs", 0), r.get("rpm", 0), r.get("torque_kn_m", 0),
                     r.get("standpipe_pressure_psi", 0), r.get("flow_in_lpm", 0),
                     r.get("flow_out_lpm", 0), r.get("pit_volume_bbl", 0),
                     r.get("mud_weight_ppg", 9.0), r.get("d_exponent", 1.0)),
                )
                n_telemetry += 1

            # --- Real Volve data (additive; source_type='REAL' throughout) ---
            cur.execute(
                "INSERT INTO operators (operator_code, operator_name) VALUES (%s, %s) "
                "ON CONFLICT (operator_code) DO NOTHING",
                ("Equinor", "Equinor"),
            )
            cur.execute(
                """INSERT INTO fields (field_code, field_name, operator_id)
                   SELECT %s, %s, operator_id FROM operators WHERE operator_code = 'Equinor'
                   ON CONFLICT (field_code) DO NOTHING""",
                ("VOLVE", "Volve"),
            )

            for w in REAL_WELLS:
                cur.execute(
                    """INSERT INTO wells
                        (well_id, well_name, field_id, operator_id, surface_location,
                         kb_elevation_m, total_depth_md_m, well_type, status, source_type)
                       VALUES (%s, %s,
                        (SELECT field_id FROM fields WHERE field_code = 'VOLVE'),
                        (SELECT operator_id FROM operators WHERE operator_code = 'Equinor'),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s, %s, %s, 'REAL')
                       ON CONFLICT (well_id) DO NOTHING""",
                    (w["well_id"], w["well_name"], w["surface_lon"], w["surface_lat"],
                     w["kb_elevation_m"], w["total_depth_md_m"], w["well_type"], w["status"]),
                )

            n_real_stations = 0
            for traj in real_trajectories:
                for s in traj["stations"]:
                    cur.execute(
                        """INSERT INTO trajectory_stations
                            (well_id, md_m, inclination_deg, azimuth_deg, tvd_m, ns_m, ew_m,
                             tvdss_m, method, source_type)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'REAL')
                           ON CONFLICT (well_id, md_m) DO NOTHING""",
                        (traj["well_id"], s["md_m"], s["inclination_deg"], s["azimuth_deg"],
                         s["tvd_m"], s["ns_m"], s["ew_m"], s["tvdss_m"], traj["method"]),
                    )
                    n_real_stations += 1

            for t in real_formations_raw:
                formation_name = t["formation_name"]
                cur.execute(
                    "INSERT INTO formations (formation_name, stratigraphic_group) VALUES (%s, %s) "
                    "ON CONFLICT (formation_name) DO NOTHING",
                    (formation_name, formation_group(formation_name)),
                )
                # real_formations_fresh.json carries only a top_md_m per row
                # (see real_data/extract_real_trajectories.py's source
                # table) -- no base/thickness. data_store.py's own
                # in-memory FormationTop for this same file assumes a 50m
                # nominal thickness (top_tvd_m=top_md_m, base_md_m=top_md_m
                # + 50) since no better bound is available; mirrored
                # verbatim here rather than inventing a different number.
                cur.execute(
                    """INSERT INTO formation_tops
                        (well_id, formation_name, formation_id, top_md_m, top_tvd_m,
                         base_md_m, thickness_m, source_type)
                       VALUES (%s, %s, (SELECT formation_id FROM formations WHERE formation_name = %s),
                               %s, %s, %s, %s, 'REAL')
                       ON CONFLICT (well_id, formation_name, top_md_m) DO NOTHING""",
                    (t["well_id"], formation_name, formation_name,
                     t["top_md_m"], t["top_md_m"], t["top_md_m"] + 50, 50.0),
                )

            for i, e in enumerate(real_events_raw):
                event_id = f"EVT-REAL-{i:03d}"
                cur.execute(
                    """INSERT INTO drilling_events
                        (event_id, well_id, event_type, severity, depth_start_md_m,
                         source_document_id, source_type)
                       VALUES (%s, %s, %s, %s, %s, NULL, 'REAL')
                       ON CONFLICT (event_id) DO NOTHING""",
                    (event_id, e["well_id"], e["hazard_type"], e.get("severity", "MEDIUM"),
                     e["depth_start_md_m"]),
                )

            n_real_casing = 0
            for c in real_casing_raw:
                if c.get("well_id") not in REAL_WELL_IDS:
                    continue
                cur.execute(
                    """INSERT INTO casing_programs
                        (well_id, casing_size_inches, shoe_depth_md_m, top_of_cement_md_m, source_type)
                       VALUES (%s, %s, %s, %s, 'REAL')
                       ON CONFLICT (well_id, shoe_depth_md_m) DO NOTHING""",
                    (c["well_id"], c.get("casing_size_inches"), c["shoe_depth_md_m"],
                     c.get("top_of_cement_md_m")),
                )
                n_real_casing += 1

        conn.commit()
        print(f"Committed: {len(wells)} wells, {n_stations} trajectory stations, "
              f"{len(formation_tops)} formation tops, {len(drilling_events)} events "
              f"({n_embedded} embedded), {n_telemetry} telemetry records.")
        print(f"Committed (real): {len(REAL_WELLS)} wells, {n_real_stations} trajectory stations, "
              f"{len(real_formations_raw)} formation tops, {len(real_events_raw)} events, "
              f"{n_real_casing} casing records.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
