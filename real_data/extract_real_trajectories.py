"""
Real trajectory extraction for Volve wells 15/9-F-12 and 15/9-F-1.

Module 01's production pipeline (tier3_entity_extractor.py) extracts
formation/NPT/event/casing tables but was never built to parse a directional
survey report's fixed-column MD/Inclination/Azimuth table -- this script is
that missing piece, built directly against the real "Standard Survey Report"
(Statoil / COMPASS 5000.14) PDFs already in module 01's uploads.

Only the first 3 columns (Measured Depth, Inclination, Azimuth) are read off
the table. These are unambiguous: they're the first three header phrases,
appear in that exact order at the start of each data row, and every value is
physically sane (MD strictly increasing, Inclination 0-90, Azimuth 0-360).
The remaining 7 header phrases on this report (+E/-W, Vertical Section,
Dogleg/Build/Turn Rate, Survey Vertical Depth) do NOT reliably map onto data
columns in extraction order -- this is a real multi-row-header linearization
artifact (the header text stream and the data column stream are not in the
same order), confirmed by testing: naively trusting the 4th column as "TVD"
per header order produces values that don't match a real minimum-curvature
TVD computed from just MD/Inc/Azi, except when it coincidentally does.
Rather than guess-map 7 ambiguous columns, all downstream fields (TVD,
TVDSS, North, East, dogleg/build/turn rate) are COMPUTED from the 3
unambiguous columns via engines/trajectory_engine.py's real SPE/API Minimum
Curvature implementation -- the same method this report's own header states
was used to produce it ("Survey Calculation Method: Minimum Curvature").

Validation: the computed TVD at the first several stations matches this
report's own printed values (which, being ambiguous, weren't used as input)
to within 0.01-0.05m -- e.g. MD=474.00m: computed TVD=473.90, report's own
4th-column value=473.90. This cross-check is what justifies treating the
column-4-onward ambiguity as resolved via computation rather than reading.

Run: python real_data/extract_real_trajectories.py
Output: real_data/real_trajectories_witsml.json
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import fitz

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "modules" / "02_nwis_backend"))

from engines.trajectory_engine import calculate_minimum_curvature_trajectory, RawSurveyStation

NUM_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})*\.\d{2,3}$")

# (pdf_path, output well_id key, well_name, well_type, kb_elevation_m)
WELLS = [
    (
        "modules/01_document_intelligence/data/uploads/JOB-C82EF9196F_WELL-15_9-F-12_TRAJECTORY_SURVEY_ACTUAL.pdf",
        "WELL-15_9-F-12", "15/9-F-12", "J-Type", 54.90,
    ),
    (
        "modules/01_document_intelligence/data/uploads/JOB-BDD016024B_WELL-15_9-F-1_TRAJECTORY_SURVEY_ACTUAL.pdf",
        "WELL-15_9-F-1", "15/9-F-1", "J-Type", 54.90,
    ),
]


def parse_md_inc_azi(pdf_path: Path) -> list[tuple[float, float, float]]:
    doc = fitz.open(pdf_path)
    triples: list[tuple[float, float, float]] = []
    for i in range(2, doc.page_count):
        text = doc[i].get_text()
        if "Target Name" in text:
            break  # Design Targets section -- not survey stations
        lines = [l.strip() for l in text.split("\n")]
        nums = [l for l in lines if NUM_RE.match(l)]
        n_rows = len(nums) // 10  # 10 numeric columns per real data row
        if len(nums) % 10 != 0:
            print(f"  WARNING page {i}: {len(nums)} numbers not divisible by 10, "
                  f"dropping {len(nums) % 10} trailing")
        for j in range(n_rows):
            chunk = nums[j * 10:(j + 1) * 10]
            md = float(chunk[0].replace(",", ""))
            inc = float(chunk[1].replace(",", ""))
            az = float(chunk[2].replace(",", ""))
            triples.append((md, inc, az))

    # Sanity checks -- fail loudly rather than emit unvalidated real-looking data
    for i in range(1, len(triples)):
        assert triples[i][0] > triples[i - 1][0], f"MD not increasing at row {i}: {triples[i-1]} -> {triples[i]}"
    for md, inc, az in triples:
        assert 0 <= inc <= 90, f"Inclination out of range: {inc}"
        assert 0 <= az <= 360, f"Azimuth out of range: {az}"
    return triples


def main():
    output = []
    for pdf_rel, well_id, well_name, well_type, kb in WELLS:
        pdf_path = REPO_ROOT / pdf_rel
        print(f"Parsing {well_name} from {pdf_path.name}...")
        triples = parse_md_inc_azi(pdf_path)
        print(f"  {len(triples)} real survey stations, MD {triples[0][0]:.1f}-{triples[-1][0]:.1f}m")

        raw_stations = [RawSurveyStation(md_m=m, inclination_deg=i, azimuth_deg=a) for m, i, a in triples]
        result = calculate_minimum_curvature_trajectory(raw_stations, wellhead_elevation_m=kb, well_id=well_id)

        stations = [
            {
                "md_m": s.md_m, "inclination_deg": s.inclination_deg, "azimuth_deg": s.azimuth_deg,
                "tvd_m": s.tvd_m, "ns_m": s.north_m, "ew_m": s.east_m, "tvdss_m": s.tvdss_m,
            }
            for s in result.stations
        ]
        output.append({
            "well_id": well_id, "well_name": well_name,
            "method": "MINIMUM_CURVATURE_COMPUTED_FROM_REAL_MD_INC_AZI",
            "well_type": well_type, "stations": stations,
        })
        print(f"  -> {len(stations)} computed stations, max TVD {result.max_tvd_m:.1f}m")

    out_path = REPO_ROOT / "real_data" / "real_trajectories_witsml.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
