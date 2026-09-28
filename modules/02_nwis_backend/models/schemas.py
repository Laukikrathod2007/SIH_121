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
    confidence: float = Field(ge=0.0, le=1.0, default=0.90)


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
    # NOTE: this is deliberately a DIFFERENT measure from
    # HazardRiskAssessment.risk_level (which is derived from the full
    # R_H(t) composite score). This one reflects purely how close/inside the
    # bit is to this specific corridor (see logger/02_MATHEMATICAL_AND_
    # ALGORITHMIC_FORMULATIONS.md §3's Safe/Early-Warning/Critical states) —
    # it does not factor in sensor anomaly or the ML term. It is named
    # differently from HazardRiskAssessment.risk_level (rather than reusing
    # "risk_level") specifically so the two are never mistaken for the same
    # number: a corridor can legitimately show CRITICAL proximity while its
    # parent hazard assessment shows LOW overall risk, if the historical
    # frequency here is low and sensor/ML signals are quiet.
    proximity_risk_level: RiskLevel = RiskLevel.LOW
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
