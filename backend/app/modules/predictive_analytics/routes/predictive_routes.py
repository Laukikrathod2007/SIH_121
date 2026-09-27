"""
Module 5 Predictive Risk Analytics -- REST API Routes.

Exposes:
- POST /api/v1/predictive/evaluate: Evaluates live telemetry point and returns fused multi-hazard risk.
- POST /api/v1/predictive/train-and-benchmark: Executes benchmark pipeline and updates ML_MODEL_REPORT.md.
- GET /api/v1/predictive/models: Lists registered model versions.
- GET /api/v1/predictive/status: Returns service health and active buffer depths.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter

from app.modules.predictive_analytics.services.realtime_inference import RealTimeRiskInferenceService
from app.modules.predictive_analytics.evaluation.model_benchmarking import ModelBenchmarkPipeline
from app.modules.predictive_analytics.registry.model_registry import ModelRegistry

predictive_router = APIRouter(prefix="/predictive", tags=["Predictive Risk Analytics"])
inference_service = RealTimeRiskInferenceService()
registry = ModelRegistry()


class EvaluateTelemetryRequest(BaseModel):
    telemetry: Dict[str, Any]
    correlation_confidence: Optional[float] = 0.90
    historical_offset_events: Optional[Dict[str, int]] = None


@predictive_router.post("/evaluate")
def evaluate_telemetry_risk(req: EvaluateTelemetryRequest):
    """
    Sub-second online risk inference:
    Evaluates streaming telemetry through rules, anomaly detection, XGBoost, and risk fusion.
    """
    return inference_service.process_telemetry_point(
        telemetry_envelope=req.telemetry,
        historical_offset_events=req.historical_offset_events,
        correlation_confidence=req.correlation_confidence or 0.90,
    )


@predictive_router.post("/train-and-benchmark")
def run_training_benchmark():
    """
    Executes full multi-architecture training and comparative benchmarking.
    Updates docs/ML_MODEL_REPORT.md and registers trained model artifacts.
    """
    pipeline = ModelBenchmarkPipeline()
    res = pipeline.run_full_training_and_benchmarking()
    return res


@predictive_router.get("/models")
def list_registered_models():
    """Returns active models and version metadata from ModelRegistry."""
    return [m.model_dump() for m in registry.list_models()]


@predictive_router.get("/status")
def get_service_status():
    """Returns real-time inference service status and active well buffers."""
    return {
        "status": "operational",
        "service": "eRTMAC-NWIS Predictive Risk Inference Service",
        "active_well_buffers": list(inference_service._telemetry_buffers.keys()),
        "registered_models_count": len(registry.list_models()),
    }


class MitigateAlertRequest(BaseModel):
    well_id: str
    alert_id: str


@predictive_router.post("/alerts/mitigate")
def apply_mitigation(req: MitigateAlertRequest):
    """
    Applies an engineer mitigation action to resolve an active hazard alert.
    """
    alert = inference_service.apply_mitigation_action(well_id=req.well_id, alert_id=req.alert_id)
    if not alert:
        return {"status": "error", "message": f"Alert {req.alert_id} not found for well {req.well_id}"}
    return {"status": "success", "alert": alert}


@predictive_router.get("/alerts/{well_id}")
def get_well_alerts(well_id: str):
    """Returns all active and mitigated alerts for the specified well."""
    return inference_service.get_active_alerts(well_id=well_id)
