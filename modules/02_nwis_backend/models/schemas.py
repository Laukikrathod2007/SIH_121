"""
NWIS Module 02 — Core Data Models (WITSML-Compliant)
Pydantic schemas for the Backend Intelligence Core.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class WellType(str, Enum):
    VERTICAL = "Vertical"
    J_TYPE = "J-Type"
    S_TYPE = "S-Type"
    HORIZONTAL = "Horizontal"


class WellStatus(str, Enum):
    PRODUCING = "PRODUCING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    SUSPENDED = "SUSPENDED"
    DRILLING = "DRILLING"


class HazardType(str, Enum):
    MUD_LOSS = "MUD_LOSS"
    STUCK_PIPE = "STUCK_PIPE"
    KICK = "KICK"
    WELLBORE_INSTABILITY = "WELLBORE_INSTABILITY"
    TORQUE_SPIKE = "TORQUE_SPIKE"
    CEMENTING_FAILURE = "CEMENTING_FAILURE"
    # Added to match module 01's EventType.OVERPRESSURE_ZONE addition — PS
    # 26121 outcome (v) names "overpressure zones" explicitly alongside the
    # other five hazards above, and this module had no equivalent despite
    # already carrying pore_pressure_gradient_ppg on FormationTop.
    OVERPRESSURE_ZONE = "OVERPRESSURE_ZONE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceStrength(str, Enum):
    HIGH = "HIGH"       # N >= 5 analog wells
    MODERATE = "MODERATE"  # 3 <= N < 5
    LOW = "LOW"         # 1 <= N < 3
    INSUFFICIENT = "INSUFFICIENT"  # N == 0


# ---------------------------------------------------------------------------
# Well
# ---------------------------------------------------------------------------

class SurveyStation(BaseModel):
    md_m: float
    inclination_deg: float
    azimuth_deg: float
    tvd_m: float
    ns_m: float
    ew_m: float
    tvdss_m: float


class WellTrajectory(BaseModel):
    well_id: str
    well_name: str
    method: str = "MINIMUM_CURVATURE"
    well_type: WellType = WellType.VERTICAL
    stations: List[SurveyStation] = Field(default_factory=list)

    @property
    def avg_inclination(self) -> float:
        if not self.stations:
            return 0.0
        return sum(s.inclination_deg for s in self.stations) / len(self.stations)

    @property
    def max_tvd(self) -> float:
        if not self.stations:
            return 0.0
        return max(s.tvd_m for s in self.stations)

    def tvd_at_md(self, md: float) -> float:
        """Interpolate TVD at a given MD."""
        for i, s in enumerate(self.stations):
            if s.md_m >= md:
                if i == 0:
                    return s.tvd_m
                prev = self.stations[i - 1]
                frac = (md - prev.md_m) / max(s.md_m - prev.md_m, 0.001)
                return prev.tvd_m + frac * (s.tvd_m - prev.tvd_m)
        return self.stations[-1].tvd_m if self.stations else md


class Well(BaseModel):
    well_id: str
    well_name: str
    field: str
    field_code: str
    operator: str
    surface_lat: float
    surface_lon: float
    kb_elevation_m: float = 10.0
    total_depth_md_m: float
    well_type: WellType = WellType.VERTICAL
    spud_date: Optional[str] = None
    completion_date: Optional[str] = None
    status: WellStatus = WellStatus.COMPLETED
    witsml_uid: str = Field(default_factory=lambda: str(uuid.uuid4()))


# ---------------------------------------------------------------------------
# Formation
# ---------------------------------------------------------------------------

class FormationTop(BaseModel):
    well_id: str
    well_name: str
    formation_name: str
    top_md_m: float
    top_tvd_m: float
    base_md_m: float
    thickness_m: float
    pore_pressure_gradient_ppg: float = 9.0
    lithology: Optional[str] = None
    # Added after re-reading PS 26121 word-by-word: problem-description item
    # (iii) asks to correlate "reservoir characteristics" across wells, and
    # this model had none — lithology and pore pressure aren't the same
    # thing. All three are real, commonly-reported log-derived properties
    # (not invented) — confirmed present in real Volve petrophysical/
    # completion reports (e.g. WELL-15_9-F-1_PETROPHYSICAL.pdf: 28 porosity
    # mentions, 28 permeability, 14 water-saturation, real percentages).
    # Optional and None by default since most formation tops in the existing
    # synthetic testbed were never given these values — added for real
    # documents that report them, not retrofitted as a universal requirement.
    porosity_pct: Optional[float] = None
    permeability_md: Optional[float] = None
    water_saturation_pct: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.90)


class CasingRecord(BaseModel):
    """
    Real casing string data (size, shoe depth, top-of-cement), so casing
    programs and cementing practices are correlatable across wells per PS
    26121 problem-description item (iii). Mirrors module 01's CasingRecord
    (which does real extraction now — logger Step 20) but as plain fields,
    matching this module's style, rather than ExtractedField-wrapped.

    NOTE, stated honestly: this model exists so module 02 CAN serve/
    correlate casing data, but nothing currently populates it from module
    01's real extraction output -- the two modules aren't connected (see
    logger/09_VERIFIED_STATUS...md §2.3). That's the separately-scoped
    Postgres/integration work, not silently implied as done here.
    """
    well_id: str
    casing_size_inches: Optional[float] = None
    shoe_depth_md_m: float
    top_of_cement_md_m: Optional[float] = None


# ---------------------------------------------------------------------------
# Drilling Event
# ---------------------------------------------------------------------------

class DrillingEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    well_id: str
    event_type: HazardType
    severity: str = "MEDIUM"
    depth_start_md_m: float
    depth_end_md_m: Optional[float] = None
    formation: Optional[str] = None
    raw_narrative: str = ""
    npt_hours: float = 0.0
    iadc_npt_code: Optional[str] = None
    loss_rate_bbl_hr: Optional[float] = None
    mitigation_description: Optional[str] = None
    outcome: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.90)
    source_document: Optional[str] = None
    source_page: Optional[int] = None


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

class TelemetryRecord(BaseModel):
    well_id: str
    timestamp: str
    depth_m: float
    rop_m_hr: float = 0.0
    wob_klbs: float = 0.0
    rpm: float = 0.0
    torque_kn_m: float = 0.0
    standpipe_pressure_psi: float = 0.0
    flow_in_lpm: float = 0.0
    flow_out_lpm: float = 0.0
    pit_volume_bbl: float = 0.0
    mud_weight_ppg: float = 9.0
    d_exponent: float = 1.0


# ---------------------------------------------------------------------------
# DORS Engine Outputs
# ---------------------------------------------------------------------------

class DORSComponentScores(BaseModel):
    spatial: float = Field(ge=0.0, le=1.0)
    formation: float = Field(ge=0.0, le=1.0)
    depth: float = Field(ge=0.0, le=1.0)
    trajectory: float = Field(ge=0.0, le=1.0)
    hazard: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)
    distance_km: float


class OffsetWellRanking(BaseModel):
    rank: int
    well_id: str
    well_name: str
    field: str
    well_type: str
    dors_score: float
    component_scores: DORSComponentScores
    formation_match: str
    events_in_lookahead: int
    distance_km: float


# ---------------------------------------------------------------------------
# Risk Corridor
# ---------------------------------------------------------------------------

class RiskCorridor(BaseModel):
    corridor_id: str = Field(default_factory=lambda: f"COR-{uuid.uuid4().hex[:6].upper()}")
    hazard_type: HazardType
    depth_start_m: float
    depth_end_m: float
    contributing_wells: List[str]   # well_ids
    contributing_events: List[str]  # event_ids
    event_count: int
    avg_npt_hours: float
    max_severity: str
    historical_frequency: float     # P_history [0,1]
    lead_distance_m: Optional[float] = None  # Δ from current bit depth
    risk_level: RiskLevel = RiskLevel.LOW
    recommended_action: str = ""
    formation: Optional[str] = None


# ---------------------------------------------------------------------------
# 4-Pillar Confidence
# ---------------------------------------------------------------------------

class FourPillarConfidence(BaseModel):
    evidence_strength: EvidenceStrength
    evidence_count: int              # N offset analogs
    sensor_anomaly_score: float = Field(ge=0.0, le=1.0)  # Z-score normalized
    data_quality_index: float = Field(ge=0.0, le=1.0)    # completeness
    audit_status: str = "GROUNDED"   # GROUNDED / PARTIAL / UNVERIFIED
    overall_confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Hazard Risk Assessment (single hazard family output)
# ---------------------------------------------------------------------------

class HazardRiskAssessment(BaseModel):
    hazard_type: HazardType
    risk_level: RiskLevel
    composite_score: float           # R_H(t) ∈ [0,1]
    p_history: float                 # Historical frequency weight (α=0.45)
    a_sensor: float                  # Sensor anomaly score (β=0.35)
    m_ml: float                      # ML prediction (γ=0.20)
    # "trained_model" (a real classifier trained on historical events — see
    # ml/train_hazard_models.py) or "heuristic_fallback" (too few historical
    # examples exist yet for this hazard type to train one — see
    # ml/feature_engineering.py's MIN_POSITIVE_SAMPLES). Exposed so the API
    # never presents a hand-coded heuristic and a real model as the same
    # kind of number — consistent with 4-Pillar Confidence's whole point.
    m_ml_source: str = "heuristic_fallback"
    confidence: FourPillarConfidence
    active_corridor: Optional[RiskCorridor] = None
    lead_time_meters: Optional[float] = None
    recommended_action: str = ""
    evidence_events: List[str] = Field(default_factory=list)  # event_ids


# ---------------------------------------------------------------------------
# Full NWIS Analysis Response
# ---------------------------------------------------------------------------

class NWISAnalysisResponse(BaseModel):
    active_well_id: str
    current_depth_m: float
    analysis_timestamp: str
    offset_rankings: List[OffsetWellRanking]
    hazard_assessments: List[HazardRiskAssessment]
    active_risk_corridors: List[RiskCorridor]
    formation_at_bit: Optional[str] = None
    overall_risk_level: RiskLevel = RiskLevel.LOW
    alert_message: Optional[str] = None
