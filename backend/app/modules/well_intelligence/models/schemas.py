"""
Well Intelligence Domain Models & Schemas (WITSML-Compliant).
Pydantic schemas for Wells, Trajectories, Formations, DORS Rankings, Risk Corridors, and 4-Pillar Confidence.
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
    HIGH = "HIGH"               # N >= 5 analog wells
    MODERATE = "MODERATE"       # 3 <= N < 5
    LOW = "LOW"                 # 1 <= N < 3
    INSUFFICIENT = "INSUFFICIENT" # N == 0


# ---------------------------------------------------------------------------
# Well & Trajectory
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
# Provenance & Structural Enums
# ---------------------------------------------------------------------------

class ProvenanceTier(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    IMPUTED = "IMPUTED"
    EXTRAPOLATED = "EXTRAPOLATED"
    SYNTHETIC = "SYNTHETIC"


class StructuralFaultStatus(str, Enum):
    SAME_FAULT_BLOCK = "SAME_FAULT_BLOCK"
    POSSIBLE_FAULT_BOUNDARY = "POSSIBLE_FAULT_BOUNDARY"
    CONFIRMED_FAULT = "CONFIRMED_FAULT"


# ---------------------------------------------------------------------------
# Formation Top
# ---------------------------------------------------------------------------

class FormationTop(BaseModel):
    well_id: str
    well_name: str
    formation_name: str
    top_md_m: float
    top_tvd_m: float
    base_md_m: float
    thickness_m: float
    top_tvdss_m: Optional[float] = None
    base_tvdss_m: Optional[float] = None
    uncertainty_m: float = 5.0
    provenance_tier: str = "OBSERVED"
    method: str = "WELL_LOG"
    pore_pressure_gradient_ppg: float = 9.0
    lithology: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.90)
    source_document: Optional[str] = None
    source_page: Optional[int] = None


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
    depth_tvdss_m: Optional[float] = None
    formation: Optional[str] = None
    raw_narrative: str = ""
    npt_hours: float = 0.0
    iadc_npt_code: Optional[str] = None
    loss_rate_bbl_hr: Optional[float] = None
    mitigation_description: Optional[str] = None
    outcome: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.90)
    provenance_tier: str = "OBSERVED"
    source_document: Optional[str] = None
    source_page: Optional[int] = None
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1] normalized coords


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
# DORS / Omega Engine Outputs
# ---------------------------------------------------------------------------

class DORSComponentScores(BaseModel):
    spatial: float = Field(ge=0.0, le=1.0)
    formation: float = Field(ge=0.0, le=1.0)
    depth: float = Field(ge=0.0, le=1.0)
    trajectory: float = Field(ge=0.0, le=1.0)
    hazard: float = Field(ge=0.0, le=1.0)
    total: float = Field(ge=0.0, le=1.0)
    distance_km: float


class OmegaComponentScores(BaseModel):
    distance: float = Field(ge=0.0, le=1.0)
    geological: float = Field(ge=0.0, le=1.0)
    trajectory: float = Field(ge=0.0, le=1.0)
    completion: float = Field(ge=0.0, le=1.0)
    total_omega: float = Field(ge=0.0, le=1.0)
    distance_km: float
    structural_status: str = "SAME_FAULT_BLOCK"


class OffsetWellRanking(BaseModel):
    rank: int
    well_id: str
    well_name: str
    field: str
    well_type: str
    dors_score: float
    component_scores: DORSComponentScores
    omega_score: Optional[float] = None
    omega_components: Optional[OmegaComponentScores] = None
    structural_status: str = "SAME_FAULT_BLOCK"
    formation_match: str
    events_in_lookahead: int
    distance_km: float


# ---------------------------------------------------------------------------
# Risk Corridor & Ahead-of-Bit Projections
# ---------------------------------------------------------------------------

class AheadOfBitCorridorPoint(BaseModel):
    depth_ahead_m: float
    md_m: float
    tvdss_m: float
    formation: Optional[str] = None
    xi: Optional[float] = None
    in_bounds: bool = True
    window_tier: str = "PROACTIVE_50_200M"
    lost_circulation_risk: float = 0.0
    stuck_pipe_risk: float = 0.0
    kick_risk: float = 0.0
    wellbore_instability_risk: float = 0.0
    torque_spike_risk: float = 0.0
    evidence_count: int = 0
    evidence_events: List[Dict[str, Any]] = Field(default_factory=list)


class AheadOfBitCorridor(BaseModel):
    active_well_id: str
    current_md_m: float
    current_tvdss_m: float
    current_formation: Optional[str] = None
    current_xi: Optional[float] = None
    points: List[AheadOfBitCorridorPoint] = Field(default_factory=list)


class RiskCorridor(BaseModel):
    corridor_id: str = Field(default_factory=lambda: f"COR-{uuid.uuid4().hex[:6].upper()}")
    hazard_type: HazardType
    depth_start_m: float
    depth_end_m: float
    contributing_wells: List[str]
    contributing_events: List[str]
    event_count: int
    avg_npt_hours: float
    max_severity: str
    historical_frequency: float
    lead_distance_m: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.LOW
    recommended_action: str = ""
    formation: Optional[str] = None


# ---------------------------------------------------------------------------
# 4-Pillar Confidence
# ---------------------------------------------------------------------------

class FourPillarConfidence(BaseModel):
    evidence_strength: EvidenceStrength
    evidence_count: int
    sensor_anomaly_score: float = Field(ge=0.0, le=1.0)
    data_quality_index: float = Field(ge=0.0, le=1.0)
    audit_status: str = "GROUNDED"
    overall_confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Hazard Risk Assessment
# ---------------------------------------------------------------------------

class HazardRiskAssessment(BaseModel):
    hazard_type: HazardType
    risk_level: RiskLevel
    composite_score: float
    p_history: float
    a_sensor: float
    m_ml: float
    confidence: FourPillarConfidence
    active_corridor: Optional[RiskCorridor] = None
    lead_time_meters: Optional[float] = None
    recommended_action: str = ""
    evidence_events: List[str] = Field(default_factory=list)


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
    ahead_of_bit_corridor: Optional[AheadOfBitCorridor] = None
    formation_at_bit: Optional[str] = None
    overall_risk_level: RiskLevel = RiskLevel.LOW
    alert_message: Optional[str] = None

