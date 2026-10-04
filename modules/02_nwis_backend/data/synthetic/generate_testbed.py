"""
NWIS Module 02 — Assam-Arakan Basin Synthetic Testbed Generator
Generates 15 realistic wells with authentic stratigraphy, trajectories,
historical drilling incidents, and 1-Hz live telemetry streams.

Run: python generate_testbed.py
Output: wells.json, trajectories.json, formation_tops.json,
        drilling_events.json, telemetry_stream.json
"""

from __future__ import annotations
import json
import math
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
random.seed(42)

# ---------------------------------------------------------------------------
# Assam-Arakan Basin Authentic Stratigraphy (OIL India operational area)
# ---------------------------------------------------------------------------
ASSAM_STRATIGRAPHY = [
    # (name, typical_top_m, typical_thickness_m, pp_gradient_ppg, litho)
    ("Alluvium",          100,   100,  8.6,  "Unconsolidated sand-gravel"),
    ("Dihing",            200,   200,  8.7,  "Pebbly sandstone, coarse grained"),
    ("Tipam Sandstone",   400,   800,  8.9,  "Fine-medium sandstone, major aquifer"),
    ("Girujan Clay",     1200,   400,  9.2,  "Thick clay-shale, pressure seal"),
    ("Barail Sandstone", 1600,   600,  9.8,  "Tight sandstone, gas bearing"),
    ("Barail Coal-Shale",2200,   300, 10.1,  "Carbonaceous shale, coal bands"),
    ("Kopili",           2500,   400, 10.4,  "Hard limestone-shale alternation"),
    ("Sylhet Limestone", 2900,   300, 10.8,  "Fractured carbonate, prolific"),
    ("Langpar",          3200,   200, 11.2,  "Dense limestone, tight"),
    ("Basement",         3400,   500, 11.5,  "Crystalline basement, no reservoir"),
]

# ---------------------------------------------------------------------------
# OIL India operational fields (real coordinates approx)
# ---------------------------------------------------------------------------
FIELDS = [
    {"name": "Nahorkatiya",  "lat": 27.19, "lon": 95.35, "field_code": "NHK"},
    {"name": "Moran",        "lat": 27.10, "lon": 95.00, "field_code": "MRN"},
    {"name": "Baghjan",      "lat": 27.55, "lon": 95.35, "field_code": "BGJ"},
    {"name": "Hugrijan",     "lat": 27.25, "lon": 94.80, "field_code": "HGJ"},
    {"name": "Rajapukhuri",  "lat": 27.40, "lon": 95.10, "field_code": "RPK"},
]

OPERATORS = ["OIL_INDIA_LIMITED", "OIL_INDIA_LIMITED", "ONGC"]
WELL_TYPES = ["Vertical", "J-Type", "S-Type"]
TRAJECTORY_WEIGHTS = [0.50, 0.35, 0.15]  # probability per type

# ---------------------------------------------------------------------------
# Historical Incident Library (authentic petroleum engineering events)
# ---------------------------------------------------------------------------
INCIDENT_TEMPLATES = {
    "MUD_LOSS": [
        "Lost circulation encountered at {depth}m in {formation}. Total fluid loss of {volume} bbl. Pumped {pill_vol} bbl medium-nut-plug LCM pill at {pump_rate} lpm. Returned to full circulation after {npt_hr:.1f} hrs.",
        "Severe lost returns at {depth}m. Loss rate estimated {loss_rate:.0f} bbl/hr in vugular {formation}. Applied {pill_vol} bbl diesel-bentonite squeeze. NPT: {npt_hr:.1f} hrs.",
        "Partial loss of circulation at {depth}m ({formation}). Loss rate {loss_rate:.0f} bbl/hr. Reduced ECD by lowering mud weight from {mw_hi:.1f} to {mw_lo:.1f} ppg. Regained returns in {npt_hr:.1f} hrs.",
    ],
    "STUCK_PIPE": [
        "Differential pipe sticking at {depth}m in {formation}. Applied {torque:.0f} kNm right torque and reciprocated string. Worked free after {npt_hr:.1f} hrs. LCM pill not required.",
        "Tight hole observed while tripping out through {formation} at {depth}m. Pipe stuck for {npt_hr:.1f} hrs. Applied {overpull:.0f} klbs overpull. Released after spot freeing agent.",
        "Mechanical sticking in {formation} at {depth}m. Key-seating suspected. Rotated string and applied jar blows ({npt_hr:.1f} hrs NPT).",
    ],
    "KICK": [
        "Pit gain of {pit_gain:.0f} bbls observed at {depth}m while drilling {formation}. Shut in BOP. SICP={sicp:.0f} psi, SIDPP={sidpp:.0f} psi. Killed using Driller's Method in {npt_hr:.1f} hrs.",
        "Unexpected gas show at {depth}m in {formation}. Fingerprinting confirmed formation gas. Weight up mud to {mw_new:.1f} ppg. NPT {npt_hr:.1f} hrs.",
        "Gas kick detected at {depth}m. Flow check positive. Shut in well. Kill mud density {mw_new:.1f} ppg required. NPT: {npt_hr:.1f} hrs.",
    ],
    "WELLBORE_INSTABILITY": [
        "Wellbore instability (WBS) observed in {formation} at {depth}m. High cavings on shakers. Increased mud weight to {mw_new:.1f} ppg and added KCl inhibitor. NPT: {npt_hr:.1f} hrs.",
        "Tight hole and overpull of {overpull:.0f} klbs noted at {depth}m in {formation} shale. Reamed and circulated to clear cavings.",
        "Washout suspected at {depth}m in {formation}. Caliper log showed {washout:.0f}% over-gauge hole. Pumped casing cement to seal.",
    ],
    # Added 2026-10-04 (remediation pass, extending real-data-insufficient
    # hazards into the synthetic testbed -- see hazard_predictor.py docstring
    # for the full 3-tier real->synthetic->heuristic design). Torque spikes
    # are a trajectory/mechanics phenomenon (hole-cleaning, doglegs, cuttings
    # bed buildup in a deviated annulus), not primarily a lithology one --
    # unlike the other 4 hazards above, this one is triggered by WELL_TYPE in
    # generate_incidents_for_well(), not by formation lookup, which is the
    # domain-accurate anchor for this specific hazard.
    "TORQUE_SPIKE": [
        "Torque spike to {torque:.0f} kNm observed at {depth}m in {formation} while rotating through the build section. Reduced WOB and circulated bottoms-up to clear cuttings bed. NPT: {npt_hr:.1f} hrs.",
        "Erratic torque fluctuation ({torque:.0f} kNm peak) at {depth}m, consistent with stick-slip in {formation}. Reduced RPM and adjusted WOB. Resumed drilling after {npt_hr:.1f} hrs.",
        "High torque ({torque:.0f} kNm) and drag noted tripping through {formation} at {depth}m, attributed to dogleg severity in the tangent section. Reamed interval before continuing.",
    ],
    # Cementing failures correlate with washout-prone/unstable formations
    # (the same clay/shale zones already flagged for WELLBORE_INSTABILITY --
    # poor annular clearance and mud-cake quality in washed-out hole is a
    # well-established real cause of a bad cement job) rather than a
    # dedicated casing-point depth, since this testbed has no synthetic
    # casing-program schedule to anchor to (only the 2 real Volve wells have
    # real casing records -- see api.ts's getCasing() comment). Documented
    # simplification, not a fabricated casing depth.
    "CEMENTING_FAILURE": [
        "Cement bond log shows poor bond across {formation} at {depth}m, likely from washed-out hole reducing annular clearance. Squeeze cementing job scheduled. NPT: {npt_hr:.1f} hrs.",
        "Lost returns during primary cement job opposite {formation} at {depth}m. Suspected micro-annulus from inadequate mud displacement. Remedial squeeze performed.",
        "Centralizer standoff below spec across washed-out {formation} interval at {depth}m. Primary cement job failed bond log; remedial squeeze required.",
    ],
    # Overpressure zones are a transition-zone phenomenon: pore pressure
    # stepping up faster than expected as a new, higher-pp_gradient
    # formation is entered -- anchored to the TOP of a formation (the
    # transition point) rather than a random depth within it, using the
    # same pp_gradient_ppg already defined per formation in
    # ASSAM_STRATIGRAPHY, not an invented pressure value.
    "OVERPRESSURE_ZONE": [
        "Abnormal pressure transition detected entering {formation} at {depth}m: d-exponent trend broke sharply, connection gas rising. Weighted mud up to {mw_new:.1f} ppg ahead of the zone. NPT: {npt_hr:.1f} hrs.",
        "Overpressured interval confirmed at {depth}m at the {formation} transition -- pore pressure gradient stepped up above offset-well prognosis. Increased mud weight to {mw_new:.1f} ppg, monitored for well control.",
        "Early kick indicators (flow increase, pit gain trend) at {depth}m approaching {formation} top prompted a precautionary mud weight increase to {mw_new:.1f} ppg before the full transition was drilled into.",
    ],
}

SEVERITY_MAP = {
    "MUD_LOSS": ["MEDIUM", "HIGH", "CRITICAL"],
    "STUCK_PIPE": ["HIGH", "CRITICAL", "HIGH"],
    "KICK": ["HIGH", "CRITICAL", "HIGH"],
    "WELLBORE_INSTABILITY": ["MEDIUM", "MEDIUM", "HIGH"],
    "TORQUE_SPIKE": ["MEDIUM", "MEDIUM", "HIGH"],
    "CEMENTING_FAILURE": ["MEDIUM", "HIGH", "HIGH"],
    "OVERPRESSURE_ZONE": ["HIGH", "CRITICAL", "HIGH"],
}

IADC_NPT_CODES = {
    "MUD_LOSS": "201",
    "STUCK_PIPE": "101",
    "KICK": "301",
    "WELLBORE_INSTABILITY": "102",
    # UNVERIFIED placeholder codes, consistent in FORM with the 4 above
    # (same digit-length convention, distinct from 101/102/201/301) but NOT
    # confirmed against an actual IADC DDR-Plus code table -- a web search
    # during this session could not verify ANY of these four existing codes
    # or these 3 new ones against IADC's official reference. Flagged here
    # explicitly rather than asserted as real, since this field is rendered
    # directly in the UI (HistoricalIntelligencePage.tsx, NearbyWellsPage.tsx,
    # GeologicalCorrelationPage.tsx). Treat as illustrative/synthetic, not an
    # audited IADC classification, until someone checks them against
    # IADC's actual DDR-Plus documentation.
    "TORQUE_SPIKE": "401",
    "CEMENTING_FAILURE": "601",
    "OVERPRESSURE_ZONE": "302",
}

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def generate_trajectory_stations(well_type: str, td_md: float) -> list[dict]:
    """Generate survey stations using minimum curvature method."""
    stations = []
    current_md = 0.0
    current_incl = 0.0
    current_azi = random.uniform(0, 360)
    current_tvd = 0.0
    ns = 0.0
    ew = 0.0

    step = 30.0  # survey every 30m
    kickoff_md = td_md * 0.15 if well_type != "Vertical" else td_md * 2  # no kickoff for vertical

    target_incl = {
        "Vertical": 2.0,
        "J-Type": random.uniform(25, 55),
        "S-Type": random.uniform(30, 60),
    }[well_type]

    while current_md < td_md:
        next_md = min(current_md + step, td_md)
        ds = next_md - current_md

        # Build inclination profile
        if current_md < kickoff_md:
            next_incl = current_incl + random.uniform(-0.1, 0.2)
        elif current_md < kickoff_md + 400:
            # Build angle
            next_incl = current_incl + random.uniform(0.5, 2.5)
            next_incl = min(next_incl, target_incl)
        elif well_type == "S-Type" and current_md > kickoff_md + 800:
            next_incl = max(next_incl if stations else current_incl, current_incl - 1.5)
        else:
            next_incl = current_incl + random.uniform(-0.3, 0.3)

        next_incl = max(0.0, min(next_incl, 90.0))
        next_azi = current_azi + random.uniform(-1.5, 1.5)

        # Minimum curvature
        i1, i2 = math.radians(current_incl), math.radians(next_incl)
        a1, a2 = math.radians(current_azi), math.radians(next_azi)

        dl = math.acos(
            math.cos(i2 - i1) - math.sin(i1) * math.sin(i2) * (1 - math.cos(a2 - a1))
        )
        rf = (2 / dl) * math.tan(dl / 2) if dl > 0.001 else 1.0

        dtvd = ds / 2 * (math.cos(i1) + math.cos(i2)) * rf
        dns = ds / 2 * (math.sin(i1)*math.cos(a1) + math.sin(i2)*math.cos(a2)) * rf
        dew = ds / 2 * (math.sin(i1)*math.sin(a1) + math.sin(i2)*math.sin(a2)) * rf

        current_tvd += dtvd
        ns += dns
        ew += dew
        current_md = next_md
        current_incl = next_incl
        current_azi = next_azi

        stations.append({
            "md_m": round(current_md, 2),
            "inclination_deg": round(current_incl, 2),
            "azimuth_deg": round(current_azi % 360, 2),
            "tvd_m": round(current_tvd, 2),
            "ns_m": round(ns, 2),
            "ew_m": round(ew, 2),
            "tvdss_m": round(current_tvd, 2),  # simplified (kb elev ~10m)
        })

    return stations


def formation_tops_for_well(td_md: float, tvd_stations: list[dict]) -> list[dict]:
    """Generate formation top depths with variance per well."""
    tops = []
    running_md = 0.0

    for i, (name, base_top, thickness, pp_grad, litho) in enumerate(ASSAM_STRATIGRAPHY):
        # Vary top depth ±15% across wells
        variance = random.uniform(-0.12, 0.12)
        top_md = base_top * (1 + variance) + running_md * 0.01
        top_md = max(running_md + 30, top_md)

        if top_md >= td_md:
            break

        base_md = min(top_md + thickness * random.uniform(0.85, 1.15), td_md)

        # Find TVD for this MD
        tvd = top_md  # simplified linear if no stations
        for s in tvd_stations:
            if s["md_m"] >= top_md:
                tvd = s["tvd_m"] - (s["md_m"] - top_md) * 0.95
                break

        tops.append({
            "formation_name": name,
            "top_md_m": round(top_md, 1),
            "top_tvd_m": round(tvd, 1),
            "base_md_m": round(base_md, 1),
            "thickness_m": round(base_md - top_md, 1),
            "pore_pressure_gradient_ppg": pp_grad + random.uniform(-0.2, 0.2),
            "lithology": litho,
            "confidence": round(random.uniform(0.82, 0.99), 2),
        })
        running_md = top_md

    return tops


def generate_incidents_for_well(well_id: str, tops: list[dict], well_type: str = "Vertical") -> list[dict]:
    """Generate 2-6 authentic drilling incidents in hazard-prone formations.

    well_type added 2026-10-04 so TORQUE_SPIKE can be anchored to trajectory
    (deviated wells genuinely have more torque/drag issues than vertical
    ones -- a real mechanics relationship, not an arbitrary addition) rather
    than formation lithology alone, which is the domain-accurate trigger for
    that specific hazard (see INCIDENT_TEMPLATES comment above it).

    IMPORTANT on randomness isolation: every draw from the module-level
    `random` instance in this function is UNCHANGED in count, order, and
    call signature from the pre-2026-10-04 version of this function -- this
    was a real bug found and fixed in this same session. An earlier attempt
    at this extension added new `random.random()`/`random.choice()` calls
    directly into the per-incident loop using the shared `random` module,
    which silently shifted the PRNG sequence for every well generated AFTER
    the first one (their lat/lon, total_depth_md_m, trajectory stations --
    everything downstream of ANY shared-stream draw) even though
    `random.seed(42)` never changed. Caught by diffing a regenerated
    wells.json against git HEAD and finding total_depth_md_m/lat/lon values
    had shifted for wells that should have been untouched. Fixed by giving
    ALL new hazard-type logic (TORQUE_SPIKE's trajectory gate, the 3-way vs
    2-way clay/shale branch, OVERPRESSURE_ZONE's whole generation pass) its
    own dedicated random.Random() instance, seeded deterministically from
    well_id so results stay fully reproducible, but which cannot perturb the
    shared `random` module's state no matter how many draws it makes.
    """
    # Dedicated, isolated RNG for every NEW decision this extension adds --
    # never touches the shared `random` module used by the rest of this
    # function (and thus never shifts trajectory/well-coordinate generation
    # for subsequent wells). Seeded from well_id, not a shared counter, so
    # it's still fully deterministic across runs.
    extra_rng = random.Random(f"hazard-extension-{well_id}")

    events = []
    hazard_formations = [t for t in tops if t["formation_name"] in
                         {"Tipam Sandstone", "Barail Sandstone", "Kopili", "Sylhet Limestone", "Girujan Clay"}]

    num_incidents = random.randint(2, 6)
    used_depths = set()

    for _ in range(num_incidents):
        if not hazard_formations:
            break
        formation = random.choice(hazard_formations)
        depth = random.uniform(
            formation["top_md_m"] + 20,
            min(formation["base_md_m"] - 20, formation["top_md_m"] + 300)
        )
        depth = round(depth, 1)

        # Avoid duplicate depths
        if any(abs(depth - d) < 50 for d in used_depths):
            continue
        used_depths.add(depth)

        # Assign incident type weighted by formation -- UNCHANGED from the
        # original 4-hazard branch logic (same calls, same order) so the
        # shared `random` stream's draw sequence is identical to before this
        # extension for every well. New hazard types are decided using
        # extra_rng (isolated instance) AFTER the original choice is made,
        # and only override it -- this still consumes the same number of
        # shared-stream draws per iteration as the pre-extension code did.
        if "Clay" in formation["formation_name"] or "Shale" in formation["formation_name"]:
            incident_type = random.choice(["WELLBORE_INSTABILITY", "STUCK_PIPE"])
        elif "Limestone" in formation["formation_name"] or "Kopili" in formation["formation_name"]:
            incident_type = random.choice(["MUD_LOSS", "KICK"])
        else:
            incident_type = random.choice(["MUD_LOSS", "STUCK_PIPE", "KICK", "WELLBORE_INSTABILITY"])

        # New hazard overrides, decided from the ISOLATED rng only -- cannot
        # shift the shared stream regardless of how many draws happen here.
        if well_type != "Vertical" and extra_rng.random() < 0.20:
            incident_type = "TORQUE_SPIKE"
        elif incident_type == "WELLBORE_INSTABILITY" and extra_rng.random() < 0.30:
            incident_type = "CEMENTING_FAILURE"  # same washout-prone clay/shale formation, different manifestation

        npt_hr = round(random.uniform(1.5, 8.5), 1)
        severity = random.choice(SEVERITY_MAP[incident_type])
        mw = round(formation["pore_pressure_gradient_ppg"] + random.uniform(0.3, 0.8), 1)

        # Fill incident narrative
        templates = INCIDENT_TEMPLATES[incident_type]
        template = random.choice(templates)
        narrative = template.format(
            depth=depth,
            formation=formation["formation_name"],
            volume=round(random.uniform(20, 120), 0),
            pill_vol=round(random.uniform(20, 40), 0),
            pump_rate=random.choice([1200, 1400, 1550, 1650]),
            npt_hr=npt_hr,
            loss_rate=round(random.uniform(15, 80), 0),
            mw_hi=mw + 0.3,
            mw_lo=mw - 0.3,
            mw_new=round(mw + 0.4, 1),
            torque=round(random.uniform(15, 35), 0),
            overpull=round(random.uniform(30, 80), 0),
            pit_gain=round(random.uniform(5, 30), 0),
            sicp=random.randint(200, 800),
            sidpp=random.randint(150, 600),
            washout=round(random.uniform(15, 40), 0),
        )

        mitigations = {
            "MUD_LOSS": "Pumped LCM pill; reduced mud weight; staged cementing squeeze",
            "STUCK_PIPE": "Applied overpull + torque; spotted freeing agent; reciprocated string",
            "KICK": "Shut in BOP; applied Driller's Method; weighted up mud to kill weight",
            "WELLBORE_INSTABILITY": "Raised KCl inhibitor; increased mud weight; short trips for caliper",
            "TORQUE_SPIKE": "Reduced WOB/RPM; circulated bottoms-up to clear cuttings bed; reamed tight sections",
            "CEMENTING_FAILURE": "Ran cement bond log; performed remedial squeeze cementing",
        }

        outcome = {
            "MUD_LOSS": "Returns restored; resumed drilling",
            "STUCK_PIPE": "Pipe freed; cased off interval",
            "KICK": "Well killed successfully; drilling resumed",
            "WELLBORE_INSTABILITY": "Stabilized; casing run",
            "TORQUE_SPIKE": "Torque normalized; drilling resumed",
            "CEMENTING_FAILURE": "Bond restored via squeeze; casing integrity confirmed",
        }

        event = {
            "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
            "well_id": well_id,
            "event_type": incident_type,
            "severity": severity,
            "depth_start_md_m": depth,
            "depth_end_md_m": round(depth + random.uniform(5, 50), 1),
            "formation": formation["formation_name"],
            "raw_narrative": narrative,
            "npt_hours": npt_hr,
            "iadc_npt_code": IADC_NPT_CODES[incident_type],
            "loss_rate_bbl_hr": round(random.uniform(15, 80), 1) if incident_type == "MUD_LOSS" else None,
            "mitigation_description": mitigations[incident_type],
            "outcome": outcome[incident_type],
            "confidence": round(random.uniform(0.85, 0.99), 2),
            "source_document": f"DDR_{well_id}_{int(depth)}m.pdf",
            "source_page": random.randint(1, 8),
            "witsml_mapping": "opsReport.activity (WITSML 2.0)",
        }
        events.append(event)

    # OVERPRESSURE_ZONE: generated as a separate pass, not from the random-
    # depth-within-formation loop above, because this hazard is specifically
    # a TRANSITION phenomenon -- anchored to the top of a formation where
    # pore-pressure gradient steps up versus the formation above it (using
    # the real pp_gradient_ppg values already assigned per formation in
    # ASSAM_STRATIGRAPHY, not an invented pressure jump). Roughly 1 in 3
    # wells gets one -- not every formation transition is a real overpressure
    # event, so this isn't attached to every well indiscriminately.
    if len(tops) >= 2 and extra_rng.random() < 0.35:
        # pick a transition with a genuine gradient step-up (not the first
        # formation, which has nothing to transition from). Basement is
        # explicitly excluded -- crystalline basement has no reservoir pore
        # fluid (see its own "no reservoir" lithology note in
        # ASSAM_STRATIGRAPHY), so an "overpressure zone" there would be
        # geologically meaningless, not a real hazard. Found and fixed
        # during this same session after the first generation run produced
        # exactly this nonsensical case -- not assumed correct on the first try.
        # Every draw below uses extra_rng (isolated), not the shared `random`
        # module, so this whole pass cannot shift subsequent wells' data.
        step_up_candidates = [
            tops[i] for i in range(1, len(tops))
            if tops[i]["pore_pressure_gradient_ppg"] > tops[i - 1]["pore_pressure_gradient_ppg"] + 0.2
            and tops[i]["formation_name"] != "Basement"
        ]
        if step_up_candidates:
            formation = extra_rng.choice(step_up_candidates)
            depth = round(formation["top_md_m"] + extra_rng.uniform(5, 40), 1)
            if not any(abs(depth - d) < 50 for d in used_depths):
                npt_hr = round(extra_rng.uniform(1.5, 8.5), 1)
                severity = extra_rng.choice(SEVERITY_MAP["OVERPRESSURE_ZONE"])
                mw = round(formation["pore_pressure_gradient_ppg"] + extra_rng.uniform(0.3, 0.8), 1)
                template = extra_rng.choice(INCIDENT_TEMPLATES["OVERPRESSURE_ZONE"])
                narrative = template.format(
                    depth=depth, formation=formation["formation_name"],
                    npt_hr=npt_hr, mw_new=round(mw + 0.4, 1),
                )
                events.append({
                    "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
                    "well_id": well_id,
                    "event_type": "OVERPRESSURE_ZONE",
                    "severity": severity,
                    "depth_start_md_m": depth,
                    "depth_end_md_m": round(depth + extra_rng.uniform(5, 50), 1),
                    "formation": formation["formation_name"],
                    "raw_narrative": narrative,
                    "npt_hours": npt_hr,
                    "iadc_npt_code": IADC_NPT_CODES["OVERPRESSURE_ZONE"],
                    "loss_rate_bbl_hr": None,
                    "mitigation_description": "Weighted mud up ahead of transition; monitored d-exponent and connection gas trend",
                    "outcome": "Transition drilled safely at increased mud weight; no kick",
                    "confidence": round(extra_rng.uniform(0.85, 0.99), 2),
                    "source_document": f"DDR_{well_id}_{int(depth)}m.pdf",
                    "source_page": extra_rng.randint(1, 8),
                    "witsml_mapping": "opsReport.activity (WITSML 2.0)",
                })

    return events


def generate_telemetry_stream(
    well_id: str,
    start_depth_m: float,
    end_depth_m: float,
    rop_avg: float = 7.5,
    dt_sec: float = 1.0,
) -> list[dict]:
    """Generate synthetic 1-Hz drilling telemetry with anomaly injections."""
    records = []
    depth = start_depth_m
    t = datetime(2026, 9, 20, 6, 0, 0)  # Drill-out start time

    wob = 22.0
    rpm = 115.0
    torque = 18.5
    spp = 2800.0
    flow_in = 1450.0
    flow_out = 1450.0
    mud_weight = 10.2
    pit_volume = 320.0

    # Inject anomaly at ~70% depth
    anomaly_depth_trigger = start_depth_m + (end_depth_m - start_depth_m) * 0.70

    while depth < end_depth_m:
        # ROP varies
        rop = rop_avg + random.gauss(0, 1.5)
        depth_inc = (rop / 3600) * dt_sec
        depth += depth_inc

        # Normal operating noise
        wob = wob + random.gauss(0, 0.3)
        rpm = max(60, rpm + random.gauss(0, 2))
        torque = torque + random.gauss(0, 0.4)
        spp = spp + random.gauss(0, 30)
        flow_in = flow_in + random.gauss(0, 10)
        flow_out = flow_out + random.gauss(0, 10)
        pit_volume = pit_volume + random.gauss(0, 0.5)

        # Anomaly injection: mud loss signature
        if abs(depth - anomaly_depth_trigger) < 15:
            flow_out = max(0, flow_out - random.uniform(100, 300))
            pit_volume -= random.uniform(0.5, 2.0)
            spp = spp * random.uniform(0.88, 0.96)

        record = {
            "well_id": well_id,
            "timestamp": t.isoformat() + "Z",
            "depth_m": round(depth, 3),
            "rop_m_hr": round(max(0, rop), 2),
            "wob_klbs": round(max(0, wob), 2),
            "rpm": round(max(0, rpm), 1),
            "torque_kn_m": round(max(0, torque), 2),
            "standpipe_pressure_psi": round(max(0, spp), 1),
            "flow_in_lpm": round(max(0, flow_in), 1),
            "flow_out_lpm": round(max(0, flow_out), 1),
            "pit_volume_bbl": round(max(0, pit_volume), 2),
            "mud_weight_ppg": round(mud_weight + random.gauss(0, 0.01), 3),
            "d_exponent": round(max(0.5, 1.2 + random.gauss(0, 0.05)), 3),
        }
        records.append(record)
        t += timedelta(seconds=dt_sec)

        if len(records) >= 3600:  # Cap at 1 hour of data per well
            break

    return records


# ---------------------------------------------------------------------------
# Main Generator
# ---------------------------------------------------------------------------

def generate_all():
    print("=" * 60)
    print("  NWIS Assam-Arakan Basin Synthetic Testbed Generator")
    print("=" * 60)

    wells = []
    trajectories = []
    all_formation_tops = []
    all_events = []
    all_telemetry = []

    well_counter = 0
    for field in FIELDS:
        wells_in_field = 3 if field["field_code"] != "RPK" else 0
        for i in range(wells_in_field):
            well_counter += 1
            well_code = f"{field['field_code']}-{str(well_counter).zfill(3)}"
            well_id = f"WELL-{well_code}"
            well_type = random.choices(WELL_TYPES, weights=TRAJECTORY_WEIGHTS)[0]
            td = round(random.uniform(2800, 3600), 0)
            spud_year = random.randint(2015, 2024)

            # Surface coordinates (small random offset from field center)
            lat = field["lat"] + random.uniform(-0.08, 0.08)
            lon = field["lon"] + random.uniform(-0.08, 0.08)

            well = {
                "well_id": well_id,
                "well_name": well_code,
                "field": field["name"],
                "field_code": field["field_code"],
                "operator": random.choices(["OIL_INDIA_LIMITED", "ONGC"], weights=[0.85, 0.15])[0],
                "surface_lat": round(lat, 6),
                "surface_lon": round(lon, 6),
                "kb_elevation_m": round(random.uniform(90, 130), 1),
                "total_depth_md_m": td,
                "well_type": well_type,
                "spud_date": f"{spud_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "completion_date": f"{spud_year + random.randint(0,1)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
                "status": random.choice(["PRODUCING", "COMPLETED", "ABANDONED", "SUSPENDED"]),
                "witsml_uid": str(uuid.uuid4()),
            }
            wells.append(well)

            # Trajectory
            stations = generate_trajectory_stations(well_type, td)
            trajectories.append({
                "well_id": well_id,
                "well_name": well_code,
                "method": "MINIMUM_CURVATURE",
                "well_type": well_type,
                "stations": stations,
            })

            # Formation tops
            tvd_stations = stations
            tops = formation_tops_for_well(td, tvd_stations)
            for top in tops:
                top["well_id"] = well_id
                top["well_name"] = well_code
            all_formation_tops.extend(tops)

            # Drilling events
            events = generate_incidents_for_well(well_id, tops, well_type)
            all_events.extend(events)

            print(f"  Generated: {well_id} | {well_type} | TD={td:.0f}m | "
                  f"Tops={len(tops)} | Events={len(events)}")

    # Active well (the one currently drilling — for live telemetry)
    active_well = wells[-1]  # Use last well as "active"
    start_d = active_well["total_depth_md_m"] * 0.75
    end_d = active_well["total_depth_md_m"] * 0.92
    telemetry = generate_telemetry_stream(active_well["well_id"], start_d, end_d)

    telemetry_bundle = {
        "active_well_id": active_well["well_id"],
        "stream_type": "SIMULATED_REPLAY",
        "start_depth_m": start_d,
        "end_depth_m": end_d,
        "sample_rate_hz": 1.0,
        "total_records": len(telemetry),
        "records": telemetry,
    }

    # Save all files
    files = {
        "wells.json": wells,
        "trajectories.json": trajectories,
        "formation_tops.json": all_formation_tops,
        "drilling_events.json": all_events,
        "telemetry_stream.json": telemetry_bundle,
    }

    for fname, data in files.items():
        fpath = OUTPUT_DIR / fname
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        size_kb = fpath.stat().st_size / 1024
        print(f"  Saved: {fname} ({size_kb:.1f} KB)")

    print(f"\n  Total Wells:           {len(wells)}")
    print(f"  Total Formation Tops:  {len(all_formation_tops)}")
    print(f"  Total Drilling Events: {len(all_events)}")
    print(f"  Telemetry Records:     {len(telemetry)}")
    print("\n  Testbed generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    generate_all()
