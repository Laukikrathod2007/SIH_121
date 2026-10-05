"""
NWIS Module 02 — Master Data Store
In-memory singleton that loads and indexes all synthetic testbed data.
Provides fast lookup dicts for all engines.

Usage:
    from data_store import NWISDataStore
    store = NWISDataStore()  # Singleton — loads once
    wells = store.all_wells
"""

from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Optional

from loguru import logger

from app.modules.nwis.models.schemas import (
    Well, WellTrajectory, SurveyStation, FormationTop, DrillingEvent,
    TelemetryRecord, HazardType, WellType, WellStatus, CasingRecord
)

DATA_DIR = Path(__file__).parent / "data" / "synthetic"

# Real casing/cementing data (logger Step 20-23) -- genuinely real, from
# module 01's extraction of real Equinor Volve documents, kept as its own
# real_data/ file rather than merged into the synthetic testbed's
# Assam-Arakan wells, which it has nothing to do with. Casing programs are
# correlatable across whichever wells actually have real casing data (2
# real Volve wells currently), not fabricated for the synthetic ones.
REAL_CASING_DATA_PATH = Path(__file__).parent.parent.parent / "real_data" / "real_casing_records_all.json"
REAL_FORMATIONS_PATH = Path(__file__).parent.parent.parent / "real_data" / "real_formations_fresh.json"
REAL_EVENTS_PATH = Path(__file__).parent.parent.parent / "real_data" / "real_events_depth_tagged_fresh.json"
REAL_TRAJECTORIES_PATH = Path(__file__).parent.parent.parent / "real_data" / "real_trajectories_witsml.json"

# Real Volve wells added to the live analyze()-able well set (additive,
# alongside the synthetic Assam-Arakan testbed) so the live pipeline is
# genuinely real end-to-end, not just at the offline model-training stage:
# real formation tops, real events, real trajectory (computed via minimum
# curvature from real MD/Inc/Azi -- see real_data/extract_real_trajectories.py
# for why only those 3 columns are read directly off the survey report and
# everything else is computed, not guess-mapped from an ambiguous table).
# Real casing exists for F-12 only (loaded separately below, keyed by
# well_id already); F-1 has none in the extracted casing data -- correctly
# absent, not fabricated. Surface position and KB elevation are the real
# values read off each well's own WITSML/EDM survey report header (module 01
# extraction). total_depth_md_m uses each well's own real trajectory's
# deepest station, the most authoritative real value available.
REAL_WELL_F12 = Well(
    well_id="15/9-F-12", well_name="15/9-F-12", field="Volve",
    field_code="VOLVE", operator="Equinor", surface_lat=58.441613,
    surface_lon=1.887480, kb_elevation_m=54.90, total_depth_md_m=3520.0,
    well_type=WellType.J_TYPE, status=WellStatus.COMPLETED, witsml_uid="",
)
REAL_WELL_F1 = Well(
    well_id="15/9-F-1", well_name="15/9-F-1", field="Volve",
    field_code="VOLVE", operator="Equinor", surface_lat=58.441641,
    surface_lon=1.887419, kb_elevation_m=54.90, total_depth_md_m=3632.0,
    well_type=WellType.J_TYPE, status=WellStatus.COMPLETED, witsml_uid="",
)
REAL_WELLS = [REAL_WELL_F12, REAL_WELL_F1]
REAL_TRAJECTORY_KEY = {"15/9-F-12": "WELL-15_9-F-12", "15/9-F-1": "WELL-15_9-F-1"}


class NWISDataStore:
    """
    Singleton data store for all NWIS testbed data.
    Loaded once at startup; all engines query from this store.
    """
    _instance: Optional[NWISDataStore] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, data_dir: Path = DATA_DIR) -> None:
        if self._loaded:
            return

        logger.info(f"Loading NWIS testbed data from: {data_dir}")

        # Load wells
        wells_raw = self._read_json(data_dir / "wells.json", [])
        self.all_wells: List[Well] = []
        for w in wells_raw:
            try:
                well = Well(
                    well_id=w["well_id"],
                    well_name=w["well_name"],
                    field=w["field"],
                    field_code=w["field_code"],
                    operator=w["operator"],
                    surface_lat=w["surface_lat"],
                    surface_lon=w["surface_lon"],
                    kb_elevation_m=w.get("kb_elevation_m", 10.0),
                    total_depth_md_m=w["total_depth_md_m"],
                    well_type=WellType(w.get("well_type", "Vertical")),
                    spud_date=w.get("spud_date"),
                    completion_date=w.get("completion_date"),
                    status=WellStatus(w.get("status", "COMPLETED")),
                    witsml_uid=w.get("witsml_uid", ""),
                )
                self.all_wells.append(well)
            except Exception as e:
                logger.warning(f"Skipping well {w.get('well_id')}: {e}")

        self.wells_by_id: Dict[str, Well] = {w.well_id: w for w in self.all_wells}

        # Load trajectories
        trajs_raw = self._read_json(data_dir / "trajectories.json", [])
        self.all_trajectories: Dict[str, WellTrajectory] = {}
        for t in trajs_raw:
            try:
                stations = [SurveyStation(**s) for s in t.get("stations", [])]
                traj = WellTrajectory(
                    well_id=t["well_id"],
                    well_name=t["well_name"],
                    method=t.get("method", "MINIMUM_CURVATURE"),
                    well_type=WellType(t.get("well_type", "Vertical")),
                    stations=stations,
                )
                self.all_trajectories[t["well_id"]] = traj
            except Exception as e:
                logger.warning(f"Skipping trajectory {t.get('well_id')}: {e}")

        # Load formation tops
        tops_raw = self._read_json(data_dir / "formation_tops.json", [])
        self.formation_tops_by_well: Dict[str, List[FormationTop]] = {}
        for top in tops_raw:
            try:
                fm = FormationTop(**top)
                self.formation_tops_by_well.setdefault(fm.well_id, []).append(fm)
            except Exception as e:
                logger.warning(f"Skipping formation top: {e}")

        # Load drilling events
        events_raw = self._read_json(data_dir / "drilling_events.json", [])
        self.events_by_well: Dict[str, List[DrillingEvent]] = {}
        self.all_events: List[DrillingEvent] = []
        for ev in events_raw:
            try:
                event = DrillingEvent(
                    event_id=ev["event_id"],
                    well_id=ev["well_id"],
                    event_type=HazardType(ev["event_type"]),
                    severity=ev.get("severity", "MEDIUM"),
                    depth_start_md_m=ev["depth_start_md_m"],
                    depth_end_md_m=ev.get("depth_end_md_m"),
                    formation=ev.get("formation"),
                    raw_narrative=ev.get("raw_narrative", ""),
                    npt_hours=ev.get("npt_hours", 0.0),
                    iadc_npt_code=ev.get("iadc_npt_code"),
                    loss_rate_bbl_hr=ev.get("loss_rate_bbl_hr"),
                    mitigation_description=ev.get("mitigation_description"),
                    outcome=ev.get("outcome"),
                    confidence=ev.get("confidence", 0.90),
                    source_document=ev.get("source_document"),
                    source_page=ev.get("source_page"),
                    # This whole loop reads the project's own synthetic
                    # testbed fixture (drilling_events.json), never real
                    # OIL/Volve source documents -- honestly SYNTHETIC,
                    # matching the DB schema's own source_type vocabulary.
                    source_type="SYNTHETIC",
                )
                self.events_by_well.setdefault(event.well_id, []).append(event)
                self.all_events.append(event)
            except Exception as e:
                logger.warning(f"Skipping event {ev.get('event_id')}: {e}")

        # Load telemetry
        telemetry_raw = self._read_json(data_dir / "telemetry_stream.json", {})
        self.active_well_id: str = telemetry_raw.get("active_well_id", "")
        telemetry_records = telemetry_raw.get("records", [])
        self.telemetry_records: List[TelemetryRecord] = []
        self.telemetry_by_well: Dict[str, List[TelemetryRecord]] = {}
        skipped_telemetry = 0
        for rec in telemetry_records:
            try:
                if not rec.get("well_id") and self.active_well_id:
                    rec["well_id"] = self.active_well_id
                r = TelemetryRecord(**rec)
                self.telemetry_records.append(r)
                self.telemetry_by_well.setdefault(r.well_id, []).append(r)
            except Exception as e:
                skipped_telemetry += 1
                logger.debug(f"Skipping malformed telemetry record: {e}")
        if skipped_telemetry:
            # Was a bare `pass` — a bad telemetry file could silently lose
            # most/all of its records with zero visible signal at load time.
            logger.warning(f"Skipped {skipped_telemetry} malformed telemetry record(s) out of {len(telemetry_records)}")

        self.telemetry_by_depth: Dict[int, TelemetryRecord] = {
            int(r.depth_m): r for r in self.telemetry_records
        }

        # Real casing/cementing records (logger Step 20-23). Loaded from a
        # separate real_data/ path, not data/synthetic/ -- these are real
        # Volve wells the synthetic testbed knows nothing about, so this is
        # additive, not merged into the synthetic well set.
        casing_raw = self._read_json(REAL_CASING_DATA_PATH, [])
        self.casing_records_by_well: Dict[str, List[CasingRecord]] = {}
        for c in casing_raw:
            try:
                record = CasingRecord(
                    well_id=c["well_id"],
                    casing_size_inches=c.get("casing_size_inches"),
                    shoe_depth_md_m=c["shoe_depth_md_m"],
                    top_of_cement_md_m=c.get("top_of_cement_md_m"),
                )
                self.casing_records_by_well.setdefault(record.well_id, []).append(record)
            except Exception as e:
                logger.warning(f"Skipping casing record: {e}")

        # Real Volve wells -- additive to the synthetic set (see REAL_WELLS
        # comment above).
        for w in REAL_WELLS:
            self.all_wells.append(w)
            self.wells_by_id[w.well_id] = w

        # Real trajectory, computed via minimum curvature from real MD/Inc/Azi
        # (real_data/extract_real_trajectories.py). Only wells with a real
        # survey PDF are present in this file -- absent means genuinely no
        # real trajectory exists, not a loading failure.
        real_traj_raw = self._read_json(REAL_TRAJECTORIES_PATH, [])
        real_traj_by_key = {t["well_id"]: t for t in real_traj_raw}
        for w in REAL_WELLS:
            traj_key = REAL_TRAJECTORY_KEY.get(w.well_id)
            t = real_traj_by_key.get(traj_key) if traj_key else None
            if t is None:
                continue
            try:
                stations = [SurveyStation(**s) for s in t["stations"]]
                self.all_trajectories[w.well_id] = WellTrajectory(
                    well_id=w.well_id, well_name=w.well_name,
                    method=t.get("method", "MINIMUM_CURVATURE"),
                    well_type=w.well_type, stations=stations,
                )
            except Exception as e:
                logger.warning(f"Skipping real trajectory for {w.well_id}: {e}")

        # Real formation tops. Sanity-filtered against a generous absolute
        # depth bound (not each well's own total_depth_md_m, which is itself
        # only the deepest *surveyed* point and can legitimately be shallower
        # than a real deep formation top like F-12's Sleipner reservoir top):
        # module 01's COMPLETION.pdf table parser has a real,
        # previously-undetected bug that produces 6+ digit garbage depths
        # (e.g. "285220.0"m) for some rows -- likely column/page-number
        # bleed-through in that specific document type (see
        # tier3_entity_extractor.py's extract_formation_tops fix, logger Step
        # 25 -- that fix covers module 01's production Assam pipeline; this
        # file was produced by a separate, now-discarded reconnaissance
        # script that predates it, so the filter below remains the actual
        # enforcement point for this specific file's known-bad rows).
        VOLVE_MAX_PLAUSIBLE_DEPTH_M = 6000.0
        real_well_ids = {w.well_id for w in REAL_WELLS}
        real_tops_raw = self._read_json(REAL_FORMATIONS_PATH, [])
        n_tops_dropped = 0
        for t in real_tops_raw:
            if t.get("well_id") not in real_well_ids:
                continue
            if t["top_md_m"] is None or t["top_md_m"] > VOLVE_MAX_PLAUSIBLE_DEPTH_M:
                n_tops_dropped += 1
                continue
            fm = FormationTop(
                well_id=t["well_id"], well_name=t["well_id"],
                formation_name=t["formation_name"], top_md_m=t["top_md_m"],
                top_tvd_m=t["top_md_m"], base_md_m=t["top_md_m"] + 50,
                thickness_m=50.0,
            )
            self.formation_tops_by_well.setdefault(fm.well_id, []).append(fm)
        if n_tops_dropped:
            logger.warning(
                f"Dropped {n_tops_dropped} real formation tops exceeding "
                f"{VOLVE_MAX_PLAUSIBLE_DEPTH_M}m (known reconnaissance-script "
                f"parsing bug, not fabricated data being hidden)"
            )

        # Real drilling events. Only rows with a resolved hazard_type are
        # usable (module 01 tags some real events, e.g. EQUIPMENT_FAILURE,
        # as hazard_type=null because they don't map to a PS 26121 hazard
        # family -- correctly excluded here, not coerced into one).
        # Deduped on (well_id, event_type, depth): the same real event can
        # appear in more than one source document for the same well (e.g.
        # F-1's MUD_LOG.pdf and MUD_LOG_COMBINED.pdf both narrate the same
        # stuck-pipe incident) -- counting it twice would double-weight one
        # real occurrence as two in any downstream frequency-based scoring.
        real_events_raw = self._read_json(REAL_EVENTS_PATH, [])
        seen_events = set()
        n_events_deduped = 0
        for i, e in enumerate(real_events_raw):
            if e.get("well_id") not in real_well_ids or e.get("hazard_type") is None:
                continue
            dedupe_key = (e["well_id"], e["hazard_type"], e["depth_start_md_m"])
            if dedupe_key in seen_events:
                n_events_deduped += 1
                continue
            seen_events.add(dedupe_key)
            event = DrillingEvent(
                event_id=f"EVT-REAL-{i:03d}",
                well_id=e["well_id"],
                event_type=HazardType(e["hazard_type"]),
                severity=e.get("severity", "MEDIUM"),
                depth_start_md_m=e["depth_start_md_m"],
                source_document=e.get("source_file"),
                # Parsed from real source documents for the 2 real Volve
                # wells (see this loop's own docstring above) -- genuinely
                # REAL, not demonstration data.
                source_type="REAL",
            )
            self.events_by_well.setdefault(event.well_id, []).append(event)
            self.all_events.append(event)
        if n_events_deduped:
            logger.info(f"Deduped {n_events_deduped} real events repeated across source documents")

        self._loaded = True

        logger.success(
            f"NWIS store loaded: {len(self.all_wells)} wells | "
            f"{sum(len(v) for v in self.formation_tops_by_well.values())} tops | "
            f"{len(self.all_events)} events | "
            f"{len(self.telemetry_records)} telemetry records | "
            f"{sum(len(v) for v in self.casing_records_by_well.values())} real casing records "
            f"({len(self.casing_records_by_well)} real wells)"
        )

    def get_telemetry_at(
        self,
        depth_m: float,
        window: int = 120,
        well_id: Optional[str] = None,
    ) -> List[TelemetryRecord]:
        """Return up to `window` telemetry records near the given depth strictly for the specified well.

        Telemetry Attribution Contract:
        - When well_id is provided, ONLY telemetry records strictly belonging to that well are returned.
        - If the target well has no telemetry records in the store, returns an empty list.
          NEVER substitutes records from another well.
        - When well_id is omitted/None, scopes strictly to self.active_well_id. If self.active_well_id
          has no telemetry, returns an empty list.
        """
        target_well = well_id or self.active_well_id
        if not target_well:
            return []

        well_records = self.telemetry_by_well.get(target_well)
        if well_records is None:
            well_records = [r for r in self.telemetry_records if r.well_id == target_well]
            if well_records:
                self.telemetry_by_well[target_well] = well_records

        if not well_records:
            return []

        result = [r for r in well_records if r.depth_m <= depth_m]
        return result[-window:]

    def get_events_for_top_wells(
        self,
        top_well_ids: List[str],
    ) -> List[DrillingEvent]:
        """Get all events from a list of offset well IDs."""
        result = []
        for wid in top_well_ids:
            result.extend(self.events_by_well.get(wid, []))
        return result

    @staticmethod
    def _read_json(path: Path, default):
        if not path.exists():
            logger.warning(f"Data file missing: {path} — run generate_testbed.py first")
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_loaded(self) -> bool:
        return self._loaded

    def status(self) -> dict:
        return {
            "loaded": self._loaded,
            "wells": len(self.all_wells) if self._loaded else 0,
            "events": len(self.all_events) if self._loaded else 0,
            "telemetry_records": len(self.telemetry_records) if self._loaded else 0,
            "active_well_id": self.active_well_id if self._loaded else None,
        }
