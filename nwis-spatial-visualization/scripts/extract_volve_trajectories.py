#!/usr/bin/env python3
"""Extract traceable survey trajectories from an official Equinor Volve export.

The input must be an already-downloaded/unpacked official Volve WITSML dataset.
The script deliberately does not fetch data, infer well identity from filenames,
or turn drilling/log samples into a trajectory. It accepts exact primary-bore
WITSML wellbore names for a small allowlist and writes only surveys containing
at least two stations with source-provided MD/TVD/NS/EW in metres.

Example (after downloading the official dataset from Equinor's Databricks
Marketplace listing):
  python scripts/extract_volve_trajectories.py \
    --input "D:/datasets/Volve Data Village" --official-dataset

The explicit flag is an operator attestation; the script cannot independently
prove the provenance of arbitrary files on disk. Do not use it for public-mirror
files, tests, fixtures, or the real-time depth/time CSVs.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


WITSML_NS = "http://www.witsml.org/schemas/1series"
TARGET_WELLS = (
    "15/9-F-12",
    "15/9-F-1",
    "15/9-F-14",
    "15/9-F-4",
    "15/9-F-5",
    "15/9-F-9",
)
TARGET_KEYS = {re.sub(r"[^A-Z0-9]", "", well.upper()): well for well in TARGET_WELLS}
MAIN_BORE = re.compile(r"\s*-\s*Main Wellbore\s*$", re.IGNORECASE)
COUNTRY_PREFIX = re.compile(r"^\s*NO\s+", re.IGNORECASE)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element if local_name(item.tag) == name), None)


def text_value(element: ET.Element, name: str) -> str | None:
    item = child(element, name)
    return item.text.strip() if item is not None and item.text and item.text.strip() else None


def numeric(element: ET.Element, name: str, expected_uom: str | None = None) -> float | None:
    item = child(element, name)
    if item is None or item.text is None:
        return None
    if expected_uom is not None and item.get("uom") != expected_uom:
        return None
    try:
        result = float(item.text)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def canonical_well_name(raw: str) -> str | None:
    cleaned = MAIN_BORE.sub("", raw.strip())
    cleaned = COUNTRY_PREFIX.sub("", cleaned)
    key = re.sub(r"[^A-Z0-9]", "", cleaned.upper())
    return TARGET_KEYS.get(key)


def first_text(element: ET.Element, candidates: tuple[str, ...]) -> str | None:
    for name in candidates:
        value = text_value(element, name)
        if value:
            return value
    return None


def parse_station(station: ET.Element) -> dict[str, float | None] | None:
    # Preserve the source values. Units must be explicit metres; no silent
    # unit conversions are permitted in this extraction step.
    md = numeric(station, "md", "m")
    tvd = numeric(station, "tvd", "m")
    ns = numeric(station, "dispNs", "m")
    ew = numeric(station, "dispEw", "m")
    if None in (md, tvd, ns, ew):
        return None

    incl_item = child(station, "incl")
    azi_item = child(station, "azi")
    incl = numeric(station, "incl")
    azi = numeric(station, "azi")
    if incl is not None and incl_item is not None:
        if incl_item.get("uom") == "rad":
            incl = math.degrees(incl)
        elif incl_item.get("uom") != "dega":
            incl = None
    if azi is not None and azi_item is not None:
        if azi_item.get("uom") == "rad":
            azi = math.degrees(azi)
        elif azi_item.get("uom") != "dega":
            azi = None

    tvdss = numeric(station, "tvdss", "m")
    if tvdss is None:
        tvdss = numeric(station, "tvdSs", "m")
    return {
        "md_m": md,
        "inclination_deg": incl,
        "azimuth_deg": azi,
        "tvd_m": tvd,
        "ns_m": ns,
        "ew_m": ew,
        "tvdss_m": tvdss,
    }


def trajectory_records(path: Path, root: Path) -> list[dict[str, Any]]:
    try:
        document = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        print(f"SKIP {path}: {error}", file=sys.stderr)
        return []

    records = []
    for trajectory in document.iter():
        if local_name(trajectory.tag) != "trajectory":
            continue
        raw_name = first_text(trajectory, ("nameWellbore",))
        if not raw_name:
            continue
        well_id = canonical_well_name(raw_name)
        if not well_id:
            continue
        stations = []
        for station in trajectory:
            if local_name(station.tag) != "trajectoryStation":
                continue
            parsed = parse_station(station)
            if parsed is not None:
                stations.append(parsed)
        stations.sort(key=lambda record: record["md_m"] or 0)
        # Duplicate MD values do not constitute distinct stations.
        unique: dict[float, dict[str, float | None]] = {}
        for station in stations:
            unique[float(station["md_m"])] = station
        stations = [unique[key] for key in sorted(unique)]
        if len(stations) < 2:
            print(f"SKIP {path} / {raw_name}: fewer than two complete metre survey stations", file=sys.stderr)
            continue

        azi_ref = first_text(trajectory, ("aziRef", "azimuthReference"))
        source_rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        records.append({
            "well_id": well_id,
            "raw_wellbore_name": raw_name,
            "stations": stations,
            "source_file": source_rel,
            "azimuth_reference": azi_ref,
        })
    return records


def file_slug(well_id: str) -> str:
    return well_id.replace("/", "_").replace(" ", "_")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="directory or a single official WITSML XML file")
    parser.add_argument("--output", type=Path, default=Path("public/data/trajectories"), help="output directory (default: public/data/trajectories)")
    parser.add_argument("--official-dataset", action="store_true", help="attest that input came from Equinor's official Volve Data Village distribution")
    args = parser.parse_args()
    if not args.official_dataset:
        parser.error("refusing extraction without --official-dataset; use only for a downloaded official Equinor Volve dataset")
    source = args.input.expanduser().resolve()
    if not source.exists():
        parser.error(f"input does not exist: {source}")
    root = source if source.is_dir() else source.parent
    files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() == ".xml")
    if source.is_file() and source.suffix.lower() != ".xml":
        parser.error("input file must be WITSML XML; depth/time logs and production data are not trajectory sources")
    if not files:
        print(f"No WITSML XML files found under {source}. No trajectory files created.")
        print("Download/unpack the official Equinor Volve Data Village dataset, including its WITSML trajectory/survey XML group.")
        return 0

    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in files:
        for record in trajectory_records(path, root):
            candidates[record["well_id"]].append(record)

    args.output.mkdir(parents=True, exist_ok=True)
    report = []
    for well_id in TARGET_WELLS:
        rows = candidates.get(well_id, [])
        # Do not guess which trajectory is canonical if multiple different
        # primary-bore survey records are present. Exact duplicates are safe.
        signatures = {json.dumps(row["stations"], sort_keys=True) for row in rows}
        if not rows:
            report.append({"well_id": well_id, "status": "unavailable", "reason": "no matching official WITSML primary-bore survey found"})
            continue
        if len(signatures) != 1:
            report.append({"well_id": well_id, "status": "ambiguous", "reason": "multiple non-identical primary-bore trajectory records; no file written", "source_files": [row["source_file"] for row in rows]})
            continue

        record = max(rows, key=lambda row: (len(row["stations"]), row["stations"][-1]["md_m"] or 0))
        payload = {
            "well_id": well_id,
            "name": well_id,
            "source": "Equinor Volve",
            "source_provenance": "Official Equinor Volve Data Village distribution; operator-attested at extraction time",
            "source_file": record["source_file"],
            "raw_wellbore_name": record["raw_wellbore_name"],
            "azimuth_reference": record["azimuth_reference"],
            "calculation_method": "Source-provided WITSML MD/TVD/dispNs/dispEw survey coordinates; no trajectory reconstruction",
            "computed_fields": [],
            "stations": record["stations"],
        }
        target = args.output / f"{file_slug(well_id)}.json"
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        report.append({
            "well_id": well_id,
            "status": "written",
            "stations": len(record["stations"]),
            "minimum_md_m": record["stations"][0]["md_m"],
            "maximum_md_m": record["stations"][-1]["md_m"],
            "trajectory_source_file": record["source_file"],
            "azimuth_reference": record["azimuth_reference"],
            "calculation_method": payload["calculation_method"],
            "output_file": str(target),
        })

    print(json.dumps({"input": str(source), "xml_files_scanned": len(files), "results": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
