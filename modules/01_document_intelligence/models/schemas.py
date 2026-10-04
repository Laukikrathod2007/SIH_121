"""
NWIS Module 01 — Data Schemas (WITSML-Compliant)
All extracted data is mapped to these Pydantic models before being saved.
Based on: logger/03_DATA_MODELS_AND_WITSML_SCHEMAS.md
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, ConfigDict
import uuid
from datetime import datetime


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DocumentType(str, Enum):
    DDR = "DAILY_DRILLING_REPORT"
    WCR = "WELL_COMPLETION_REPORT"
    MUD_LOG = "MUD_LOG"
    MORNING_REPORT = "MORNING_REPORT"
    UNKNOWN = "UNKNOWN"


class EventType(str, Enum):
    MUD_LOSS = "MUD_LOSS"
    STUCK_PIPE = "STUCK_PIPE"
    KICK = "KICK"
    EQUIPMENT_FAILURE = "EQUIPMENT_FAILURE"
    WELLBORE_INSTABILITY = "WELLBORE_INSTABILITY"
    GAS_INFLUX = "GAS_INFLUX"
    LOST_CIRCULATION = "LOST_CIRCULATION"
    DEVIATION = "DEVIATION_CONTROL"
    NPT_OPERATIONAL = "NPT_OPERATIONAL"
    # Added after re-reading PS 26121 word-by-word: outcome (v) names
    # "overpressure zones" explicitly alongside mud loss/stuck pipe/torque
    # spikes/cementing, and none of the existing 10 values covered it.
    # Confirmed real, not speculative — real Volve completion reports
    # describe genuine overpressure findings in bar-vs-field-gradient terms
    # (e.g. "~12 bar overpressure compared to initial main field oil
    # gradient", WELL-15_9-F-1A_COMPLETION.pdf).
    OVERPRESSURE_ZONE = "OVERPRESSURE_ZONE"
    # Also named explicitly in the PS's own relevant-data list (item ix),
    # alongside mud losses/kicks/stuck pipe/NPT. Added for schema
    # completeness; honestly disclosed in the benchmark log that the
    # current real-data pull (14 Volve documents) has zero fishing-operation
    # narratives to validate this extraction against — unlike the other
    # additions here, this one is not yet real-data-verified.
    FISHING_OPERATION = "FISHING_OPERATION"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# EventType -> modules/02_nwis_backend HazardType reconciliation.
#
# Found during real-data benchmarking (Equinor Volve field documents): this
# module's EventType and module 02's HazardType are two independently-evolved
# taxonomies with no mapping between them. module 02's HazardType is
# MUD_LOSS/STUCK_PIPE/KICK/WELLBORE_INSTABILITY/TORQUE_SPIKE/CEMENTING_FAILURE
# — four values line up exactly by name, but this module's GAS_INFLUX and
# LOST_CIRCULATION (both real, frequently-extracted event types — see Step 13
# in logger/04_STEP_BY_STEP_IMPLEMENTATION_LOG.md) had nowhere to go
# downstream, and EQUIPMENT_FAILURE/DEVIATION/NPT_OPERATIONAL/UNKNOWN
# genuinely have no HazardType equivalent at all (they aren't offset-well
# geological hazards in module 02's sense — an equipment failure or NPT
# delay isn't something a future well would encounter at the same formation).
#
# No live integration currently pushes module 01's extracted events into
# module 02's data store — this mapping exists so that when one is built, the
# translation is explicit and justified per case rather than invented ad hoc
# at the call site.
EVENT_TYPE_TO_HAZARD_TYPE: dict["EventType", Optional[str]] = {
    EventType.MUD_LOSS: "MUD_LOSS",
    EventType.STUCK_PIPE: "STUCK_PIPE",
    EventType.KICK: "KICK",
    EventType.WELLBORE_INSTABILITY: "WELLBORE_INSTABILITY",
    # Lost circulation is a mud-loss mechanism specifically (fluid lost to
    # the formation rather than returned to surface) — module 02 doesn't
    # distinguish loss mechanisms, only MUD_LOSS as a whole.
    EventType.LOST_CIRCULATION: "MUD_LOSS",
    # A gas influx is the leading indicator/early form of a well-control
    # kick — module 02 has no separate "influx" hazard type, and treating it
    # as anything other than KICK would understate its severity.
    EventType.GAS_INFLUX: "KICK",
    # No HazardType equivalent — these describe the document/operation, not
    # a geological hazard a future offset well would encounter at this
    # formation, which is what module 02's HazardType exists to rank.
    EventType.EQUIPMENT_FAILURE: None,
    EventType.DEVIATION: None,
    EventType.NPT_OPERATIONAL: None,
    EventType.UNKNOWN: None,
    # module 02 gained a FISHING_OPERATION HazardType member for storage/
    # search purposes (Priority 5, 2026-10-04 remediation pass), so unlike
    # when this dict was first written, a mapping now exists. Still not fed
    # into hazard-prediction/scoring (a fishing job is a remedial action
    # after an incident, not a predictable geological hazard — see the full
    # reasoning on HazardType.FISHING_OPERATION itself); this mapping only
    # lets a module-01-extracted fishing event be stored/searched as a
    # historical record in module 02's event store, consistent with how
    # every other mapped EventType here is used downstream.
    EventType.FISHING_OPERATION: "FISHING_OPERATION",
}


def to_hazard_type(event_type: "EventType") -> Optional[str]:
    """
    Map this module's EventType to modules/02_nwis_backend's HazardType
    string value, or None if there's no equivalent (see
    EVENT_TYPE_TO_HAZARD_TYPE's per-case reasoning above). Returns the raw
    string, not module 02's enum class, since module 01 does not import
    module 02 as a dependency — the caller constructs module 02's HazardType
    from this value at the actual integration boundary.
    """
    return EVENT_TYPE_TO_HAZARD_TYPE.get(event_type)


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExtractionTier(str, Enum):
    TIER1_NATIVE = "TIER1_NATIVE_DIGITAL"
    TIER2_OCR = "TIER2_DOCLING_OCR"
    TIER3_TEMPLATE = "TIER3_TEMPLATE_MATCH"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FLAGGED = "FLAGGED_LOW_CONFIDENCE"
    FAILED = "FAILED_PHYSICS_VALIDATION"
    MANUAL_REVIEW = "PENDING_MANUAL_REVIEW"


# ---------------------------------------------------------------------------
# Bounding Box (visual grounding — every value has provenance)
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    """[x0, y0, x1, y1] in PDF points (1pt = 1/72 inch)"""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int = Field(ge=0, description="0-indexed page number")

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


# ---------------------------------------------------------------------------
# Extracted Field (atomic unit — single key:value with full provenance)
# ---------------------------------------------------------------------------

class ExtractedField(BaseModel):
    """
    Atomic extraction unit. Every field extracted from a DDR/WCR
    carries its bounding box, confidence score, and validation status.
    This is what makes us identical to cloud APIs like Reducto.
    """
    field_name: str
    raw_text: str                        # Exactly what OCR read
    normalized_value: Any                # Parsed float/int/str
    unit: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None
    validation_status: ValidationStatus = ValidationStatus.PASS
    validation_note: Optional[str] = None
    extraction_tier: ExtractionTier = ExtractionTier.TIER1_NATIVE


# ---------------------------------------------------------------------------
# Mud Properties (extracted from DDR header table)
# ---------------------------------------------------------------------------

class MudProperties(BaseModel):
    """Mud program data extracted from DDR — WITSML mudLog mapping"""
    # extra="forbid": this model exposes convenience properties (density_ppg,
    # viscosity_sec, water_loss_ml) that shadow the real field names below.
    # Pydantic silently drops unknown constructor kwargs by default, so
    # `MudProperties(density_ppg=...)` would build an empty object with no
    # error. Forbidding extras turns that into a loud failure instead.
    model_config = ConfigDict(extra="forbid")

    mud_weight_ppg: Optional[ExtractedField] = None       # witsml: mudLog.mudWeight
    funnel_viscosity_sec: Optional[ExtractedField] = None # witsml: mudLog.vis
    plastic_viscosity_cp: Optional[ExtractedField] = None
    yield_point_lbf_100sqft: Optional[ExtractedField] = None
    water_loss_ml_30min: Optional[ExtractedField] = None  # API filtrate loss
    cake_thickness_mm: Optional[ExtractedField] = None
    chloride_content_ppm: Optional[ExtractedField] = None
    ph: Optional[Union[ExtractedField, float]] = None

    @property
    def density_ppg(self) -> Optional[float]:
        return float(self.mud_weight_ppg.normalized_value) if (self.mud_weight_ppg and self.mud_weight_ppg.normalized_value is not None) else None

    @density_ppg.setter
    def density_ppg(self, val: Optional[float]):
        if self.mud_weight_ppg:
            self.mud_weight_ppg.normalized_value = val
        elif val is not None:
            self.mud_weight_ppg = ExtractedField(
                field_name="mud_weight_ppg",
                raw_text=str(val),
                normalized_value=val,
                unit="ppg",
                confidence=0.95,
            )

    @property
    def viscosity_sec(self) -> Optional[float]:
        return float(self.funnel_viscosity_sec.normalized_value) if (self.funnel_viscosity_sec and self.funnel_viscosity_sec.normalized_value is not None) else None

    @viscosity_sec.setter
    def viscosity_sec(self, val: Optional[float]):
        if self.funnel_viscosity_sec:
            self.funnel_viscosity_sec.normalized_value = val
        elif val is not None:
            self.funnel_viscosity_sec = ExtractedField(
                field_name="funnel_viscosity_sec",
                raw_text=str(val),
                normalized_value=val,
                unit="sec",
                confidence=0.95,
            )

    @property
    def water_loss_ml(self) -> Optional[float]:
        return float(self.water_loss_ml_30min.normalized_value) if (self.water_loss_ml_30min and self.water_loss_ml_30min.normalized_value is not None) else None

    @water_loss_ml.setter
    def water_loss_ml(self, val: Optional[float]):
        if self.water_loss_ml_30min:
            self.water_loss_ml_30min.normalized_value = val
        elif val is not None:
            self.water_loss_ml_30min = ExtractedField(
                field_name="water_loss_ml_30min",
                raw_text=str(val),
                normalized_value=val,
                unit="ml",
                confidence=0.95,
            )


# ---------------------------------------------------------------------------
# Drilling Parameters (BHA / bit run data)
# ---------------------------------------------------------------------------

class DrillingParameters(BaseModel):
    """Bit run / BHA data from DDR — WITSML opsReport mapping"""
    depth_from_md_m: Optional[ExtractedField] = None
    depth_to_md_m: Optional[ExtractedField] = None
    bit_size_inches: Optional[ExtractedField] = None
    bit_type: Optional[ExtractedField] = None
    rop_m_hr: Optional[ExtractedField] = None
    wob_klbs: Optional[ExtractedField] = None
    rpm: Optional[ExtractedField] = None
    torque_kn_m: Optional[ExtractedField] = None
    standpipe_pressure_psi: Optional[ExtractedField] = None
    flow_rate_lpm: Optional[ExtractedField] = None


# ---------------------------------------------------------------------------
# Formation Top (extracted from WCR / mud log)
# ---------------------------------------------------------------------------

class FormationTop(BaseModel):
    """WITSML stratigraphicColumn.formationMarker"""
    # See MudProperties for why extras are forbidden — top_depth_m/base_depth_m
    # are convenience properties, not real fields (top_md_m/base_md_m are).
    model_config = ConfigDict(extra="forbid")

    formation_name: str
    top_md_m: Optional[ExtractedField] = None
    top_tvd_m: Optional[ExtractedField] = None
    base_md_m: Optional[ExtractedField] = None
    lithology_description: Optional[str] = None
    # Matches module 02's FormationTop.porosity_pct/permeability_md/
    # water_saturation_pct addition — PS 26121 problem-description item
    # (iii) asks to correlate "reservoir characteristics" across wells.
    porosity_pct: Optional[ExtractedField] = None
    permeability_md: Optional[ExtractedField] = None
    water_saturation_pct: Optional[ExtractedField] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)

    @property
    def top_depth_m(self) -> Optional[float]:
        if self.top_md_m and self.top_md_m.normalized_value is not None:
            return float(self.top_md_m.normalized_value)
        return None

    @top_depth_m.setter
    def top_depth_m(self, val: Optional[float]):
        if self.top_md_m:
            self.top_md_m.normalized_value = val
        elif val is not None:
            self.top_md_m = ExtractedField(
                field_name="top_md_m",
                raw_text=str(val),
                normalized_value=val,
                unit="m",
                confidence=0.95,
            )

    @property
    def base_depth_m(self) -> Optional[float]:
        if self.base_md_m and self.base_md_m.normalized_value is not None:
            return float(self.base_md_m.normalized_value)
        return None

    @base_depth_m.setter
    def base_depth_m(self, val: Optional[float]):
        if self.base_md_m:
            self.base_md_m.normalized_value = val
        elif val is not None:
            self.base_md_m = ExtractedField(
                field_name="base_md_m",
                raw_text=str(val),
                normalized_value=val,
                unit="m",
                confidence=0.95,
            )


WellboreFormation = FormationTop


# ---------------------------------------------------------------------------
# NPT Record (Non-Productive Time)
# ---------------------------------------------------------------------------

class NPTRecord(BaseModel):
    """IADC NPT taxonomy mapping — WITSML opsReport.activity"""
    iadc_code: Optional[str] = None          # e.g. "101" = Stuck Pipe
    description: str
    start_time_hhmm: Optional[str] = None
    end_time_hhmm: Optional[str] = None
    npt_hours: Optional[ExtractedField] = None
    depth_md_m: Optional[ExtractedField] = None
    cost_usd_estimate: Optional[float] = None


# ---------------------------------------------------------------------------
# Drilling Event (the most important output for NWIS RAG engine)
# ---------------------------------------------------------------------------

class DrillingEvent(BaseModel):
    """
    Normalized drilling hazard event. This is the core entity
    that feeds the NWIS Risk Corridor engine and RAG retrieval.
    WITSML: opsReport.activity + custom extension
    """
    # See MudProperties for why extras are forbidden — remediation_action
    # below is a convenience property, not a real field (mitigation_description is).
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    event_type: EventType = EventType.UNKNOWN
    severity: Severity = Severity.MEDIUM
    depth_start_md_m: Optional[Union[ExtractedField, float]] = None
    depth_end_md_m: Optional[Union[ExtractedField, float]] = None
    formation: Optional[str] = None
    raw_narrative: str = ""              # Original OCR text from remarks section
    loss_rate_bbl_hr: Optional[Union[ExtractedField, float]] = None
    npt_hours: Optional[Union[ExtractedField, float]] = None
    mitigation_description: Optional[str] = None
    outcome: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    bounding_box: Optional[BoundingBox] = None

    @property
    def remediation_action(self) -> str:
        return self.mitigation_description or ""


# ---------------------------------------------------------------------------
# Casing Record
# ---------------------------------------------------------------------------

class CasingRecord(BaseModel):
    """WITSML: casing shoe / casing string data from WCR"""
    casing_size_inches: Optional[ExtractedField] = None
    shoe_depth_md_m: Optional[ExtractedField] = None
    top_of_cement_md_m: Optional[ExtractedField] = None
    grade: Optional[str] = None
    weight_lbft: Optional[ExtractedField] = None


# ---------------------------------------------------------------------------
# Page-Level Extraction Result
# ---------------------------------------------------------------------------

class PageExtractionResult(BaseModel):
    """Results extracted from a single PDF page"""
    page_number: int                     # 0-indexed
    is_scanned: bool = False             # True = raster image, used Tier 2
    extraction_tier: ExtractionTier
    processing_time_ms: float
    raw_text_preview: str = ""           # First 500 chars of extracted text
    mud_properties: Optional[MudProperties] = None
    drilling_parameters: Optional[DrillingParameters] = None
    formation_tops: List[FormationTop] = Field(default_factory=list)
    npt_records: List[NPTRecord] = Field(default_factory=list)
    drilling_events: List[DrillingEvent] = Field(default_factory=list)
    casing_records: List[CasingRecord] = Field(default_factory=list)
    page_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    # "local" (default) | "reducto" | "extend_ai" — which engine actually
    # produced this page's text. Exists so a document that used an external
    # cloud fallback is auditable per-page, not just a silent aggregate —
    # this matters for the air-gapped/DGH-sovereignty posture: any page
    # that left the local boundary must be traceable. See pipeline/cloud_fallback.py.
    extraction_source: str = "local"


# ---------------------------------------------------------------------------
# Document-Level Extraction Result (Master Output)
# ---------------------------------------------------------------------------

class DocumentExtractionResult(BaseModel):
    """
    Master output schema for a fully processed DDR or WCR document.
    This is what gets saved to data/output/ and served via REST API.
    WITSML-compliant, benchmarkable, and directly loadable into PostgreSQL.
    """
    # See MudProperties for why extras are forbidden — formation_tops/
    # drilling_events/npt_records below are convenience properties aliasing
    # all_formation_tops/all_drilling_events/all_npt_records, the real fields.
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(default_factory=lambda: f"DOC-{uuid.uuid4().hex[:12].upper()}")
    job_id: str = ""
    source_filename: str
    document_type: DocumentType = DocumentType.UNKNOWN
    well_name: Optional[str] = None
    operator: Optional[str] = None
    report_date: Optional[str] = None   # ISO date string

    # Extraction metadata
    total_pages: int = 0
    pages_processed: int = 0
    scanned_pages: int = 0              # Pages that required Tier 2 OCR
    template_used: Optional[str] = None # If template learning was applied

    # Timing
    extraction_started_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    extraction_completed_at: Optional[str] = None
    total_processing_time_ms: float = 0.0

    # Page-level results
    pages: List[PageExtractionResult] = Field(default_factory=list)

    # Aggregated top-level entities (flattened from pages for easy DB insert)
    all_formation_tops: List[FormationTop] = Field(default_factory=list)
    all_npt_records: List[NPTRecord] = Field(default_factory=list)
    all_drilling_events: List[DrillingEvent] = Field(default_factory=list)
    all_casing_records: List[CasingRecord] = Field(default_factory=list)
    mud_properties: List[MudProperties] = Field(default_factory=list)
    # Well-level headline porosity/permeability/water-saturation reading
    # (see extract_reservoir_properties' docstring for why this is a plain
    # dict, not per-formation). Keys: porosity_pct, permeability_md,
    # water_saturation_pct -- any subset may be present.
    reservoir_properties: dict = Field(default_factory=dict)

    # Cloud fallback audit trail (see pipeline/cloud_fallback.py). Stays at
    # zero/empty for every document unless NWIS_REDUCTO_API_KEY or
    # NWIS_EXTEND_API_KEY is actually configured AND at least one page's
    # local confidence fell below threshold — i.e. the air-gapped default
    # posture is unaffected unless this is visibly non-zero.
    cloud_fallback_pages_count: int = 0
    cloud_fallback_providers_used: List[str] = Field(default_factory=list)

    # Physics & Operational Summary
    total_npt_hours: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PASS

    # Quality metrics
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    flagged_fields_count: int = 0
    physics_violations_count: int = 0

    # WITSML export ready flag
    witsml_compliant: bool = True

    # -------------------------------------------------------------------
    # Human curation / review workflow (inspired by GDR/OpenEI's curator
    # review before publication — see logger/04_STEP_BY_STEP_IMPLEMENTATION_LOG.md).
    # validation_status can already carry MANUAL_REVIEW (models/schemas.py's
    # ValidationStatus enum), but until this, nothing ever set it and there
    # was no way for a human to act on it — see api/routes/review.py.
    # -------------------------------------------------------------------
    reviewed: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_decision: Optional[str] = None  # "approved" | "rejected"
    review_notes: Optional[str] = None
    # Lightweight, non-destructive field-level annotations — deliberately
    # NOT an automatic patch-in-place of extracted values. A generic
    # deep-path JSON patcher is exactly the kind of thing that silently
    # corrupts data when the path is slightly wrong; a human-readable note
    # attached to the document is safer and still closes the audit-trail
    # gap ("a person looked at this specific field and here's what's
    # actually true") without that risk.
    field_annotations: List[dict] = Field(default_factory=list)

    @property
    def formation_tops(self) -> List[FormationTop]:
        return self.all_formation_tops

    @formation_tops.setter
    def formation_tops(self, val: List[FormationTop]):
        self.all_formation_tops = val

    @property
    def drilling_events(self) -> List[DrillingEvent]:
        return self.all_drilling_events

    @drilling_events.setter
    def drilling_events(self, val: List[DrillingEvent]):
        self.all_drilling_events = val

    @property
    def npt_records(self) -> List[NPTRecord]:
        return self.all_npt_records

    @npt_records.setter
    def npt_records(self, val: List[NPTRecord]):
        self.all_npt_records = val


# ---------------------------------------------------------------------------
# API Request / Response Models
# ---------------------------------------------------------------------------

class IngestJobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestJobResponse(BaseModel):
    """Returned immediately when a document is submitted for ingestion"""
    job_id: str
    filename: str
    status: IngestJobStatus = IngestJobStatus.QUEUED
    message: str = "Document queued for processing"
    submitted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class JobStatusResponse(BaseModel):
    """Poll this to check ingestion progress"""
    job_id: str
    status: IngestJobStatus
    progress_percent: int = Field(ge=0, le=100, default=0)
    current_page: int = 0
    total_pages: int = 0
    message: str = ""
    document_id: Optional[str] = None   # Available when COMPLETED
    error: Optional[str] = None


class BenchmarkScore(BaseModel):
    """Benchmark metrics reported after validation run"""
    metric: str
    value: float
    unit: str
    reference_system: str
    reference_value: float
    status: str  # "MEETS", "EXCEEDS", "BELOW"
