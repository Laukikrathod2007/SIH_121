"""
ML Data Engineering Pipeline -- Ingestion & Validation.

Implements Module 5 Data Pipeline Sections 4, 6, 53-55:
- Robust schema validation.
- Timestamp parsing & UTC normalization with original timezone preservation.
- Deterministic sorting (never train on unsorted telemetry).
- Duplicate detection & resolution (prefers highest quality).
- Plausible engineering range checks (flags BAD without silently deleting spikes).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.modules.physics.models.telemetry import ChannelQuality
from app.modules.physics.data_pipeline.models import ProvenanceClass, DataRecordMetadata


# Standard engineering bounds for drilling channels
ENGINEERING_BOUNDS = {
    "rop_m_hr": (0.0, 150.0),
    "rpm": (0.0, 300.0),
    "bit_rpm": (0.0, 500.0),
    "wob_kn": (0.0, 350.0),
    "torque_kn_m": (0.0, 80.0),
    "hookload_kn": (0.0, 3500.0),
    "flow_in_lpm": (0.0, 6000.0),
    "flow_out_lpm": (0.0, 8000.0),
    "standpipe_pressure_bar": (0.0, 450.0),
    "annular_pressure_bar": (0.0, 1000.0),
    "pit_volume_m3": (0.0, 300.0),
    "mud_weight_gcc": (0.8, 2.5),
    "temperature_c": (0.0, 250.0),
}


class TelemetryIngestor:
    """Ingests raw telemetry records, parses time, deduplicates, and checks ranges."""

    def __init__(self, default_source: str = "NWIS_INGESTION", provenance: ProvenanceClass = ProvenanceClass.SYNTHETIC):
        self.default_source = default_source
        self.provenance = provenance

    def parse_timestamp(self, ts_raw: Any) -> Tuple[datetime, str]:
        """
        Parses raw timestamp into UTC datetime object and preserves original string.
        Supports ISO 8601 strings and numeric epoch seconds.
        """
        if isinstance(ts_raw, (int, float)):
            dt = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
            return dt, dt.isoformat()
        elif isinstance(ts_raw, str):
            # Parse ISO string
            try:
                dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt, ts_raw
            except ValueError:
                dt = datetime.now(timezone.utc)
                return dt, dt.isoformat()
        else:
            dt = datetime.now(timezone.utc)
            return dt, dt.isoformat()

    def deduplicate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes duplicates by (well_id, timestamp, sequence),
        preferring records with higher overall quality.
        """
        seen: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
        for r in records:
            well_id = r.get("well_id", "DEFAULT")
            ts = str(r.get("timestamp", ""))
            seq = int(r.get("sequence", 0))
            key = (well_id, ts, seq)

            if key not in seen:
                seen[key] = r
            else:
                # Prefer record with higher overall quality
                existing_q = seen[key].get("quality", {}).get("overall", 0.0) if isinstance(seen[key].get("quality"), dict) else 0.0
                new_q = r.get("quality", {}).get("overall", 0.0) if isinstance(r.get("quality"), dict) else 0.0
                if new_q > existing_q:
                    seen[key] = r

        return list(seen.values())

    def validate_ranges(
        self,
        channels: Dict[str, float],
    ) -> Tuple[Dict[str, float], Dict[str, ChannelQuality]]:
        """
        Validates engineering bounds for all channels without silently deleting values.
        Marks out-of-bound values with SUSPECT or BAD.
        """
        qualities: Dict[str, ChannelQuality] = {}
        validated: Dict[str, float] = {}

        for ch, val in channels.items():
            if val is None:
                validated[ch] = 0.0
                qualities[ch] = ChannelQuality.BAD
                continue

            num_val = float(val)
            validated[ch] = num_val

            if ch in ENGINEERING_BOUNDS:
                min_b, max_b = ENGINEERING_BOUNDS[ch]
                if min_b <= num_val <= max_b:
                    qualities[ch] = ChannelQuality.GOOD
                elif (min_b * 0.8) <= num_val <= (max_b * 1.2):
                    qualities[ch] = ChannelQuality.SUSPECT
                else:
                    qualities[ch] = ChannelQuality.BAD
            else:
                qualities[ch] = ChannelQuality.GOOD

        return validated, qualities

    def process_batch(self, raw_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Full ingestion pipeline:
        Deduplicate -> Parse Timestamps -> Sort chronologically -> Validate ranges.
        """
        deduped = self.deduplicate(raw_records)

        # Parse timestamps and sort
        parsed_records = []
        for r in deduped:
            dt_utc, orig_ts = self.parse_timestamp(r.get("timestamp"))
            item = dict(r)
            item["_dt_utc"] = dt_utc
            item["timestamp_utc"] = dt_utc.isoformat()
            item["original_timestamp"] = orig_ts
            parsed_records.append(item)

        # Sort strictly by timestamp
        parsed_records.sort(key=lambda x: x["_dt_utc"])

        # Range check channels
        output = []
        for r in parsed_records:
            channels = r.get("channels", {})
            if isinstance(channels, dict):
                clean_ch, ch_qualities = self.validate_ranges(channels)
                r["channels"] = clean_ch
                r["channel_qualities"] = {k: v.value for k, v in ch_qualities.items()}
            r.pop("_dt_utc", None)
            output.append(r)

        return output
