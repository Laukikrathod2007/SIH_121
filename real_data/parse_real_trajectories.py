"""
Parse real MD/Inc/Azi/TVD survey stations out of Equinor Volve's actual
COMPASS directional-survey PDF reports (real_data/volve/*_TRAJECTORY_SURVEY_ACTUAL.pdf)
into modules/02_nwis_backend's exact SurveyStation/WellTrajectory shape, for
real-data validation of the stratigraphic correlator and DORS trajectory
scoring (logger Step 17).

Column order inferred from the actual numeric data pattern, not the header
text (PyMuPDF's text extraction does not preserve the header's visual
left-right table alignment): MD, INC, AZI, TVD, NS, EW, VS, DLS, BUILD, TURN
-- verified against known physics (TVD ~= MD at low inclination near
surface; TVD < MD once inclined) before trusting it, not assumed.
"""
from __future__ import annotations
import json
import re
import fitz

KB_ELEVATION_M = 54.90  # "Rotary Table @ 54.90m" -- same for both wells, read from the PDF header text itself


def parse_trajectory_pdf(path: str, well_id: str, well_name: str) -> dict:
    doc = fitz.open(path)
    full_text = "\n".join(page.get_text("text") for page in doc)

    # Real survey data rows are 10 whitespace/newline-separated numeric
    # tokens in a row (comma-thousands, optional leading minus, optional
    # decimal). Reject rows that don't parse as exactly 10 floats.
    number_re = re.compile(r"-?[\d,]+\.\d+")
    lines = full_text.split("\n")
    numbers_seq = [n for n in (line.strip() for line in lines) if number_re.fullmatch(n)]

    # First pass: naive 10-number chunking produced real rows interleaved
    # with false positives from unrelated header numeric blocks ("Tie On
    # Depth: 145.90", magnetic model data, etc.) -- e.g. inclination=150.15
    # and md_m=0.0-with-nonzero-tvd both appeared, physically impossible for
    # this well profile. Found by inspecting the actual output, not assumed
    # correct after the first parse. A real survey table's one universal,
    # cheap-to-check invariant: MD is always strictly increasing row to row.
    # Enforce that instead of trusting every 10-number window.
    stations = []
    last_md = -1.0
    i = 0
    while i + 10 <= len(numbers_seq):
        chunk = numbers_seq[i:i + 10]
        try:
            vals = [float(v.replace(",", "")) for v in chunk]
        except ValueError:
            i += 1
            continue
        md, inc, azi, tvd, ns, ew, vs, dls, build, turn = vals
        valid = (
            last_md < md <= 10000 and 0 <= inc <= 100 and 0 <= azi <= 360
            and 0 <= tvd <= md + 1
        )
        if valid:
            stations.append({
                "md_m": md, "inclination_deg": inc, "azimuth_deg": azi,
                "tvd_m": tvd, "ns_m": ns, "ew_m": ew,
                "tvdss_m": round(tvd - KB_ELEVATION_M, 2),
            })
            last_md = md
            i += 10
        else:
            i += 1

    stations.sort(key=lambda s: s["md_m"])

    # Post-filter: one remaining artifact found by inspection -- a station
    # whose ns_m/ew_m jumps implausibly relative to both neighbors (a
    # tie-on-point parsing collision), physically impossible at real dogleg
    # severities over a normal station spacing. Drop rather than silently
    # keep a station known to be wrong.
    if len(stations) >= 3:
        s0, s1, s2 = stations[0], stations[1], stations[2]
        jump01 = abs(s1["ew_m"] - s0["ew_m"]) + abs(s1["ns_m"] - s0["ns_m"])
        jump12 = abs(s2["ew_m"] - s1["ew_m"]) + abs(s2["ns_m"] - s1["ns_m"])
        if jump01 > 200 and jump12 < 50:
            stations = stations[1:]  # first station is the tie-on-collision artifact

    cleaned = []
    for idx, s in enumerate(stations):
        if 0 < idx < len(stations) - 1:
            prev_s, next_s = stations[idx - 1], stations[idx + 1]
            jump_prev = abs(s["ew_m"] - prev_s["ew_m"]) + abs(s["ns_m"] - prev_s["ns_m"])
            jump_next = abs(next_s["ew_m"] - s["ew_m"]) + abs(next_s["ns_m"] - s["ns_m"])
            neighbor_jump = abs(next_s["ew_m"] - prev_s["ew_m"]) + abs(next_s["ns_m"] - prev_s["ns_m"])
            if jump_prev > 200 and jump_next > 200 and neighbor_jump < 50:
                continue  # this station is the outlier, not its neighbors
        cleaned.append(s)

    return {
        "well_id": well_id, "well_name": well_name,
        "method": "MINIMUM_CURVATURE", "well_type": "J-Type",
        "stations": cleaned,
    }


if __name__ == "__main__":
    trajectories = [
        parse_trajectory_pdf("real_data/volve/WELL-15_9-F-1_TRAJECTORY_SURVEY_ACTUAL.pdf", "WELL-15_9-F-1", "15/9-F-1"),
        parse_trajectory_pdf("real_data/volve/WELL-15_9-F-12_TRAJECTORY_SURVEY_ACTUAL.pdf", "WELL-15_9-F-12", "15/9-F-12"),
    ]
    for t in trajectories:
        n = len(t["stations"])
        print(f"{t['well_id']}: {n} stations, MD {t['stations'][0]['md_m'] if n else '-'} -> {t['stations'][-1]['md_m'] if n else '-'}")
    with open("real_data/real_trajectories.json", "w", encoding="utf-8") as f:
        json.dump(trajectories, f, indent=2)
    print("Saved real_data/real_trajectories.json")
