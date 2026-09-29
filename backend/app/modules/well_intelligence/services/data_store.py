"""
NWIS Module 02 — Master Data Store
In-memory singleton that loads and indexes all synthetic testbed data.
Provides fast lookup dicts for all engines.

Usage:
    from app.modules.well_intelligence.services.data_store import NWISDataStore
    store = NWISDataStore()  # Singleton — loads once
    wells = store.all_wells
"""

from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from typing import List, Dict, Optional

from app.core.logging import logger
from app.config import settings

from app.modules.well_intelligence.models.schemas import (
    Well, WellTrajectory, SurveyStation, FormationTop, DrillingEvent,
    TelemetryRecord, HazardType, WellType, WellStatus
)

DATA_DIR = settings.SYNTHETIC_DATA_DIR


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
                    depth_tvdss_m=ev.get("depth_tvdss_m"),
                    formation=ev.get("formation"),
                    raw_narrative=ev.get("raw_narrative", ""),
                    npt_hours=ev.get("npt_hours", 0.0),
                    iadc_npt_code=ev.get("iadc_npt_code"),
                    loss_rate_bbl_hr=ev.get("loss_rate_bbl_hr"),
                    mitigation_description=ev.get("mitigation_description"),
                    outcome=ev.get("outcome"),
                    confidence=ev.get("confidence", 0.90),
                    provenance_tier=ev.get("provenance_tier", "OBSERVED"),
                    source_document=ev.get("source_document"),
                    source_page=ev.get("source_page"),
                    bbox=ev.get("bbox"),
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
        skipped_telemetry = 0
        for rec in telemetry_records:
            try:
                self.telemetry_records.append(TelemetryRecord(**rec))
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

        self._loaded = True

        logger.success(
            f"NWIS store loaded: {len(self.all_wells)} wells | "
            f"{sum(len(v) for v in self.formation_tops_by_well.values())} tops | "
            f"{len(self.all_events)} events | "
            f"{len(self.telemetry_records)} telemetry records"
        )

    def get_telemetry_at(self, depth_m: float, window: int = 120) -> List[TelemetryRecord]:
        """Return up to `window` telemetry records near the given depth."""
        result = [r for r in self.telemetry_records if r.depth_m <= depth_m]
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

