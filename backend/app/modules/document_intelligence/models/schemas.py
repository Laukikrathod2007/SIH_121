"""
Document Intelligence Domain Models & Schemas (WITSML-Compliant).
Pydantic schemas for DDR/WCR extraction, entities, bounding boxes, and ingestion jobs.
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
    UNKNOWN = "UNKNOWN"


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
# Visual Provenance
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    """[x0, y0, x1, y1] in PDF points (1pt = 1/72 inch)."""
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


class ExtractedField(BaseModel):
    """Atomic extraction field with bounding box, confidence, and validation status."""
    field_name: str
    raw_text: str
    normalized_value: Any
    unit: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None
    validation_status: ValidationStatus = ValidationStatus.PASS
    validation_note: Optional[str] = None
    extraction_tier: ExtractionTier = ExtractionTier.TIER1_NATIVE


# ---------------------------------------------------------------------------
# Extracted Entity Schemas
# ---------------------------------------------------------------------------

class MudProperties(BaseModel):
    """Mud program properties extracted from DDR header table."""
    model_config = ConfigDict(extra="forbid")

    mud_weight_ppg: Optional[ExtractedField] = None
    funnel_viscosity_sec: Optional[ExtractedField] = None
    plastic_viscosity_cp: Optional[ExtractedField] = None
    yield_point_lbf_100sqft: Optional[ExtractedField] = None
    water_loss_ml_30min: Optional[ExtractedField] = None
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


class DrillingParameters(BaseModel):
    """Bit run and BHA drilling parameters."""
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


class FormationTop(BaseModel):
    """Stratigraphic formation tops and lithology markers."""
    model_config = ConfigDict(extra="forbid")

    formation_name: str
    top_md_m: Optional[ExtractedField] = None
    top_tvd_m: Optional[ExtractedField] = None
    base_md_m: Optional[ExtractedField] = None
    lithology_description: Optional[str] = None
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


class NPTRecord(BaseModel):
    """IADC Non-Productive Time record."""
    iadc_code: Optional[str] = None
    description: str
    start_time_hhmm: Optional[str] = None
    end_time_hhmm: Optional[str] = None
    npt_hours: Optional[ExtractedField] = None
    depth_md_m: Optional[ExtractedField] = None
    cost_usd_estimate: Optional[float] = None


class DrillingEvent(BaseModel):
    """Normalized drilling hazard event from DDR/WCR narrative."""
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    event_type: EventType = EventType.UNKNOWN
    severity: Severity = Severity.MEDIUM
    depth_start_md_m: Optional[Union[ExtractedField, float]] = None
    depth_end_md_m: Optional[Union[ExtractedField, float]] = None
    formation: Optional[str] = None
    raw_narrative: str = ""
    loss_rate_bbl_hr: Optional[Union[ExtractedField, float]] = None
    npt_hours: Optional[Union[ExtractedField, float]] = None
    mitigation_description: Optional[str] = None
    outcome: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    bounding_box: Optional[BoundingBox] = None

    @property
    def remediation_action(self) -> str:
        return self.mitigation_description or ""


class CasingRecord(BaseModel):
    """Casing string and shoe depth record."""
    casing_size_inches: Optional[ExtractedField] = None
    shoe_depth_md_m: Optional[ExtractedField] = None
    top_of_cement_md_m: Optional[ExtractedField] = None
    grade: Optional[str] = None
    weight_lbft: Optional[ExtractedField] = None


# ---------------------------------------------------------------------------
# Page & Document Aggregates
# ---------------------------------------------------------------------------

class PageExtractionResult(BaseModel):
    """Results extracted from a single PDF page."""
    page_number: int
    is_scanned: bool = False
    extraction_tier: ExtractionTier
    processing_time_ms: float
    raw_text_preview: str = ""
    mud_properties: Optional[MudProperties] = None
    drilling_parameters: Optional[DrillingParameters] = None
    formation_tops: List[FormationTop] = Field(default_factory=list)
    npt_records: List[NPTRecord] = Field(default_factory=list)
    drilling_events: List[DrillingEvent] = Field(default_factory=list)
    casing_records: List[CasingRecord] = Field(default_factory=list)
    page_confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class DocumentExtractionResult(BaseModel):
    """Master output schema for a fully processed DDR or WCR document."""
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(default_factory=lambda: f"DOC-{uuid.uuid4().hex[:12].upper()}")
    job_id: str = ""
    source_filename: str
    document_type: DocumentType = DocumentType.UNKNOWN
    well_name: Optional[str] = None
    operator: Optional[str] = None
    report_date: Optional[str] = None

    total_pages: int = 0
    pages_processed: int = 0
    scanned_pages: int = 0
    template_used: Optional[str] = None

    extraction_started_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    extraction_completed_at: Optional[str] = None
    total_processing_time_ms: float = 0.0

    pages: List[PageExtractionResult] = Field(default_factory=list)

    all_formation_tops: List[FormationTop] = Field(default_factory=list)
    all_npt_records: List[NPTRecord] = Field(default_factory=list)
    all_drilling_events: List[DrillingEvent] = Field(default_factory=list)
    all_casing_records: List[CasingRecord] = Field(default_factory=list)
    mud_properties: List[MudProperties] = Field(default_factory=list)

    total_npt_hours: float = 0.0
    validation_status: ValidationStatus = ValidationStatus.PASS

    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    flagged_fields_count: int = 0
    physics_violations_count: int = 0
    witsml_compliant: bool = True

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
# API Job Payloads
# ---------------------------------------------------------------------------

class IngestJobStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IngestJobResponse(BaseModel):
    job_id: str
    filename: str
    status: IngestJobStatus = IngestJobStatus.QUEUED
    message: str = "Document queued for processing"
    submitted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class JobStatusResponse(BaseModel):
    job_id: str
    status: IngestJobStatus
    progress_percent: int = Field(ge=0, le=100, default=0)
    current_page: int = 0
    total_pages: int = 0
    message: str = ""
    document_id: Optional[str] = None
    error: Optional[str] = None


class BenchmarkScore(BaseModel):
    metric: str
    value: float
    unit: str
    reference_system: str
    reference_value: float
    status: str
