"""
ML Data Engineering Pipeline for eRTMAC-NWIS Module 5.
"""

from data_pipeline.models import (
    ProvenanceClass,
    EventPhase,
    DataRecordMetadata,
    NormalizedTelemetryPoint,
    MultiHorizonLabels,
)
from data_pipeline.ingestion import TelemetryIngestor
from data_pipeline.cleaner import UnitStandardizer, TelemetryCleaner
from data_pipeline.alignment import DepthTimeAligner
from data_pipeline.feature_engine import FeatureEngine
from data_pipeline.labeler import HazardLabeler
from data_pipeline.splitter import DatasetSplitter
from data_pipeline.synthetic_generator import (
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
