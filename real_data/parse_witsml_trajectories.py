"""
Parse real WITSML 1.4.1.1 trajectory XML (real_data/witsml/*/*/trajectory/*.xml,
pulled from Equinor Volve's Databricks share) into modules/02_nwis_backend's
exact SurveyStation/WellTrajectory shape. Proper structured XML, not PDF
text-pattern matching -- <trajectoryStation> elements map directly to
SurveyStation fields (md/tvd/incl/azi/dispNs/dispEw), no heuristic column
inference needed.

Covers ~18 real Volve wells, vs. the 2 hand-picked via PDF parsing in
Step 17 -- broad enough for a real DORS ranking validation across many
offset-well candidates, not just a single pairwise comparison.
"""
from __future__ import annotations
import glob
import json
import os
import xml.etree.ElementTree as ET

NS = {"w": "http://www.witsml.org/schemas/1series"}
KB_ELEVATION_M = 54.90  # same rotary-table reference as Step 17's PDF-derived data


def parse_witsml_file(path: str) -> dict | None:
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return None
    root = tree.getroot()
    traj_el = root.find("w:trajectory", NS)
    if traj_el is None:
        return None

    well_name = (traj_el.findtext("w:nameWell", default="", namespaces=NS) or "").strip()
    if not well_name:
        return None

    stations = []
    for st in traj_el.findall("w:trajectoryStation", NS):
        def f(tag):
            el = st.find(f"w:{tag}", NS)
            return float(el.text) if el is not None and el.text else None
        md, tvd, incl, azi = f("md"), f("tvd"), f("incl"), f("azi")
        ns, ew = f("dispNs"), f("dispEw")
        if None in (md, tvd, incl, azi):
            continue
        stations.append({
            "md_m": md, "inclination_deg": incl, "azimuth_deg": azi % 360,
            "tvd_m": tvd, "ns_m": ns or 0.0, "ew_m": ew or 0.0,
            "tvdss_m": round(tvd - KB_ELEVATION_M, 2),
        })

    if len(stations) < 3:
        return None
    stations.sort(key=lambda s: s["md_m"])
    # De-duplicate stations at the same MD (multiple trajectory XML files per
    # wellbore are different survey RUNS over overlapping depth ranges, not
    # a single continuous log) -- keep the first occurrence at each MD.
    seen_md, deduped = set(), []
    for s in stations:
        if s["md_m"] in seen_md:
            continue
        seen_md.add(s["md_m"])
        deduped.append(s)

    return {"well_name": well_name, "stations": deduped, "n_raw_files_contributed": 1}


def main():
    wells: dict[str, dict] = {}
    for well_dir in sorted(glob.glob("real_data/witsml/*")):
        for xml_path in glob.glob(os.path.join(well_dir, "*", "trajectory", "*.xml")):
            parsed = parse_witsml_file(xml_path)
            if parsed is None:
                continue
            wn = parsed["well_name"]
            if wn not in wells:
                wells[wn] = {"well_id": f"WELL-{wn.replace('/', '_')}", "well_name": wn,
                             "method": "MINIMUM_CURVATURE", "well_type": "J-Type", "stations": []}
            # Merge stations across multiple XML files for the same well (different
            # survey runs), then re-sort/de-dup by MD at the end.
            wells[wn]["stations"].extend(parsed["stations"])

    result = []
    for wn, w in wells.items():
        w["stations"].sort(key=lambda s: s["md_m"])
        seen, deduped = set(), []
        for s in w["stations"]:
            if s["md_m"] in seen:
                continue
            seen.add(s["md_m"])
            deduped.append(s)
        if len(deduped) < 5:
            continue
        w["stations"] = deduped
        result.append(w)
        print(f"{w['well_id']:25s} {len(deduped):4d} stations, MD {deduped[0]['md_m']:.1f} -> {deduped[-1]['md_m']:.1f}m")

    print(f"\n{len(result)} real wells with usable trajectory data")
    with open("real_data/real_trajectories_witsml.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print("Saved real_data/real_trajectories_witsml.json")


if __name__ == "__main__":
    main()
