"""
Document Intelligence Domain Physics Validation Rules
OISD-157, IADC Drilling Manual (12th Ed), OIL India Operational Standards.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from app.modules.document_intelligence.models.schemas import ValidationStatus

# ---------------------------------------------------------------------------
# Physical Constants (Drilling Engineering Fundamentals)
# ---------------------------------------------------------------------------

FRESHWATER_DENSITY_PPG = 8.33   # lb/gal — minimum possible mud weight
MAX_BARITE_MUD_PPG = 21.0       # lb/gal — theoretical maximum with barite
MAX_ROP_HARD_ROCK_M_HR = 200.0  # Extreme upper bound for any lithology
MAX_WOB_KLBS = 100.0            # Physical limit of standard BHA
MAX_TORQUE_KNM = 80.0           # Upper bound for 6-5/8" drill pipe
MAX_SPP_PSI = 5000.0            # Standard pump working pressure limit
MAX_FLOW_RATE_LPM = 4000.0      # High-flow mud pumps
MAX_HOURS_PER_DAY = 24.0        # Hard physical limit
MIN_BIT_SIZE_INCHES = 3.5       # Smallest PDC bit used in E&P
MAX_BIT_SIZE_INCHES = 36.0      # Largest conductor section bit


@dataclass
class ValidationRule:
    field_name: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_units: List[str] = field(default_factory=list)
    cross_check_field: Optional[str] = None
    cross_check_condition: Optional[str] = None
    error_message: str = ""
    warning_threshold: Optional[float] = None
    unit_conversion_factor: float = 1.0


DRILLING_DOMAIN_RULES: dict[str, ValidationRule] = {
    "mud_weight_ppg": ValidationRule(
        field_name="mud_weight_ppg",
        min_value=FRESHWATER_DENSITY_PPG,
        max_value=MAX_BARITE_MUD_PPG,
        allowed_units=["ppg", "lb/gal", "kg/m3", "sg", "pcf"],
        warning_threshold=18.0,
        error_message=(
            f"Mud weight must be between {FRESHWATER_DENSITY_PPG} ppg (freshwater) "
            f"and {MAX_BARITE_MUD_PPG} ppg (max barite slurry). "
            "Values outside this range indicate an OCR misread."
        ),
    ),
    "funnel_viscosity_sec": ValidationRule(
        field_name="funnel_viscosity_sec",
        min_value=26.0,
        max_value=300.0,
        allowed_units=["sec", "s", "seconds"],
        error_message=(
            "Marsh funnel viscosity must be 26–300 seconds. "
            "Below 26s = thinner than water (impossible for drilling mud). "
            "Above 300s = funnel will not flow (not a realistic DDR value)."
        ),
    ),
    "plastic_viscosity_cp": ValidationRule(
        field_name="plastic_viscosity_cp",
        min_value=1.0,
        max_value=120.0,
        allowed_units=["cp", "cP", "mPa.s", "mPas"],
        error_message="Plastic viscosity must be 1–120 cP for drilling fluids.",
    ),
    "yield_point_lbf_100sqft": ValidationRule(
        field_name="yield_point_lbf_100sqft",
        min_value=0.0,
        max_value=80.0,
        allowed_units=["lbf/100sqft", "lb/100sqft", "Pa"],
        error_message="Yield point must be 0–80 lbf/100sqft.",
    ),
    "water_loss_ml_30min": ValidationRule(
        field_name="water_loss_ml_30min",
        min_value=0.5,
        max_value=50.0,
        allowed_units=["ml", "mL", "cc"],
        error_message=(
            "API water loss (30 min) must be 0.5–50 mL. "
            ">50 mL indicates severe filtration — flag for review."
        ),
    ),
    "ph": ValidationRule(
        field_name="ph",
        min_value=7.0,
        max_value=13.5,
        allowed_units=["pH", ""],
        error_message=(
            "Drilling fluid pH must be 7–13.5. "
            "Below 7 = acidic (corrosive, never used in active drilling). "
            "Above 13.5 = caustic soda overtreatment (physically impossible in DDR)."
        ),
    ),
    "rop_m_hr": ValidationRule(
        field_name="rop_m_hr",
        min_value=0.0,
        max_value=MAX_ROP_HARD_ROCK_M_HR,
        allowed_units=["m/hr", "m/h", "ft/hr", "ft/h"],
        warning_threshold=80.0,
        error_message=(
            f"ROP must be 0–{MAX_ROP_HARD_ROCK_M_HR} m/hr. "
            "Above this indicates OCR error (e.g., misread '1.8' as '18')."
        ),
    ),
    "wob_klbs": ValidationRule(
        field_name="wob_klbs",
        min_value=0.0,
        max_value=MAX_WOB_KLBS,
        allowed_units=["klbs", "k-lbs", "kN", "kdaN"],
        error_message=f"WOB must be 0–{MAX_WOB_KLBS} klbs.",
    ),
    "rpm": ValidationRule(
        field_name="rpm",
        min_value=0.0,
        max_value=350.0,
        allowed_units=["rpm", "RPM", "rev/min"],
        error_message="Surface RPM must be 0–350. Above this = OCR misread.",
    ),
    "torque_kn_m": ValidationRule(
        field_name="torque_kn_m",
        min_value=0.0,
        max_value=MAX_TORQUE_KNM,
        allowed_units=["kN.m", "kNm", "ft.lbf", "ft-lbf"],
        warning_threshold=50.0,
        error_message=f"Surface torque must be 0–{MAX_TORQUE_KNM} kN.m.",
    ),
    "standpipe_pressure_psi": ValidationRule(
        field_name="standpipe_pressure_psi",
        min_value=0.0,
        max_value=MAX_SPP_PSI,
        allowed_units=["psi", "kPa", "MPa", "bar"],
        warning_threshold=4000.0,
        error_message=f"Standpipe pressure must be 0–{MAX_SPP_PSI} psi.",
    ),
    "flow_rate_lpm": ValidationRule(
        field_name="flow_rate_lpm",
        min_value=0.0,
        max_value=MAX_FLOW_RATE_LPM,
        allowed_units=["lpm", "l/min", "L/min", "gpm", "gal/min"],
        error_message=f"Flow rate must be 0–{MAX_FLOW_RATE_LPM} lpm.",
    ),
    "depth_md_m": ValidationRule(
        field_name="depth_md_m",
        min_value=0.0,
        max_value=12000.0,
        allowed_units=["m", "mD", "ft"],
        error_message=(
            "Measured depth must be 0–12,000 m for Indian E&P context. "
            "Depths above 6,000 m are unusual for Assam Basin — flag for review."
        ),
        warning_threshold=6000.0,
    ),
    "npt_hours": ValidationRule(
        field_name="npt_hours",
        min_value=0.0,
        max_value=MAX_HOURS_PER_DAY,
        allowed_units=["hr", "hrs", "hours", "h"],
        error_message=(
            f"NPT hours must be 0–{MAX_HOURS_PER_DAY} per day report. "
            "NPT > 24h in a single DDR = OCR misread or corrupt source."
        ),
    ),
    "bit_size_inches": ValidationRule(
        field_name="bit_size_inches",
        min_value=MIN_BIT_SIZE_INCHES,
        max_value=MAX_BIT_SIZE_INCHES,
        allowed_units=["in", "inch", "inches", '"'],
        error_message=f"Bit size must be {MIN_BIT_SIZE_INCHES}–{MAX_BIT_SIZE_INCHES} inches.",
    ),
}

STANDARD_ASSAM_CASING_PROGRAM = {
    "conductor_30in": {"min_m": 30, "max_m": 100},
    "surface_20in": {"min_m": 250, "max_m": 600},
    "intermediate_13_3_8in": {"min_m": 1200, "max_m": 2200},
    "production_9_5_8in": {"min_m": 2500, "max_m": 4500},
    "liner_7in": {"min_m": 3000, "max_m": 6000},
}

IADC_NPT_CODES = {
    "100": "Stuck Pipe — General",
    "101": "Stuck Pipe — Differential Sticking",
    "102": "Stuck Pipe — Packoff / Bridge",
    "103": "Stuck Pipe — Keyseat",
    "110": "BHA / Bit Failure",
    "111": "MWD / LWD Failure",
    "112": "Motor Failure",
    "120": "Casing / Wellhead / BOP Issue",
    "130": "Surface Equipment Failure",
    "131": "Pump Failure",
    "132": "Top Drive / Rotary Table Failure",
    "200": "Lost Circulation — General",
    "201": "Lost Circulation — Total (> 30 bbl/hr)",
    "202": "Lost Circulation — Partial (< 30 bbl/hr)",
    "210": "Wellbore Instability / Shale Sloughing",
    "211": "Tight Hole / Overpull",
    "220": "Well Control / Kick / Influx",
    "221": "Gas Influx",
    "222": "Water Influx",
    "300": "Deviation / Directional Drilling Issue",
    "310": "Formation Evaluation Delay",
    "320": "Cement / Cementing Failure",
    "400": "Rig Repair / Maintenance",
    "401": "Waiting on Cement (WOC)",
    "402": "Waiting on Orders (WOO)",
    "403": "Waiting on Weather (WOW)",
    "410": "Supply / Logistics Delay",
}

ASSAM_ARAKAN_FORMATIONS = [
    "Alluvium",
    "Girujan Clay",
    "Tipam Sandstone",
    "Barail Sandstone",
    "Kopili Shale",
    "Sylhet Limestone",
    "Langpar Formation",
    "Jaintia Group",
    "Basement",
    "TIPAM", "BARAIL", "KOPILI", "SYLHET", "LANGPAR",
]


def validate_field(field_name: str, value) -> Tuple[bool, str, str]:
    if hasattr(value, "normalized_value"):
        value = value.normalized_value
    value = float(value)

    rule = DRILLING_DOMAIN_RULES.get(field_name)
    if rule is None:
        return True, "PASS", "No rule defined — value accepted as-is"

    if rule.min_value is not None and value < rule.min_value:
        return False, "FAIL", rule.error_message

    if rule.max_value is not None and value > rule.max_value:
        return False, "FAIL", rule.error_message

    if rule.warning_threshold is not None and value > rule.warning_threshold:
        return True, "WARN", (
            f"Value {value} exceeds warning threshold {rule.warning_threshold} "
            f"for {field_name}. Flagging for review."
        )

    return True, "PASS", "Value within expected physical range"


def fuzzy_match_formation(raw_name: str) -> Optional[str]:
    from difflib import get_close_matches
    raw_upper = raw_name.upper().strip()
    candidates = [f.upper() for f in ASSAM_ARAKAN_FORMATIONS]
    matches = get_close_matches(raw_upper, candidates, n=1, cutoff=0.65)
    if matches:
        idx = candidates.index(matches[0])
        return ASSAM_ARAKAN_FORMATIONS[idx]
    return None
