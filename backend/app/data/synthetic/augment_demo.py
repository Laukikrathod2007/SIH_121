"""
Demo-data augmentation layer (deterministic, derived from the base testbed).

The base testbed (generate_testbed.py -> wells/trajectories/formation_tops/
drilling_events/telemetry_stream.json) is pinned by the test suite, so this
script ADDS to it instead of regenerating it:

  * casing_programs  — casing strings set at the base of the formations a
                       real Upper-Assam well program would case off
  * mud_programs     — per-interval mud type/weight, derived from each
                       formation's pore-pressure gradient + overbalance
  * extra events     — TORQUE_SPIKE and CEMENTING_FAILURE (absent from the
                       base set) and a Kopili/Sylhet MUD_LOSS corridor in the
                       wells around the live well WELL-HGJ-012, so the live
                       replay genuinely approaches a multi-well historical
                       risk zone near TD.

Everything is computed from the base files — no random numbers — so the
output is reproducible and internally consistent (every event depth sits
inside the stated formation of that well, every casing shoe sits at a real
formation base). Replace this layer with real WCR casing/mud records when
OIL data is connected.

Run:  python augment_demo.py   (writes demo_augmentation.json next to it)
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

CASING_PLAN = [
    # (casing size, hole size, formation whose BASE sets the shoe, purpose)
    ('20"', '26"', "Alluvium", "Conductor — isolate unconsolidated surface sands"),
    ('13-3/8"', '17-1/2"', "Tipam Sandstone", "Surface — case off Tipam loss/water zones"),
    ('9-5/8"', '12-1/4"', "Barail Coal-Shale", "Intermediate — isolate reactive Barail coals/shales"),
    ('7"', '8-1/2"', None, "Production liner — to TD"),
]

MUD_TYPES = {
    "Alluvium": "Spud mud (bentonite)",
    "Dihing": "Spud mud (bentonite)",
    "Tipam Sandstone": "KCl-Polymer WBM",
    "Girujan Clay": "KCl-PHPA inhibitive WBM",
    "Barail Sandstone": "KCl-PHPA inhibitive WBM",
    "Barail Coal-Shale": "Synthetic-based mud (SBM)",
    "Kopili": "Synthetic-based mud (SBM)",
    "Sylhet Limestone": "Synthetic-based mud (SBM)",
    "Langpar": "Synthetic-based mud (SBM)",
}

# (well_id, event_type, formation, fraction into formation, severity, npt_h,
#  loss_rate, narrative, mitigation, outcome)
EXTRA_EVENTS = [
    ("WELL-HGJ-010", "MUD_LOSS", "Kopili", 0.45, "HIGH", 14.5, 38.0,
     "Partial losses of 38 bbl/hr while drilling Kopili shale-limestone interbeds; ECD 10.9 ppg against 10.26 ppg pore pressure. Pit volume down 55 bbl over 90 min.",
     "Reduced flow rate from 2200 to 1800 lpm, spotted 40 bbl medium/fine CaCO3 + nut-plug LCM pill, cut mud weight 0.2 ppg",
     "Losses cured after second pill; resumed drilling with reduced ROP"),
    ("WELL-HGJ-011", "MUD_LOSS", "Sylhet Limestone", 0.35, "CRITICAL", 22.0, 95.0,
     "Total losses at top Sylhet Limestone — returns dropped from 100% to 0% in fractured, vugular limestone. Annulus level dropped, well monitored on trip tank.",
     "Pumped 60 bbl cross-linked LCM pill, squeezed with 50 bbl cement plug, drilled out and continued with 10.6 ppg SBM and managed ECD",
     "Returns regained after cement squeeze; 22 h NPT"),
    ("WELL-NHK-003", "MUD_LOSS", "Kopili", 0.55, "MEDIUM", 5.0, 18.0,
     "Seepage losses of 18 bbl/hr in lower Kopili while circulating bottoms-up.",
     "Added 15 ppb fine CaCO3 background LCM, reduced pump rate by 10%",
     "Seepage reduced to <3 bbl/hr"),
    ("WELL-HGJ-010", "TORQUE_SPIKE", "Barail Coal-Shale", 0.30, "MEDIUM", 3.5, None,
     "Erratic surface torque spikes 18-26 kNm (baseline 12 kNm) and stick-slip while drilling Barail coal stringers; string stalled twice.",
     "Reduced WOB 20%, increased RPM to 140, added 2% lubricant; worked pipe and back-reamed stand",
     "Torque stabilised at 13-15 kNm"),
    ("WELL-HGJ-011", "TORQUE_SPIKE", "Barail Coal-Shale", 0.55, "HIGH", 6.0, None,
     "Torque spikes to 29 kNm with overpull 25 t on connection in Barail coal; cavings of blocky coal on shakers.",
     "Raised mud weight 0.3 ppg for coal stability, pumped hi-vis sweep, back-reamed out of hole to casing shoe",
     "Hole cleaned; torque back to normal after wiper trip"),
    ("WELL-MRN-006", "TORQUE_SPIKE", "Barail Sandstone", 0.60, "LOW", 1.5, None,
     "Intermittent torque spikes 16-19 kNm in abrasive Barail Sandstone; PDC bit dull grade 3-4-WT.",
     "Pulled for bit change to more durable PDC, optimised WOB/RPM",
     "ROP recovered with new bit"),
    ("WELL-HGJ-011", "CEMENTING_FAILURE", "Barail Coal-Shale", 0.98, "HIGH", 18.0, None,
     "9-5/8\" casing cement job: losses during displacement, top of cement 400 m below plan; CBL showed poor bond across Barail coal.",
     "Remedial squeeze through perforations; subsequent wells pumped lightweight lead slurry with LCM fibres and reduced displacement rate",
     "Zonal isolation confirmed by second CBL"),
    ("WELL-BGJ-008", "CEMENTING_FAILURE", "Tipam Sandstone", 0.97, "MEDIUM", 9.0, None,
     "13-3/8\" shoe track failed formation integrity test (LOT 12.1 ppg vs 13.5 ppg planned); micro-annulus suspected.",
     "Squeezed shoe with 30 bbl cement, re-ran FIT",
     "FIT passed at 13.4 ppg"),
    ("WELL-NHK-003", "CEMENTING_FAILURE", "Barail Coal-Shale", 0.97, "MEDIUM", 7.5, None,
     "Channelling in 9-5/8\" annulus due to poor centralisation in washed-out coal section.",
     "Increased centraliser count; spacer volume doubled; remedial top-up job",
     "Acceptable bond after top-up"),
]


def _tops_by_well(tops: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for t in tops:
        out.setdefault(t["well_id"], []).append(t)
    for v in out.values():
        v.sort(key=lambda t: t["top_md_m"])
    return out


def _base_md(t: dict, td: float) -> float:
    return float(t.get("base_md_m") or td)


def build() -> dict:
    wells = json.loads((HERE / "wells.json").read_text(encoding="utf-8"))
    tops = _tops_by_well(json.loads((HERE / "formation_tops.json").read_text(encoding="utf-8")))

    casing_programs, mud_programs = [], []
    for w in wells:
        wid, td = w["well_id"], float(w["total_depth_md_m"])
        wtops = tops.get(wid, [])
        by_name = {t["formation_name"]: t for t in wtops}

        prev_shoe = 0.0
        for size, hole, fm, purpose in CASING_PLAN:
            shoe = td if fm is None else _base_md(by_name[fm], td) if fm in by_name else None
            if shoe is None or shoe <= prev_shoe:
                continue
            casing_programs.append({
                "well_id": wid, "casing_size": size, "hole_size": hole,
                "top_md_m": 0.0 if size != '7"' else round(prev_shoe - 150.0, 1),
                "shoe_md_m": round(shoe, 1), "set_in_formation": fm or (wtops[-1]["formation_name"] if wtops else None),
                "purpose": purpose,
                "cement_top_md_m": round(max(0.0, prev_shoe - 200.0), 1),
                "source_document": f"WCR_{wid}.pdf",
            })
            prev_shoe = shoe

        for t in wtops:
            pp = float(t["pore_pressure_gradient_ppg"])
            mud_programs.append({
                "well_id": wid, "formation": t["formation_name"],
                "from_md_m": round(t["top_md_m"], 1), "to_md_m": round(_base_md(t, td), 1),
                "mud_type": MUD_TYPES.get(t["formation_name"], "WBM"),
                "mud_weight_ppg": round(pp + (0.4 if pp < 9.5 else 0.5), 2),
                "pore_pressure_ppg": round(pp, 2),
                "overbalance_ppg": 0.4 if pp < 9.5 else 0.5,
                "source_document": f"WCR_{wid}.pdf",
            })

    events = []
    for i, (wid, etype, fm, frac, sev, npt, loss, narr, mit, outcome) in enumerate(EXTRA_EVENTS, start=1):
        t = next((x for x in tops.get(wid, []) if x["formation_name"] == fm), None)
        if t is None:
            continue
        td = next(float(w["total_depth_md_m"]) for w in wells if w["well_id"] == wid)
        top, base = float(t["top_md_m"]), _base_md(t, td)
        depth = round(top + frac * (base - top), 1)
        events.append({
            "event_id": f"EVT-DEMO{i:03d}",
            "well_id": wid,
            "event_type": etype,
            "severity": sev,
            "depth_start_md_m": depth,
            "depth_end_md_m": round(min(base, depth + 12.0), 1),
            "formation": fm,
            "raw_narrative": f"{narr} Depth {depth} m MD.",
            "npt_hours": npt,
            "iadc_npt_code": {"MUD_LOSS": "101", "TORQUE_SPIKE": "105", "CEMENTING_FAILURE": "108"}[etype],
            "loss_rate_bbl_hr": loss,
            "mitigation_description": mit,
            "outcome": outcome,
            "confidence": 0.9,
            "provenance_tier": "OBSERVED",
            "source_document": f"DDR_{wid}_{int(depth)}m.pdf",
            "source_page": 2 + (i % 4),
        })

    return {
        "description": "Deterministic demo augmentation derived from the base testbed (see augment_demo.py).",
        "casing_programs": casing_programs,
        "mud_programs": mud_programs,
        "events": events,
    }


if __name__ == "__main__":
    out = build()
    (HERE / "demo_augmentation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"casing={len(out['casing_programs'])} mud={len(out['mud_programs'])} events={len(out['events'])}")
