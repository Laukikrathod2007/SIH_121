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
from app.core.logging import logger

from app.modules.document_intelligence.models.schemas import (
    MudProperties,
    DrillingParameters,
    FormationTop,
    NPTRecord,
    DrillingEvent,
    ExtractedField,
    BoundingBox,
    ExtractionTier,
    EventType,
    Severity,
    ValidationStatus,
)
from app.modules.document_intelligence.models.domain_rules import (
    validate_field,
    fuzzy_match_formation,
    IADC_NPT_CODES,
    get_active_formations,
)


# ===========================================================================
# Compiled Regex Patterns (pre-compiled for speed)
# ===========================================================================

# --- Depth patterns ---
# Matches: "3,248 m", "3248m", "3248.5 mD", "10,650 ft"
RE_DEPTH = re.compile(
    # Trailing lookahead stops "4.8 mL" / "10 min" being read as a depth in metres.
    r"(\d{1,5}[,.]?\d{0,3})\s*(m(?:D|TVD)?|ft|feet|meter[s]?)(?![a-zA-Z])",
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
    from app.modules.document_intelligence.models.domain_rules import validate_field
    from app.modules.document_intelligence.models.schemas import ValidationStatus
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

    # DDR operations remarks are time-stamped entries ("0600-1130 : ...") that
    # PDF text extraction wraps across several lines. Treating every line or
    # sentence separately split one incident into an event with no action and
    # an "action" with no depth. When time-stamped entries exist, analyse each
    # whole entry as one unit (hazard sentence + the remedial sentences that
    # follow it); otherwise fall back to sentence-level analysis.
    # The page text arrives with extracted lines joined by " | "; treat that
    # separator as a line break for block detection.
    lined = re.sub(r"[ \t]*\|[ \t]*", "\n", text)
    remark_blocks = [
        re.sub(r"\s*\n\s*", " ", b).strip()
        for b in re.findall(
            r"(\d{4}\s*-\s*\d{4}\s*:.*?)(?=\n\s*\d{4}\s*-\s*\d{4}\s*:|\n\s*[A-Z][A-Z /&]{4,}\s*(?:\n|$)|\Z)",
            lined, flags=re.DOTALL,
        )
    ]
    sentences = remark_blocks if remark_blocks else re.split(r"[.;\n]+", text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15:  # Skip very short fragments
            continue

        s_lower = sentence.lower()
        # Mud-property lines ("Water Loss: 4.8 mL", "API fluid loss 5 ml")
        # describe filtrate, not a lost-circulation incident.
        if re.search(r"(water|fluid|filtrate|api)\s+loss\s*[:\d]", s_lower) and not re.search(r"lost|losses|bbl", s_lower):
            continue

        # "Kick off"/"kicked off"/"kick-off" is directional-drilling jargon
        # (starting to build inclination) with no relation to a well-control
        # kick — but the bare "kick" keyword below is a substring match, so it
        # fired on both senses. Found via real-data testing (Volve field DDRs):
        # e.g. "Bit #1 kicked off and drilled without problem to 2345m" was
        # misclassified as a HIGH-severity KICK event. Neutralize the
        # directional-drilling phrase before keyword matching, for both event
        # type and severity, rather than dropping "kick" from the keyword list
        # entirely (which would miss real well-control kicks).
        s_lower_kw = re.sub(r"kick(?:ed)?[\s-]?off", "KICKOFF_DIRECTIONAL_DRILLING_TERM", s_lower)

        # --- Determine event type ---
        event_type = EventType.UNKNOWN
        if remark_blocks:
            # Whole remark: the hazard named FIRST is the incident; later
            # keywords usually describe the remedy ("stuck pipe ... pumped LCM pill").
            first_pos = {
                etype: min((s_lower_kw.find(kw) for kw in keywords if kw in s_lower_kw), default=-1)
                for etype, keywords in EVENT_KEYWORDS.items()
            }
            hits = {k: v for k, v in first_pos.items() if v >= 0}
            if hits:
                event_type = min(hits, key=hits.get)
        else:
            for etype, keywords in EVENT_KEYWORDS.items():
                if any(kw in s_lower_kw for kw in keywords):
                    event_type = etype
                    break

        if event_type == EventType.UNKNOWN:
            continue  # Not an event sentence

        # --- Determine severity ---
        severity = Severity.MEDIUM
        for sev, keywords in SEVERITY_KEYWORDS.items():
            if any(kw in s_lower_kw for kw in keywords):
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
        if remark_blocks:
            # Everything after the incident sentence is the crew's response.
            body = re.sub(r"^\d{4}\s*-\s*\d{4}\s*:\s*", "", sentence)
            rest = re.split(r"(?<=[.;])\s+", body, maxsplit=1)
            if len(rest) == 2:
                action = re.sub(r"\s*\d+(?:\.\d+)?\s*(?:hrs?|hours?)\s*(?:of\s*)?NPT\.?", "", rest[1], flags=re.IGNORECASE).strip(" .;")
                mitigation = action or None
        for kw in ([] if mitigation else MITIGATION_KEYWORDS):
            if kw in s_lower:
                # Take the rest of the sentence after the mitigation keyword
                idx = s_lower.find(kw)
                mitigation = sentence[idx:].strip()
                break

        # --- Extract formation ---
        formation = None
        for fm in get_active_formations():
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

    # The active basin's formation list (get_active_formations() —
    # NWIS_FORMATION_PROFILE, default ASSAM_ARAKAN) lists both full names and
    # common abbreviations (e.g. "Tipam Sandstone" AND "TIPAM"). An
    # abbreviation is a substring of its full name, so a single mention like
    # "Tipam Sandstone ... 2,980 m" would otherwise match twice — once per
    # list entry — and produce two FormationTop records for the same physical
    # top. Processing longer names first and tracking which depth-figure span
    # has already been attributed prevents that double-count.
    seen_depth_spans: set = set()
    for fm_name in sorted(get_active_formations(), key=len, reverse=True):
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
        "casing_records": [],  # Implemented in phase 2
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

