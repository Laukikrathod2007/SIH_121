"""
Load the existing modules/02_nwis_backend synthetic testbed into the new
Postgres/PostGIS/pgvector/TimescaleDB schema (schema.sql).

This does NOT touch modules/01 or modules/02's own SQLite/JSON storage --
it's a one-way load into the new database layer so it's genuinely populated
rather than an empty shell. Run after `docker compose up -d`:

    pip install -r requirements.txt
    python migrate_seed.py
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

DB_DSN = "host=localhost port=5433 dbname=nwis user=nwis password=nwis_dev_password"

SYNTH_DIR = Path(__file__).resolve().parent.parent / "modules" / "02_nwis_backend" / "data" / "synthetic"

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


def main():
    wells = load_json("wells.json")
    trajectories = load_json("trajectories.json")
    formation_tops = load_json("formation_tops.json")
    drilling_events = load_json("drilling_events.json")
    telemetry = load_json("telemetry_stream.json")

    print(f"Loaded: {len(wells)} wells, {len(trajectories)} trajectories, "
          f"{len(formation_tops)} formation tops, {len(drilling_events)} events, "
          f"{telemetry['total_records']} telemetry records for {telemetry['active_well_id']}")

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
                         completion_date, status, witsml_uid)
                       VALUES (%s, %s,
                        (SELECT field_id FROM fields WHERE field_code = %s),
                        (SELECT operator_id FROM operators WHERE operator_code = %s),
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        %s, %s, %s, %s, %s, %s, %s)
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
                         base_md_m, thickness_m, pore_pressure_gradient_ppg, lithology, confidence)
                       VALUES (%s, %s, (SELECT formation_id FROM formations WHERE formation_name = %s),
                               %s, %s, %s, %s, %s, %s, %s)""",
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
                         witsml_mapping, source_document_id, source_page)
                       VALUES (%s, %s, %s, %s, %s, %s, %s,
                               (SELECT formation_id FROM formations WHERE formation_name = %s),
                               %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)
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

        conn.commit()
        print(f"Committed: {len(wells)} wells, {n_stations} trajectory stations, "
              f"{len(formation_tops)} formation tops, {len(drilling_events)} events "
              f"({n_embedded} embedded), {n_telemetry} telemetry records.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
