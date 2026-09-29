"""
ML Data Engineering Pipeline -- Models & Metadata.

Implements Module 5 Data Pipeline Section 1:
- Explicit data classes with provenance: OBSERVED, SYNTHETIC, INFERRED.
- Strict tracking of source, source_id, provenance, dataset_version, and processing_version.
- Multi-horizon hazard labels and event phases.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ProvenanceClass(str, Enum):
    OBSERVED = "OBSERVED"    # Real measured rig data (e.g. Volve, FORCE, NDR)
    SYNTHETIC = "SYNTHETIC"  # Physics digital twin generated
    INFERRED = "INFERRED"    # Derived via mathematical/geological models


class EventPhase(str, Enum):
    NORMAL = "NORMAL"
    PRE_EVENT = "PRE_EVENT"      # Developing precursors within warning horizon
    EVENT = "EVENT"              # Active fault / dysfunction
    RECOVERY = "RECOVERY"        # Post-event stabilization


class DataRecordMetadata(BaseModel):
    source: str = Field("NWIS_DIGITAL_TWIN", description="Origin of telemetry")
    source_id: str = Field("NHK-SIM-001", description="Well or dataset identifier")
    provenance: ProvenanceClass = Field(ProvenanceClass.SYNTHETIC)
    dataset_version: str = Field("1.0.0")
    processing_version: str = Field("1.0.0")


class NormalizedTelemetryPoint(BaseModel):
    timestamp_utc: str
    sim_time_s: float
    md_m: float
    tvd_m: float
    tvdss_m: float
    formation_name: str
    xi: float

    # Channels (normalized)
    channels: Dict[str, float]
    # Channel qualities [0..1]
    qualities: Dict[str, float]
    # Imputation flags
    is_imputed: Dict[str, bool] = Field(default_factory=dict)
    outlier_flags: Dict[str, bool] = Field(default_factory=dict)

    metadata: DataRecordMetadata = Field(default_factory=DataRecordMetadata)


class MultiHorizonLabels(BaseModel):
    """Multi-horizon hazard labels for predictive risk training."""
    event_phase: EventPhase = EventPhase.NORMAL
    active_hazard: Optional[str] = None
    severity: float = 0.0

    # Time-horizon predictions (Probability of event within X seconds)
    hazard_5m_ahead: bool = False
    hazard_10m_ahead: bool = False
    hazard_20m_ahead: bool = False
    hazard_30m_ahead: bool = False

    # Depth-horizon predictions (Probability of event within X meters ahead)
    hazard_10m_depth_ahead: bool = False
    hazard_20m_depth_ahead: bool = False
    hazard_50m_depth_ahead: bool = False
    hazard_100m_depth_ahead: bool = False
