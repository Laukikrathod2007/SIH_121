"""
ML Data Engineering Pipeline for eRTMAC-NWIS Module 5.
"""

from app.modules.physics_engine.data_pipeline.models import (
    ProvenanceClass,
    EventPhase,
    DataRecordMetadata,
    NormalizedTelemetryPoint,
    MultiHorizonLabels,
)
from app.modules.physics_engine.data_pipeline.ingestion import TelemetryIngestor
from app.modules.physics_engine.data_pipeline.cleaner import UnitStandardizer, TelemetryCleaner
from app.modules.physics_engine.data_pipeline.alignment import DepthTimeAligner
from app.modules.physics_engine.data_pipeline.feature_engine import FeatureEngine
from app.modules.physics_engine.data_pipeline.labeler import HazardLabeler
from app.modules.physics_engine.data_pipeline.splitter import DatasetSplitter
from app.modules.physics_engine.data_pipeline.synthetic_generator import (
    SyntheticDataGenerator,
    QualityGateFailure,
)

__all__ = [
    "ProvenanceClass",
    "EventPhase",
    "DataRecordMetadata",
    "NormalizedTelemetryPoint",
    "MultiHorizonLabels",
    "TelemetryIngestor",
    "UnitStandardizer",
    "TelemetryCleaner",
    "DepthTimeAligner",
    "FeatureEngine",
    "HazardLabeler",
    "DatasetSplitter",
    "SyntheticDataGenerator",
    "QualityGateFailure",
]
