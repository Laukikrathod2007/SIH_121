"""
Generate the source DDR / WCR PDFs that the demo dataset cites.

Every drilling event in the testbed carries `source_document` + `source_page`
(provenance). In demo mode those documents did not exist, so evidence links
were dead. This script renders one Daily Drilling Report per cited document —
the incident narrative, mitigation and outcome printed on exactly the cited
page — plus one Well Completion Report per well (casing + mud program), into
app/data/source_documents/. The evidence endpoint serves them, so
"alert -> event -> source page" resolves to a real file.

When real OIL DDRs/WCRs are connected, point settings.SOURCE_DOCS_DIR at the
archive instead; nothing else changes.

Run:  python generate_source_documents.py
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "source_documents"

PAGE_W, PAGE_H = 595, 842  # A4 points
MARGIN = 50
INK = (0.12, 0.14, 0.17)
MUTED = (0.42, 0.45, 0.5)
ACCENT = (0.75, 0.33, 0.05)


def _header(page: fitz.Page, title: str, subtitle: str, page_no: int, total: int) -> float:
    page.insert_text((MARGIN, 58), "OIL INDIA LIMITED — Drilling Department, Duliajan", fontsize=8, color=MUTED)
    page.insert_text((MARGIN, 84), title, fontsize=15, color=INK, fontname="helv")
    page.insert_text((MARGIN, 102), subtitle, fontsize=9, color=MUTED)
    page.draw_line((MARGIN, 112), (PAGE_W - MARGIN, 112), color=(0.8, 0.8, 0.8), width=0.6)
    page.insert_text((PAGE_W - MARGIN - 60, PAGE_H - 30), f"Page {page_no} of {total}", fontsize=8, color=MUTED)
    page.insert_text((MARGIN, PAGE_H - 30), "SYNTHETIC DEMO DOCUMENT — NWIS testbed", fontsize=7, color=MUTED)
    return 136.0


def _para(page: fitz.Page, y: float, label: str, text: str, color=INK) -> float:
    page.insert_text((MARGIN, y), label.upper(), fontsize=7.5, color=MUTED)
    rect = fitz.Rect(MARGIN, y + 6, PAGE_W - MARGIN, y + 220)
    rc = page.insert_textbox(rect, text, fontsize=10, color=color, fontname="helv")
    used = 220 - max(rc, 0) if rc >= 0 else 60
    return y + 6 + used + 18


def _table(page: fitz.Page, y: float, rows: list[tuple[str, str]]) -> float:
    for k, v in rows:
        page.insert_text((MARGIN, y), k, fontsize=9, color=MUTED)
        page.insert_text((MARGIN + 170, y), v, fontsize=9.5, color=INK)
        y += 16
    return y + 10


def build_ddr(ev: dict, well: dict, out: Path) -> None:
    pages = max(int(ev.get("source_page") or 1), 1) + 1
    doc = fitz.open()
    spud = date.fromisoformat(well.get("spud_date") or "2020-01-01")
    report_day = spud + timedelta(days=int(ev["depth_start_md_m"] // 60))
    title = f"Daily Drilling Report — {well['well_name']}"
    for p in range(1, pages + 1):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        y = _header(page, title, f"{well['field']} field · Report date {report_day.isoformat()} · Rig OIL-E2000", p, pages)
        if p == 1:
            y = _table(page, y, [
                ("Well", f"{well['well_name']} ({well['well_id']})"),
                ("Field", well["field"]),
                ("Well type", well["well_type"]),
                ("Report depth (MD)", f"{ev['depth_start_md_m']:.1f} m"),
                ("Formation at bit", ev.get("formation") or "—"),
                ("Operator", "Oil India Limited"),
            ])
            _para(page, y, "24-hour summary", "Drilled ahead with planned parameters. Details of operations "
                  "and any non-productive time are recorded on the following pages.")
        elif p == int(ev.get("source_page") or 1):
            y = _para(page, y, "Operations / incident",
                      f"{ev['event_type'].replace('_', ' ').title()} at {ev['depth_start_md_m']:.1f} m MD "
                      f"({ev.get('formation') or 'formation n/a'}). {ev.get('raw_narrative', '')}", ACCENT)
            y = _table(page, y, [
                ("Event type", ev["event_type"]),
                ("Severity", ev.get("severity", "")),
                ("Depth interval (MD)", f"{ev['depth_start_md_m']:.1f} – {(ev.get('depth_end_md_m') or ev['depth_start_md_m']):.1f} m"),
                ("NPT", f"{ev.get('npt_hours', 0)} h (IADC code {ev.get('iadc_npt_code') or '—'})"),
                ("Loss rate", f"{ev['loss_rate_bbl_hr']} bbl/hr" if ev.get("loss_rate_bbl_hr") else "—"),
            ])
            y = _para(page, y, "Mitigation / remedial action", ev.get("mitigation_description") or "—")
            _para(page, y, "Outcome / lesson learned", ev.get("outcome") or "—")
        else:
            _para(page, y, "Operations", "Circulated and conditioned mud. Routine rig service, BOP function test "
                  "and survey. No significant events during this reporting period.")
    doc.save(out)
    doc.close()


def build_wcr(well: dict, casing: list[dict], mud: list[dict], tops: list[dict], out: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = _header(page, f"Well Completion Report — {well['well_name']}", f"{well['field']} field · Status {well['status']}", 1, 2)
    y = _table(page, y, [
        ("Well ID", well["well_id"]), ("Surface location", f"{well['surface_lat']:.5f} N, {well['surface_lon']:.5f} E"),
        ("KB elevation", f"{well['kb_elevation_m']} m"), ("Total depth (MD)", f"{well['total_depth_md_m']} m"),
        ("Spud / completion", f"{well.get('spud_date')} / {well.get('completion_date')}"),
    ])
    page.insert_text((MARGIN, y), "CASING PROGRAM", fontsize=7.5, color=MUTED)
    y += 16
    for c in casing:
        page.insert_text((MARGIN, y), f"{c['casing_size']:>8} in {c['hole_size']} hole · shoe {c['shoe_md_m']} m MD "
                         f"({c['set_in_formation']}) · TOC {c['cement_top_md_m']} m", fontsize=9, color=INK)
        y += 14
    y += 14
    page.insert_text((MARGIN, y), "FORMATION TOPS", fontsize=7.5, color=MUTED)
    y += 16
    for t in tops:
        page.insert_text((MARGIN, y), f"{t['formation_name']:<22} top {t['top_md_m']:.1f} m MD · PP {t['pore_pressure_gradient_ppg']:.2f} ppg",
                         fontsize=9, color=INK)
        y += 14
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    y = _header(page, f"Well Completion Report — {well['well_name']}", "Mud program", 2, 2)
    for m in mud:
        page.insert_text((MARGIN, y), f"{m['from_md_m']:>7.0f}–{m['to_md_m']:<7.0f} m  {m['formation']:<20} {m['mud_type']:<28} {m['mud_weight_ppg']} ppg",
                         fontsize=8.5, color=INK)
        y += 14
    doc.save(out)
    doc.close()


SAMPLE_UPLOAD_TEXT = """DAILY DRILLING REPORT
Well: HGJ-011
Operator: Oil India Limited
Date: 02/03/2021
Rig: OIL-E2000   Field: Hugrijan

MUD PROPERTIES
Mud Weight: 10.4 ppg
Viscosity: 52 sec
pH: 9.5
Water Loss: 4.8 mL
PV: 24 cp

FORMATION TOPS
Kopili Top: 2632 m
Sylhet Limestone Top: 2759 m

OPERATIONS REMARKS
0200-0730 : Lost circulation observed at 2801 m in Sylhet Limestone, lost 60 bbl of mud. Spotted 40 bbl CaCO3 LCM pill and reduced pump rate to 1700 lpm. Losses cured. 5.5 hrs NPT.
0800-1100 : Stuck Pipe at 2812 m while making connection in Sylhet Limestone. Worked pipe and jarred free, back-reamed one stand. 3 hrs NPT.
1500-1700 : Gas influx observed at 2820 m, pit gain 6 bbl. Shut in well and circulated out kick with 10.8 ppg mud. 2 hrs NPT.
"""


def build_sample_upload(out_dir: Path) -> Path:
    """A realistic DDR for testbed well HGJ-011, used by the Documents screen's
    'try a sample report' action to demonstrate ingestion -> extraction ->
    knowledge repository end to end."""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "DDR_HGJ-011_2021-03-02.pdf"
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    page.insert_textbox(fitz.Rect(MARGIN, 60, PAGE_W - MARGIN, PAGE_H - 60), SAMPLE_UPLOAD_TEXT, fontsize=10.5, fontname="helv", color=INK)
    doc.save(path)
    doc.close()
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wells = {w["well_id"]: w for w in json.loads((HERE / "wells.json").read_text(encoding="utf-8"))}
    events = json.loads((HERE / "drilling_events.json").read_text(encoding="utf-8"))
    aug_path = HERE / "demo_augmentation.json"
    aug = json.loads(aug_path.read_text(encoding="utf-8")) if aug_path.exists() else {}
    events += aug.get("events", [])
    tops = json.loads((HERE / "formation_tops.json").read_text(encoding="utf-8"))

    n = 0
    for ev in events:
        name = ev.get("source_document")
        if name and ev["well_id"] in wells:
            build_ddr(ev, wells[ev["well_id"]], OUT / name)
            n += 1
    for wid, w in wells.items():
        build_wcr(
            w,
            [c for c in aug.get("casing_programs", []) if c["well_id"] == wid],
            [m for m in aug.get("mud_programs", []) if m["well_id"] == wid],
            sorted([t for t in tops if t["well_id"] == wid], key=lambda t: t["top_md_m"]),
            OUT / f"WCR_{wid}.pdf",
        )
    print(f"Wrote {n} DDRs and {len(wells)} WCRs to {OUT}")


if __name__ == "__main__":
    main()
