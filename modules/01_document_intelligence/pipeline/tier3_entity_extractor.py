"""
NWIS Module 01 — Tier 3: Petroleum Domain Entity Extractor
Extracts structured drilling entities from raw OCR text using:
  1. Compiled regex patterns for structured fields (fast, deterministic)
  2. Domain keyword matching for event classification
  3. Fuzzy formation name matching
  4. NPT hour calculation from time ranges

This layer handles the narrative "Operational Remarks" section of DDRs —
the part that contains the most valuable knowledge for NWIS risk intelligence.

Target accuracy: >90% F1 on petroleum NER (aligned with SPE-204112 benchmark)
"""

from __future__ import annotations
import re
import time
from typing import Optional, List, Tuple
from loguru import logger

from models.schemas import (
    MudProperties,
    DrillingParameters,
    FormationTop,
    CasingRecord,
    NPTRecord,
    DrillingEvent,
    ExtractedField,
    BoundingBox,
    ExtractionTier,
    EventType,
    Severity,
    ValidationStatus,
)
from models.domain_rules import (
    validate_field,
    fuzzy_match_formation,
    IADC_NPT_CODES,
    ASSAM_ARAKAN_FORMATIONS,
)


# ===========================================================================
# Compiled Regex Patterns (pre-compiled for speed)
# ===========================================================================

# --- Depth patterns ---
# Matches: "3,248 m", "3248m", "3248.5 mD", "10,650 ft"
RE_DEPTH = re.compile(
    r"(\d{1,5}[,.]?\d{0,3})\s*(m(?:D|TVD)?|ft|feet|meter[s]?)",
    re.IGNORECASE,
)

# --- Mud weight ---
# Matches: "11.2 ppg", "1.34 sg", "1340 kg/m3"
RE_MUD_WEIGHT = re.compile(
    r"(\d{1,2}\.?\d{0,2})\s*(ppg|lb/gal|sg|kg/m3|pcf)",
    re.IGNORECASE,
)

# --- Volume ---
# Matches: "40 bbl", "25 bbl", "200 m3"
RE_VOLUME = re.compile(
    r"(\d{1,5}\.?\d{0,2})\s*(bbl|barrel[s]?|m3|m³|ltr|litre[s]?)",
    re.IGNORECASE,
)

# --- Flow rate ---
RE_FLOW_RATE = re.compile(
    r"(\d{3,5}\.?\d{0,2})\s*(lpm|l/min|gpm|gal/min)",
    re.IGNORECASE,
)

# --- Time (HH:MM format in DDR) ---
RE_TIME_HHMM = re.compile(r"\b([0-2][0-9]):([0-5][0-9])\b")

# --- Hours ---
RE_HOURS = re.compile(
    r"(\d{1,2}\.?\d{0,2})\s*(?:hour[s]?|hr[s]?|h\b)",
    re.IGNORECASE,
)

# --- Pressure ---
RE_PRESSURE = re.compile(
    r"(\d{2,5}\.?\d{0,2})\s*(psi|kpa|mpa|bar|kg/cm2)",
    re.IGNORECASE,
)

# --- Temperature ---
RE_TEMP = re.compile(
    r"(\d{2,3}\.?\d{0,1})\s*(°?C|°?F|deg[.\s]?[CF])",
    re.IGNORECASE,
)

# --- Bit size ---
RE_BIT_SIZE = re.compile(
    r"(\d{1,2}[-\s]?\d{0,1}[/]?\d{0,1})\s*(?:in(?:ch)?|\")\s*(?:bit|PDC|TCI|roller)",
    re.IGNORECASE,
)

# --- RPM ---
RE_RPM = re.compile(r"\b(\d{2,3})\s*(?:rpm|RPM|rev/min)\b", re.IGNORECASE)

# --- WOB ---
RE_WOB = re.compile(
    r"(\d{1,3}\.?\d{0,1})\s*(?:klbs|k-lbs|kN|kdaN)\s*(?:WOB|weight[\s-]on[\s-]bit)?",
    re.IGNORECASE,
)

# --- ROP ---
RE_ROP = re.compile(
    r"(?:ROP|rate[\s-]of[\s-]penetration)[:\s]+(\d{1,3}\.?\d{0,2})\s*(?:m/hr?|ft/hr?)",
    re.IGNORECASE,
)


# ===========================================================================
# Event Classification Keywords
# ===========================================================================

EVENT_KEYWORDS: dict[EventType, List[str]] = {
    EventType.MUD_LOSS: [
        "lost circulation", "loss of circulation", "fluid loss", "mud loss",
        "lcm", "lost returns", "total loss", "partial loss", "seepage loss",
        "nut plug", "lost circ", "no returns",
    ],
    EventType.STUCK_PIPE: [
        "stuck pipe", "stuck drill string", "pipe stuck", "unable to rotate",
        "overpull", "cannot pull", "pipe became stuck", "free the pipe",
        "jar", "back-reaming stuck",
    ],
    EventType.KICK: [
        "well control", "kick", "influx", "shut in", "sicp", "sidpp",
        "well kick", "gas cut mud", "flow check",
    ],
    EventType.WELLBORE_INSTABILITY: [
        "tight hole", "sloughing", "shale sloughing", "caving", "pack off",
        "packoff", "bridging", "wellbore instability", "overpull",
        "swabbing", "surge",
    ],
    EventType.GAS_INFLUX: [
        "gas influx", "gas cut", "gas units", "h2s", "hydrogen sulfide",
        "background gas", "connection gas", "trip gas",
    ],
    EventType.EQUIPMENT_FAILURE: [
        "equipment failure", "pump failure", "motor failure", "mwd failure",
        "lwd failure", "washout", "bit balling", "top drive failure",
        "rig down", "mechanical failure",
    ],
    EventType.LOST_CIRCULATION: [
        "lost circulation", "loss zone", "thief zone", "fracture",
        "vugular", "cavernous", "open fracture",
    ],
    # Real narratives confirmed in Volve completion reports, e.g. "~12 bar
    # overpressure compared to initial main field oil gradient"
    # (WELL-15_9-F-1A_COMPLETION.pdf). Deliberately just the "overpressur"
    # stem, not "abnormal pressure" -- a real match for that phrase in the
    # same document set turned out to be a NEGATIVE case ("losses were NOT
    # due to abnormal pressure conditions"), the same false-positive shape
    # kick/kickoff had, so it's excluded rather than risk repeating it.
    EventType.OVERPRESSURE_ZONE: [
        "overpressure", "overpressured", "over-pressured", "over pressured",
    ],
    # Standard oilfield terminology, added for schema completeness per PS
    # 26121's explicit mention (relevant-data item ix) -- NOT yet validated
    # against real data. The current 14-document Volve pull has zero
    # fishing-operation narratives (confirmed by keyword scan), so this list
    # is un-tested against real text, unlike every other entry here.
    EventType.FISHING_OPERATION: [
        "fishing operation", "fishing job", "fishing string", "fishing tool",
        "junk in hole", "overshot", "fishing spear", "recover the fish",
        "lost in hole", "retrieve the assembly",
    ],
}

SEVERITY_KEYWORDS = {
    Severity.CRITICAL: [
        "total", "complete", "blowout", "well control", "h2s", "evacuation",
        "no returns", "severe", "emergency",
    ],
    Severity.HIGH: [
        "high", "major", "significant", "40 bbl", "30 bbl", "stuck",
        "kick", "influx", "over", "loss",
    ],
    Severity.MEDIUM: [
        "partial", "moderate", "intermittent", "seepage", "minor loss",
    ],
    Severity.LOW: [
        "minor", "slight", "small", "trace", "minimal",
    ],
}

MITIGATION_KEYWORDS = [
    "pumped", "mixed", "spotted", "pill", "lcm", "nut plug", "mica",
    "squeeze", "cement plug", "reduced flow", "increased mud weight",
    "weight up", "back-ream", "jar", "free", "circulate",
]


# ===========================================================================
# Helper: Parse Numeric Value from Match
# ===========================================================================

def _parse_numeric(raw: str) -> Optional[float]:
    """Parse a string like '3,248' or '11.2' to float. Returns None on failure."""
    try:
        return float(raw.replace(",", "").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def _make_field(
    field_name: str,
    raw_text: str,
    value: float,
    unit: Optional[str] = None,
    confidence: float = 0.90,
    bbox: Optional[BoundingBox] = None,
) -> ExtractedField:
    """Build an ExtractedField with physics validation applied."""
    from models.domain_rules import validate_field
    from models.schemas import ValidationStatus
    is_valid, status_str, message = validate_field(field_name, value)

    if status_str == "FAIL":
        v_status = ValidationStatus.FAILED
        confidence = min(confidence, 0.3)  # Drastically reduce confidence
    elif status_str == "WARN":
        v_status = ValidationStatus.FLAGGED
        confidence = min(confidence, 0.7)
    else:
        v_status = ValidationStatus.PASS

    return ExtractedField(
        field_name=field_name,
        raw_text=raw_text,
        normalized_value=value,
        unit=unit,
        confidence=round(confidence, 3),
        bounding_box=bbox,
        validation_status=v_status,
        validation_note=message if v_status != ValidationStatus.PASS else None,
        extraction_tier=ExtractionTier.TIER1_NATIVE,
    )


# ===========================================================================
# Mud Properties Extraction
# ===========================================================================

def extract_mud_properties(text: str) -> Optional[MudProperties]:
    """
    Extract mud program data from DDR header table text.
    Handles common DDR section headers:
    'MUD PROPERTIES', 'MUD PROGRAM', 'FLUID PROPERTIES'
    """
    if not text:
        return None

    mud = MudProperties()
    found_any = False

    # Mud weight
    mw_section = _find_section(text, ["mud weight", "mw", "fluid density", "mud wt"])
    if mw_section:
        m = RE_MUD_WEIGHT.search(mw_section)
        if m:
            val = _parse_numeric(m.group(1))
            unit = m.group(2).lower()
            # Convert SG to PPG if needed
            if val and "sg" in unit:
                val = round(val * 8.33, 2)
                unit = "ppg"
            if val:
                mud.mud_weight_ppg = _make_field("mud_weight_ppg", m.group(0), val, "ppg")
                found_any = True

    # Funnel viscosity
    vis_section = _find_section(text, ["viscosity", "vis", "marsh funnel", "funnel"])
    if vis_section:
        m = RE_HOURS.search(vis_section)  # e.g. "45 sec"
        sec_m = re.search(r"(\d{2,3})\s*(?:sec|s\b)", vis_section, re.IGNORECASE)
        if sec_m:
            val = _parse_numeric(sec_m.group(1))
            if val:
                mud.funnel_viscosity_sec = _make_field(
                    "funnel_viscosity_sec", sec_m.group(0), val, "sec"
                )
                found_any = True

    # pH
    ph_m = re.search(r"\bpH\s*[:\-=]?\s*(\d{1,2}\.?\d?)\b", text, re.IGNORECASE)
    if ph_m:
        val = _parse_numeric(ph_m.group(1))
        if val:
            mud.ph = _make_field("ph", ph_m.group(0), val, "pH")
            found_any = True

    # Water loss (API filtrate)
    wl_section = _find_section(text, ["water loss", "api loss", "filtrate", "fl@"])
    if wl_section:
        ml_m = re.search(r"(\d{1,3}\.?\d?)\s*(?:ml|cc|mL)", wl_section, re.IGNORECASE)
        if ml_m:
            val = _parse_numeric(ml_m.group(1))
            if val:
                mud.water_loss_ml_30min = _make_field(
                    "water_loss_ml_30min", ml_m.group(0), val, "mL"
                )
                found_any = True

    # Plastic Viscosity (PV)
    pv_m = re.search(r"\b(?:PV|PLASTIC\s*VISCOSITY)\s*[:\-=]?\s*(\d{1,3}\.?\d?)\s*(?:cp|cps|mPa\.s)?\b", text, re.IGNORECASE)
    if pv_m:
        val = _parse_numeric(pv_m.group(1))
        if val:
            mud.plastic_viscosity_cp = _make_field("plastic_viscosity_cp", pv_m.group(0), val, "cP")
            found_any = True

    # Yield Point (YP)
    yp_m = re.search(r"\b(?:YP|YIELD\s*POINT)\s*[:\-=]?\s*(\d{1,3}\.?\d?)\s*(?:lbf/100sqft|lb/100ft2|Pa)?\b", text, re.IGNORECASE)
    if yp_m:
        val = _parse_numeric(yp_m.group(1))
        if val:
            mud.yield_point_lbf_100sqft = _make_field("yield_point_lbf_100sqft", yp_m.group(0), val, "lbf/100sqft")
            found_any = True

    return mud if found_any else None


# ===========================================================================
# Drilling Parameters Extraction
# ===========================================================================

def extract_drilling_parameters(text: str) -> Optional[DrillingParameters]:
    """Extract BHA / bit run parameters from DDR drilling section."""
    if not text:
        return None

    params = DrillingParameters()
    found_any = False

    # ROP
    m = RE_ROP.search(text)
    if m:
        val = _parse_numeric(m.group(1))
        if val:
            params.rop_m_hr = _make_field("rop_m_hr", m.group(0), val, "m/hr")
            found_any = True

    # WOB
    m = RE_WOB.search(text)
    if m:
        val = _parse_numeric(m.group(1))
        if val:
            params.wob_klbs = _make_field("wob_klbs", m.group(0), val, "klbs")
            found_any = True

    # RPM
    m = RE_RPM.search(text)
    if m:
        val = _parse_numeric(m.group(1))
        if val:
            params.rpm = _make_field("rpm", m.group(0), val, "rpm")
            found_any = True

    # SPP
    m = RE_PRESSURE.search(text)
    if m:
        val = _parse_numeric(m.group(1))
        unit = m.group(2).lower()
        if val and "psi" in unit:
            params.standpipe_pressure_psi = _make_field(
                "standpipe_pressure_psi", m.group(0), val, "psi"
            )
            found_any = True

    # Flow rate
    m = RE_FLOW_RATE.search(text)
    if m:
        val = _parse_numeric(m.group(1))
        if val:
            params.flow_rate_lpm = _make_field("flow_rate_lpm", m.group(0), val, "lpm")
            found_any = True

    return params if found_any else None


# ===========================================================================
# Drilling Event Extraction (Narrative Remarks Section)
# ===========================================================================

def extract_drilling_events(text: str) -> List[DrillingEvent]:
    """
    Extract hazard events from the 'REMARKS' or 'OPERATIONS' section of a DDR.
    This is the most intellectually challenging extraction — narrative text.

    Example input:
    "Total fluid loss of 40 bbl at 3,248 m; mixed 25 bbl nut-plug pill.
     Reduced pump rate from 2100 lpm to 1550 lpm. NPT: 6.5 hrs."

    Output: Fully structured DrillingEvent with EventType, depth, volumes, NPT.
    """
    if not text:
        return []

    events: List[DrillingEvent] = []
    text_lower = text.lower()

    # Split into sentences for per-sentence analysis
    sentences = re.split(r"[.;\n]+", text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15:  # Skip very short fragments
            continue

        s_lower = sentence.lower()

        # --- Determine event type ---
        event_type = EventType.UNKNOWN
        for etype, keywords in EVENT_KEYWORDS.items():
            if any(kw in s_lower for kw in keywords):
                event_type = etype
                break

        if event_type == EventType.UNKNOWN:
            continue  # Not an event sentence

        # --- Determine severity ---
        severity = Severity.MEDIUM
        for sev, keywords in SEVERITY_KEYWORDS.items():
            if any(kw in s_lower for kw in keywords):
                severity = sev
                break

        # --- Extract depth ---
        depth_field = None
        depth_m = RE_DEPTH.search(sentence)
        if depth_m:
            val = _parse_numeric(depth_m.group(1))
            unit = depth_m.group(2).lower()
            if val:
                if "ft" in unit:
                    val = round(val * 0.3048, 1)  # Convert ft → m
                depth_field = _make_field("depth_md_m", depth_m.group(0), val, "m")

        # --- Extract loss rate / volume ---
        loss_field = None
        vol_m = RE_VOLUME.search(sentence)
        if vol_m:
            val = _parse_numeric(vol_m.group(1))
            if val:
                loss_field = _make_field(
                    "loss_rate_bbl_hr",
                    vol_m.group(0),
                    val,
                    vol_m.group(2).lower(),
                    confidence=0.80,  # Volume needs context to be loss_rate
                )

        # --- Extract NPT hours ---
        npt_field = None
        npt_m = RE_HOURS.search(sentence)
        if npt_m:
            val = _parse_numeric(npt_m.group(1))
            if val:
                npt_field = _make_field("npt_hours", npt_m.group(0), val, "hr")

        # --- Extract mitigation description ---
        mitigation = None
        for kw in MITIGATION_KEYWORDS:
            if kw in s_lower:
                # Take the rest of the sentence after the mitigation keyword
                idx = s_lower.find(kw)
                mitigation = sentence[idx:].strip()
                break

        # --- Extract formation ---
        formation = None
        for fm in ASSAM_ARAKAN_FORMATIONS:
            if fm.lower() in s_lower:
                formation = fm
                break
        if formation is None:
            # Try fuzzy match on any capitalized word
            cap_words = re.findall(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", sentence)
            for cw in cap_words:
                fm_match = fuzzy_match_formation(cw)
                if fm_match:
                    formation = fm_match
                    break

        # Calculate overall confidence for this event
        confidence = 0.70
        if depth_field:
            confidence += 0.10
        if loss_field:
            confidence += 0.05
        if npt_field:
            confidence += 0.05
        if mitigation:
            confidence += 0.05
        confidence = min(confidence, 0.97)

        event = DrillingEvent(
            event_type=event_type,
            severity=severity,
            depth_start_md_m=depth_field,
            formation=formation,
            raw_narrative=sentence,
            loss_rate_bbl_hr=loss_field,
            npt_hours=npt_field,
            mitigation_description=mitigation,
            confidence=round(confidence, 3),
        )
        events.append(event)

    logger.info(f"Entity extractor found {len(events)} drilling events")
    return events


# ===========================================================================
# Formation Top Extraction
# ===========================================================================

def extract_formation_tops(text: str) -> List[FormationTop]:
    """
    Extract formation top depths from WCR / Mud Log text sections.
    Looks for patterns like: "Tipam Sandstone — Top: 2,980 m"
    """
    tops: List[FormationTop] = []
    if not text:
        return tops

    # ASSAM_ARAKAN_FORMATIONS lists both full names and their common
    # abbreviations (e.g. "Tipam Sandstone" AND "TIPAM"). An abbreviation is
    # a substring of its full name, so a single mention like "Tipam Sandstone
    # ... 2,980 m" would otherwise match twice — once per list entry — and
    # produce two FormationTop records for the same physical top. Processing
    # longer names first and tracking which depth-figure span has already
    # been attributed prevents that double-count.
    seen_depth_spans: set = set()
    for fm_name in sorted(ASSAM_ARAKAN_FORMATIONS, key=len, reverse=True):
        pattern = re.compile(
            rf"{re.escape(fm_name)}[^.]*?(\d{{1,5}}[,.]?\d{{0,3}})\s*(?:m|ft|mD)",
            re.IGNORECASE,
        )
        m = pattern.search(text)
        if not m:
            continue

        depth_span = m.span(1)
        if depth_span in seen_depth_spans:
            continue  # this depth figure was already attributed to a longer/fuller formation name

        val = _parse_numeric(m.group(1))
        if val:
            seen_depth_spans.add(depth_span)
            top_field = _make_field("depth_md_m", m.group(0), val, "m", confidence=0.85)
            tops.append(
                FormationTop(
                    formation_name=fm_name,
                    top_md_m=top_field,
                    confidence=0.85,
                )
            )

    return tops


# ===========================================================================
# Casing Records (incl. cementing top-of-cement) — PS 26121 problem-
# description item (iii) asks to correlate "casing programs" and
# "cementing practices" across wells. The CasingRecord schema already
# existed in models/schemas.py (top_of_cement_md_m included) but had zero
# extraction logic anywhere in this pipeline -- found by grepping the
# codebase, not assumed. This is the first function that actually
# populates it.
# ===========================================================================

# Real pattern confirmed against WELL-15_9-F-1A_COMPLETION.pdf's casing
# records table: '20" Casing shoe | 1348.4 | 1336.4' and
# '13 3/8" Casing shoe | 2595.4 | 2446.8' (size | MD | TVD, cells joined
# with either '|' or a bare newline depending on document/row -- both
# real, confirmed by inspecting actual PyMuPDF output on real documents).
#
# Real bug found testing: the separator between the two number groups was
# originally `\s*\|?\s*` -- every piece individually optional, so it could
# match ZERO characters. When a row has only one real number (e.g. a liner
# shoe depth "3090" with no TVD following, real case:
# '9 5/8" Casing shoe\n3090'), the regex still "matched" by splitting the
# single contiguous number into two arbitrary halves ("30" + "90") to
# satisfy both required groups, rather than correctly failing to match.
# Fixed by requiring at least one real separator character ([\s|]+, one
# or more) between groups, so two numbers can only be split where a real
# newline or pipe actually separates them.
RE_CASING_SHOE_TABLE_ROW = re.compile(
    r'(\d{1,2}(?:\s\d/\d)?)\s*"\s*Casing\s*shoe[\s|]+(\d{2,5}\.?\d{0,2})[\s|]+(\d{2,5}\.?\d{0,2})\b',
    re.IGNORECASE,
)

# Single-number fallback for a real row shape confirmed above: casing size
# + shoe MD with no TVD following (a liner or an incompletely-tabulated
# row) -- tried only when the two-number pattern above doesn't match this
# specific "Casing shoe" mention, so a row that DOES have both numbers is
# never double-counted by also matching this looser pattern.
RE_CASING_SHOE_SINGLE = re.compile(
    r'(\d{1,2}(?:\s\d/\d)?)\s*"\s*Casing\s*shoe[\s|]+(\d{2,5}\.?\d{0,2})\b',
    re.IGNORECASE,
)

# Narrative fallback for documents without a clean table (e.g. DDR prose:
# "13 3/8-inch casing run to 2595m" or "9 5/8" casing set at 2200m").
RE_CASING_NARRATIVE = re.compile(
    r'(\d{1,2}(?:[\s-]\d/\d)?)\s*(?:"|inch(?:es)?)\s*casing\s*(?:run|set|landed)?\s*(?:to|at|@)?\s*(\d{2,5}\.?\d{0,2})\s*m',
    re.IGNORECASE,
)

RE_TOP_OF_CEMENT = re.compile(
    r'top\s*of\s*cement\D{0,20}(\d{1,5}\.?\d{0,2})\s*m',
    re.IGNORECASE,
)


def _parse_casing_size(raw: str) -> Optional[float]:
    """
    Real bug found testing against WELL-15_9-F-1A_COMPLETION.pdf: the
    naive 'replace space with .' approach turned '13 3/8' into the string
    '13.3/8', which float() correctly rejects -- so every fractional-inch
    casing size (the norm in real casing programs: 13 3/8", 9 5/8", 7") was
    silently dropped. Parses 'N F/D' (whole + fraction) or a plain integer.
    """
    raw = raw.strip()
    frac_m = re.match(r'^(\d{1,2})\s+(\d)/(\d)$', raw)
    if frac_m:
        whole, num, den = frac_m.groups()
        return float(whole) + float(num) / float(den)
    return _parse_numeric(raw)


def extract_casing_records(text: str) -> List[CasingRecord]:
    """
    Extract casing size + shoe depth (+ top-of-cement where stated nearby)
    from WCR completion-report casing-records tables or DDR narrative.
    """
    records: List[CasingRecord] = []
    if not text:
        return records

    seen_shoe_depths: set = set()
    for m in RE_CASING_SHOE_TABLE_ROW.finditer(text):
        size_val = _parse_casing_size(m.group(1))
        md_val = _parse_numeric(m.group(2))
        if md_val is None or md_val in seen_shoe_depths:
            continue
        seen_shoe_depths.add(md_val)
        records.append(
            CasingRecord(
                casing_size_inches=_make_field("casing_size_inches", m.group(1), size_val or 0.0, "in", confidence=0.85)
                if size_val is not None else None,
                shoe_depth_md_m=_make_field("shoe_depth_md_m", m.group(0), md_val, "m", confidence=0.85),
            )
        )

    # Real rows with only a shoe MD and no TVD (see RE_CASING_SHOE_SINGLE's
    # docstring) -- checked against seen_shoe_depths so a row the two-number
    # pattern above already captured isn't duplicated here.
    for m in RE_CASING_SHOE_SINGLE.finditer(text):
        size_val = _parse_casing_size(m.group(1))
        md_val = _parse_numeric(m.group(2))
        if md_val is None or md_val in seen_shoe_depths:
            continue
        seen_shoe_depths.add(md_val)
        records.append(
            CasingRecord(
                casing_size_inches=_make_field("casing_size_inches", m.group(1), size_val or 0.0, "in", confidence=0.80)
                if size_val is not None else None,
                shoe_depth_md_m=_make_field("shoe_depth_md_m", m.group(0), md_val, "m", confidence=0.80),
            )
        )

    if not records:
        for m in RE_CASING_NARRATIVE.finditer(text):
            size_val = _parse_casing_size(m.group(1).replace("-", " "))
            md_val = _parse_numeric(m.group(2))
            if md_val is None or md_val in seen_shoe_depths:
                continue
            seen_shoe_depths.add(md_val)
            records.append(
                CasingRecord(
                    casing_size_inches=_make_field("casing_size_inches", m.group(1), size_val or 0.0, "in", confidence=0.70)
                    if size_val is not None else None,
                    shoe_depth_md_m=_make_field("shoe_depth_md_m", m.group(0), md_val, "m", confidence=0.70),
                )
            )

    # Attach top-of-cement to the nearest-depth casing record if any is
    # mentioned in the document (real docs typically state it once near a
    # specific string, not per-record — best-effort attach to the deepest
    # shoe, which is the common real convention: TOC reported for the
    # production/intermediate string, not surface casing).
    toc_m = RE_TOP_OF_CEMENT.search(text)
    if toc_m and records:
        toc_val = _parse_numeric(toc_m.group(1))
        if toc_val is not None:
            deepest = max(records, key=lambda r: r.shoe_depth_md_m.normalized_value or 0)
            deepest.top_of_cement_md_m = _make_field("top_of_cement_md_m", toc_m.group(0), toc_val, "m", confidence=0.75)

    return records


# ===========================================================================
# Reservoir Characteristics (porosity, permeability, water saturation)
# ===========================================================================

# Real pattern confirmed against WELL-15_9-F-12_COMPLETION.pdf: "porosity of
# 0.17" (decimal fraction, not percentage) and "4 p.u. less than the
# porosity" (p.u. = porosity units = percentage points). Value is stored
# as a percentage (0.17 -> 17.0) to match module 02's porosity_pct field.
RE_POROSITY = re.compile(r'porosity\s+(?:of|is|was|being)?\s*(\d{1,2}\.\d{1,3})\b', re.IGNORECASE)
RE_PERMEABILITY = re.compile(r'permeabilit\w*\D{0,15}(\d{1,6}\.?\d{0,2})\s*(?:mD|md)\b', re.IGNORECASE)
RE_WATER_SATURATION = re.compile(r'water\s+saturation\D{0,20}(\d{1,3}\.?\d{0,2})\s*%', re.IGNORECASE)

# Real bug found testing against WELL-15_9-F-1_PETROPHYSICAL.pdf: the first
# "permeability...mD" match in that document was "cut offs correspond to a
# overburden corrected core permeability of 0.5 mD" -- a methodology
# CUTOFF threshold, not an actual reservoir reading. Same class of mistake
# as formation-tops matching methodology prose instead of a data table.
# Fixed by skipping any match whose nearby context mentions "cut off"/
# "cutoff"/"cut-off", and by checking ALL matches (not just the first) so a
# real value elsewhere in the document isn't lost when the first mention
# happens to be a cutoff.
_CUTOFF_CONTEXT = re.compile(r'cut[\s-]?off', re.IGNORECASE)


def _first_non_cutoff_match(pattern: "re.Pattern", text: str, context_window: int = 60) -> Optional["re.Match"]:
    for m in pattern.finditer(text):
        ctx_start = max(0, m.start() - context_window)
        if not _CUTOFF_CONTEXT.search(text[ctx_start:m.end()]):
            return m
    return None


def extract_reservoir_properties(text: str) -> dict:
    """
    Extract porosity/permeability/water-saturation from petrophysical or
    completion report narrative text. Returns a plain dict (well-level, not
    per-formation) since real documents in this data set report these as
    single headline values for the target reservoir, not a per-formation
    table -- attaching a well-level reading to a specific FormationTop
    record would overstate precision the source text doesn't have.
    """
    result: dict = {}
    if not text:
        return result

    m = _first_non_cutoff_match(RE_POROSITY, text)
    if m:
        val = _parse_numeric(m.group(1))
        if val is not None:
            # "porosity of 0.17" is a decimal fraction -> 17.0%; values
            # already >1 (rare, but seen as "porosity of 17.0" in some
            # narrative styles) are treated as already-percentage.
            result["porosity_pct"] = round(val * 100, 1) if val <= 1.0 else val

    m = _first_non_cutoff_match(RE_PERMEABILITY, text)
    if m:
        val = _parse_numeric(m.group(1))
        if val is not None:
            result["permeability_md"] = val

    m = _first_non_cutoff_match(RE_WATER_SATURATION, text)
    if m:
        val = _parse_numeric(m.group(1))
        if val is not None:
            result["water_saturation_pct"] = val

    return result


# ===========================================================================
# NPT Calculation from Time Ranges
# ===========================================================================

def calculate_npt_from_times(text: str) -> List[NPTRecord]:
    """
    Calculate NPT hours from time range entries in DDR.
    DDRs often have tables like:
    "0600–1130 : Stuck Pipe — Worked to free string. (5.5 hrs NPT)"
    """
    npt_records: List[NPTRecord] = []
    if not text:
        return npt_records

    # Pattern: TIME1 - TIME2 : description
    time_range_pattern = re.compile(
        r"(\d{4})\s*[-–—to]+\s*(\d{4})\s*[:\-]?\s*(.+?)(?=\d{4}\s*[-–]|\Z)",
        re.IGNORECASE | re.DOTALL,
    )

    for m in time_range_pattern.finditer(text):
        t1_str, t2_str, description = m.group(1), m.group(2), m.group(3).strip()

        # Parse HHMM format
        try:
            h1, m1 = int(t1_str[:2]), int(t1_str[2:])
            h2, m2 = int(t2_str[:2]), int(t2_str[2:])
            total_minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
            if total_minutes < 0:
                total_minutes += 24 * 60  # Handle overnight spans
            npt_hours_val = round(total_minutes / 60, 2)
        except (ValueError, IndexError):
            continue

        # Only add if description contains NPT-related keywords
        desc_lower = description.lower()
        is_npt = any(
            kw in desc_lower
            for kw in ["stuck", "loss", "kick", "fail", "wait", "repair", "cement"]
        )

        if is_npt and 0 < npt_hours_val <= 24:
            npt_field = _make_field("npt_hours", f"{npt_hours_val}hr", npt_hours_val, "hr")

            # Try to match IADC code
            iadc_code = None
            for code, label in IADC_NPT_CODES.items():
                if any(kw in desc_lower for kw in label.lower().split()):
                    iadc_code = code
                    break

            npt_records.append(
                NPTRecord(
                    iadc_code=iadc_code,
                    description=description[:200],
                    start_time_hhmm=t1_str[:2] + ":" + t1_str[2:],
                    end_time_hhmm=t2_str[:2] + ":" + t2_str[2:],
                    npt_hours=npt_field,
                )
            )

    return npt_records


# ===========================================================================
# Utility: Find text near section headers
# ===========================================================================

def _find_section(text: str, headers: List[str], window: int = 300) -> Optional[str]:
    """
    Find text within `window` characters after any of the given section headers.
    Used to extract values that appear near known DDR field labels.
    """
    text_lower = text.lower()
    for header in headers:
        idx = text_lower.find(header.lower())
        if idx != -1:
            return text[idx: idx + window]
    return None


# ===========================================================================
# Master Entity Extraction (called by orchestrator)
# ===========================================================================

def extract_all_entities(page_text: str, page_number: int) -> dict:
    """
    Run all entity extractors on page text.
    Returns dict with all extracted entities for this page.
    """
    start_ms = time.time() * 1000

    result = {
        "mud_properties": extract_mud_properties(page_text),
        "drilling_parameters": extract_drilling_parameters(page_text),
        "formation_tops": extract_formation_tops(page_text),
        "npt_records": calculate_npt_from_times(page_text),
        "drilling_events": extract_drilling_events(page_text),
        # Was a stub ("Implemented in phase 2") with zero extraction logic
        # behind it — found by grepping the codebase for CasingRecord's only
        # other reference, which was its own schema definition. Now real.
        "casing_records": extract_casing_records(page_text),
        "reservoir_properties": extract_reservoir_properties(page_text),
    }

    elapsed = time.time() * 1000 - start_ms
    logger.debug(
        f"Entity extraction page {page_number}: "
        f"events={len(result['drilling_events'])}, "
        f"formations={len(result['formation_tops'])}, "
        f"npt={len(result['npt_records'])}, "
        f"time={elapsed:.1f}ms"
    )
    return result
