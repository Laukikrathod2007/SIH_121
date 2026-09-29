"""
NWIS Module 04 — FastAPI Application Server
Exposes the drilling-physics digital twin (DrillingPhysicsEngine) and, via a
sibling-path import into Module 05 (see the sys.path insert below, symmetric
to modules/05_predictive_analytics/predictive/realtime_inference.py's own
insert reaching back into this module), the predictive risk-fusion +
alert/advisory engine over HTTP/WebSocket.

Endpoints (all mounted under /api/v3, matching the frontend's `m03` axios
client base and its WebSocket path `/api/v3/physics/stream`):
  GET    /api/v3/physics/status
  POST   /api/v3/physics/start
  POST   /api/v3/physics/pause
  POST   /api/v3/physics/step
  POST   /api/v3/physics/reset
  POST   /api/v3/physics/speed
  POST   /api/v3/physics/scenario
  DELETE /api/v3/physics/scenario
  POST   /api/v3/physics/operator-inputs
  GET    /api/v3/physics/historian
  WS     /api/v3/physics/stream
  POST   /api/v3/predictive/evaluate
  GET    /api/v3/predictive/alerts/{well_id}
  POST   /api/v3/predictive/alerts/mitigate
  GET    /api/v3/predictive/models
  GET    /health                      (no auth; also mirrored at /api/v3/health)

Module 04 owns the single live DrillingPhysicsEngine instance (it is the
simulation authority); Module 05's RealTimeRiskInferenceService is a
singleton reached via the same cross-module sys.path pattern Module 05
already uses to reach back into Module 04's data_pipeline.feature_engine.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import sys
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Path setup — module root first (so `from models...`/`from simulation...`
# resolve, matching tests/conftest.py's pattern), then Module 05's root so
# `from predictive...` resolves. Symmetric to Module 05's own sys.path insert
# that reaches back into this module for `data_pipeline.feature_engine`.
# ---------------------------------------------------------------------------
MODULE_04_ROOT = Path(__file__).resolve().parent.parent
if str(MODULE_04_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_04_ROOT))

MODULE_05_ROOT = MODULE_04_ROOT.parent / "05_predictive_analytics"
if str(MODULE_05_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_05_ROOT))

from simulation.engine import DrillingPhysicsEngine
from simulation.faults import ScenarioType
from api.auth import require_api_key, rate_limit, auth_enabled, RATE_LIMIT_ENABLED, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS

from predictive.realtime_inference import RealTimeRiskInferenceService  # noqa: E402

# ---------------------------------------------------------------------------
# Singletons — one live digital twin, one predictive inference service.
#
# well_id is set to match the frontend's default active well
# (AppContext.tsx: `useState<string>('WELL-NHK-001')`) rather than the
# engine class's own default ("NHK-SIM-001"). Without this, telemetry
# envelopes would stream under a well_id the frontend never queries
# GET /predictive/alerts/{well_id} for, and alerts generated from those
# envelopes would silently never reach AlertsAdvisoryPage. This is the one
# real seam between Module 03/04's synthetic simulation well and Module 02's
# seeded well catalog — see the handback report for the full note.
# ---------------------------------------------------------------------------
engine = DrillingPhysicsEngine(well_id="WELL-NHK-001")
risk_service = RealTimeRiskInferenceService()

_engine_lock = asyncio.Lock()
_historian: deque = deque(maxlen=2000)
_ws_clients: set = set()
# Last known {md, formation} per well_id, populated by /predictive/evaluate.
# ActiveAlert (Module 05/06) does not carry depth/formation on the alert
# object itself -- only the fused risk payload that produced it does -- so
# this small cache is what lets GET /predictive/alerts/{well_id} answer the
# frontend AlertAdvisory contract's measured_depth_m/formation fields.
_last_known_position: Dict[str, Dict[str, Any]] = {}


class _SimRuntime:
    is_running: bool = False


runtime = _SimRuntime()

LOG_DIR = MODULE_04_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(
    LOG_DIR / "nwis_module04_{time:YYYY-MM-DD}.log",
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    enqueue=True,
    level="INFO",
    backtrace=False,
    diagnose=False,
)


# ---------------------------------------------------------------------------
# Simulation loop -- advances the twin at a wall-clock cadence derived from
# config.dt_s / speed_multiplier while running, and broadcasts every step to
# connected WebSocket clients. Per SimulatorConfig's own docstring,
# speed_multiplier only ever affects THIS scheduler cadence, never the
# physics equations (engine.step() is always called with the fixed dt_s).
# ---------------------------------------------------------------------------
def _step_and_record() -> Dict[str, Any]:
    _, envelope = engine.step()
    env_dict = envelope.model_dump()
    _historian.append(env_dict)
    return env_dict


async def _broadcast(env_dict: Dict[str, Any]) -> None:
    if not _ws_clients:
        return
    dead = []
    for ws in list(_ws_clients):
        try:
            await ws.send_json(env_dict)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.discard(ws)


async def _sim_loop() -> None:
    while True:
        if runtime.is_running:
            async with _engine_lock:
                env_dict = _step_and_record()
            await _broadcast(env_dict)
            interval = engine.config.dt_s / max(0.1, engine.config.speed_multiplier)
            interval = max(0.02, min(interval, 1.0))
        else:
            interval = 0.15
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Module 04 Physics Digital Twin + Module 05 Predictive Risk API starting...")
    logger.info(f"Engine well_id={engine.well_id} initial_md_m={engine.state.md_m}")
    task = asyncio.create_task(_sim_loop())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    logger.info("Module 04/05 API shutting down")


app = FastAPI(
    title="NWIS Physics Digital Twin & Predictive Risk API",
    description=(
        "Module 04: Drilling Physics Digital Twin (10-subsystem reduced-order "
        "simulator) + Module 05: Predictive Risk Analytics (Rules + Isolation "
        "Forest + XGBoost fusion) + Module 06: Real-Time Alerts & Mitigation "
        "Advisory, exposed over HTTP/WebSocket."
    ),
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

_default_origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
import os  # noqa: E402
_extra_origins = [o.strip() for o in os.environ.get("NWIS_CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred while processing this request.",
            "path": str(request.url.path),
        },
    )


# ---------------------------------------------------------------------------
# Health (no auth) -- mirrored at both root and the versioned prefix so it
# works whether a caller hits it directly or through the m03 axios client
# (base URL `${M03_BASE}/api/v3`), matching M01/M02's `/api/vN/health`
# convention for that second path.
# ---------------------------------------------------------------------------
def _health_payload() -> Dict[str, Any]:
    return {
        "service": "NWIS Physics Digital Twin & Predictive Risk API",
        "version": "1.0.0",
        "status": "healthy",
        "engine": {
            "well_id": engine.well_id,
            "is_running": runtime.is_running,
            "sim_time_s": round(engine.state.sim_time_s, 2),
            "md_m": round(engine.state.md_m, 2),
            "active_scenarios": len(engine.faults.active_scenarios),
            "historian_size": len(_historian),
            "ws_clients": len(_ws_clients),
        },
        "predictive": {
            "anomaly_detector_fitted": bool(getattr(risk_service.anomaly_detector, "_is_fitted", False)),
            "xgboost_fitted": bool(getattr(risk_service.xgboost_classifier, "_is_fitted", False)),
        },
        "auth": {
            "status": "enabled" if auth_enabled() else "disabled",
            "role": "X-API-Key required on all /api/v3 routes when enabled",
            "rate_limiting": {
                "enabled": RATE_LIMIT_ENABLED,
                "max_requests": RATE_LIMIT_MAX_REQUESTS,
                "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            },
        },
    }


@app.get("/health", tags=["System"])
async def health_root():
    return _health_payload()


@app.get("/api/v3/health", tags=["System"])
async def health_v3():
    return _health_payload()


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "NWIS Physics Digital Twin & Predictive Risk API",
        "docs": "/docs",
        "status": "operational",
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ScenarioRequest(BaseModel):
    scenario_type: str
    severity: float = 1.0
    duration_s: Optional[float] = None


class ResetRequest(BaseModel):
    initial_md_m: float = 2500.0


class SpeedRequest(BaseModel):
    speed_multiplier: float = Field(..., gt=0)


class OperatorInputsRequest(BaseModel):
    wob_kn: Optional[float] = None
    rpm: Optional[float] = None
    flow_in_lpm: Optional[float] = None
    mud_weight_gcc: Optional[float] = None


class EvaluateRequest(BaseModel):
    telemetry: Dict[str, Any]


class MitigateRequest(BaseModel):
    well_id: str
    alert_id: str


# ---------------------------------------------------------------------------
# Physics — status / control
# ---------------------------------------------------------------------------

def _status_dict() -> Dict[str, Any]:
    active = {s["scenario_id"]: s for s in engine.faults.list_active_scenarios()}
    md = round(engine.state.md_m, 2)
    return {
        "is_running": runtime.is_running,
        "speed_multiplier": engine.config.speed_multiplier,
        "sim_time_s": round(engine.state.sim_time_s, 2),
        "measured_depth_m": md,
        # Alias -- AppContext.tsx's pollStatus() accepts either key.
        "md_m": md,
        "active_scenarios": active,
    }


@app.get("/api/v3/physics/status", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_status():
    return _status_dict()


@app.post("/api/v3/physics/start", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_start():
    runtime.is_running = True
    return _status_dict()


@app.post("/api/v3/physics/pause", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_pause():
    runtime.is_running = False
    return _status_dict()


@app.post("/api/v3/physics/step", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_step():
    """Manual single-step -- works regardless of is_running, matching the
    frontend's SimulatorPage 'step' control."""
    async with _engine_lock:
        env_dict = _step_and_record()
    await _broadcast(env_dict)
    return env_dict


@app.post("/api/v3/physics/reset", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_reset(body: ResetRequest):
    async with _engine_lock:
        engine.reset(initial_md_m=body.initial_md_m)
        _historian.clear()
    logger.info(f"Engine reset to initial_md_m={body.initial_md_m}")
    return _status_dict()


@app.post("/api/v3/physics/speed", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_speed(body: SpeedRequest):
    engine.config.speed_multiplier = body.speed_multiplier
    return _status_dict()


@app.post("/api/v3/physics/scenario", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_inject_scenario(body: ScenarioRequest):
    try:
        stype = ScenarioType(body.scenario_type.strip().upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario_type '{body.scenario_type}'. Valid: {[s.value for s in ScenarioType]}",
        )
    async with _engine_lock:
        scenario_id = engine.faults.inject_scenario(
            scenario_type=stype,
            severity=body.severity,
            # Anchored to the current sim clock so the scenario applies
            # immediately AND so duration_s expiry (evaluated relative to
            # start_sim_time_s in faults.py) actually works -- leaving this
            # None makes the fault permanent regardless of duration_s.
            start_sim_time_s=engine.state.sim_time_s,
            duration_s=body.duration_s,
        )
    logger.info(f"Injected scenario {scenario_id} (severity={body.severity}, duration_s={body.duration_s})")
    return {"scenario_id": scenario_id, **_status_dict()}


@app.delete("/api/v3/physics/scenario", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_clear_scenarios():
    async with _engine_lock:
        engine.faults.clear_scenarios()
    return _status_dict()


@app.post("/api/v3/physics/operator-inputs", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_operator_inputs(body: OperatorInputsRequest):
    async with _engine_lock:
        engine.set_operator_inputs(
            wob_kn=body.wob_kn,
            rpm=body.rpm,
            flow_in_lpm=body.flow_in_lpm,
            mud_weight_gcc=body.mud_weight_gcc,
        )
        result = {
            "wob_kn": engine.inputs.wob_kn,
            "rpm": engine.inputs.rpm,
            "flow_in_lpm": engine.inputs.flow_in_lpm,
            "mud_weight_gcc": engine.inputs.mud_weight_gcc,
        }
    return result


@app.get("/api/v3/physics/historian", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_historian(limit: int = Query(100, ge=1, le=2000)):
    return list(_historian)[-limit:]


# ---------------------------------------------------------------------------
# Physics — WebSocket stream
#
# Not gated behind X-API-Key: a browser WebSocket constructor cannot set
# custom headers (the same limitation documented on Module 02's SSE
# live_replay() endpoint), so this is a known, matching gap rather than an
# oversight. It broadcasts read-only telemetry, not a control surface.
# ---------------------------------------------------------------------------

@app.websocket("/api/v3/physics/stream")
async def physics_stream(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"WS client connected ({len(_ws_clients)} total)")
    try:
        while True:
            # Push-only channel; block here so disconnects raise promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning(f"WS client error: {exc}")
    finally:
        _ws_clients.discard(websocket)
        logger.info(f"WS client disconnected ({len(_ws_clients)} remaining)")


# ---------------------------------------------------------------------------
# Predictive risk (Module 05) + Alerts/Advisory (Module 06)
# ---------------------------------------------------------------------------

_STATUS_MAP = {"ACTIVE": "DETECTED", "ACKNOWLEDGED": "ACKNOWLEDGED", "MITIGATED": "MITIGATED", "CLEARED": "CLEARED"}
_URGENCY_MAP = {"CRITICAL": "IMMEDIATE", "WARNING": "HIGH", "ADVISORY": "MEDIUM", "CLEARED": "MEDIUM"}


def _steps_from_description(description: str) -> List[str]:
    """MitigationAction.description is a numbered plain-text protocol
    ("1. Reduce flow rate... 2. Spot 25 bbl..."); the frontend's
    RecommendedAction.steps wants a list, so split on the numbering."""
    if not description:
        return []
    parts = re.split(r"\d+\.\s*", description)
    return [p.strip() for p in parts if p.strip()]


def _alert_to_advisory(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Reconciles Module 05/06's ActiveAlert shape (alert_id, well_id,
    timestamp, hazard_type, severity, trigger_reason, evidence_chain,
    recommended_mitigation, status) against the frontend's AlertAdvisory
    contract (frontend/src/types/index.ts) exactly: alert_id, well_id,
    hazard_type, severity, measured_depth_m, formation, headline,
    causal_evidence_chain, recommended_action{action_id,title,steps,urgency},
    status, created_at. Field names differ (trigger_reason -> headline,
    evidence_chain -> causal_evidence_chain, recommended_mitigation ->
    recommended_action with a derived `steps` list and `urgency`); status
    vocab differs too (ActiveAlert's "ACTIVE" -> frontend's "DETECTED").
    measured_depth_m/formation aren't on ActiveAlert at all -- they're
    filled from _last_known_position, populated by /predictive/evaluate.
    """
    well_id = alert.get("well_id", "")
    pos = _last_known_position.get(well_id, {})
    mitigation = alert.get("recommended_mitigation") or {}
    severity = alert.get("severity", "ADVISORY")
    return {
        "alert_id": alert.get("alert_id"),
        "well_id": well_id,
        "hazard_type": alert.get("hazard_type"),
        "severity": severity,
        "measured_depth_m": pos.get("md", 0.0),
        "formation": pos.get("formation", "Unknown"),
        "headline": alert.get("trigger_reason", ""),
        "causal_evidence_chain": alert.get("evidence_chain", []),
        "recommended_action": {
            "action_id": mitigation.get("action_id", ""),
            "title": mitigation.get("title", ""),
            "steps": _steps_from_description(mitigation.get("description", "")),
            "urgency": _URGENCY_MAP.get(severity, "MEDIUM"),
        },
        "status": _STATUS_MAP.get(alert.get("status", "ACTIVE"), "DETECTED"),
        "created_at": alert.get("timestamp", datetime.now(timezone.utc).isoformat()),
    }


@app.post("/api/v3/predictive/evaluate", tags=["Predictive"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def predictive_evaluate(body: EvaluateRequest):
    telemetry = body.telemetry
    if not isinstance(telemetry, dict) or not telemetry:
        raise HTTPException(status_code=400, detail="telemetry payload is required")

    fused_output = risk_service.process_telemetry_point(telemetry_envelope=telemetry)

    well_id = fused_output.get("well_id", "DEFAULT")
    _last_known_position[well_id] = {
        "md": fused_output.get("md", 0.0),
        "formation": fused_output.get("formation", "Unknown"),
    }
    fused_output["alerts"] = [_alert_to_advisory(a) for a in fused_output.get("alerts", [])]
    return fused_output


@app.get("/api/v3/predictive/alerts/{well_id}", tags=["Predictive"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def predictive_get_alerts(well_id: str):
    alerts = risk_service.get_active_alerts(well_id)
    return [_alert_to_advisory(a) for a in alerts]


@app.post("/api/v3/predictive/alerts/mitigate", tags=["Predictive"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def predictive_mitigate_alert(body: MitigateRequest):
    alert = risk_service.apply_mitigation_action(well_id=body.well_id, alert_id=body.alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert '{body.alert_id}' not found for well '{body.well_id}'")
    return _alert_to_advisory(alert)


@app.get("/api/v3/predictive/models", tags=["Predictive"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def predictive_models():
    """No formal model registry exists yet -- this is a static description
    of the three fusion pillars actually wired into RiskFusionEngine
    (predictive/risk_fusion_engine.py), with live fitted/unfitted status."""
    return [
        {
            "model_id": "baseline_hazard_rules",
            "type": "rule_engine",
            "version": "1.0.0",
            "status": "ACTIVE",
            "hazards": ["lost_circulation", "stuck_pipe", "kick", "torque_drag", "cementing", "washout"],
            "description": "Deterministic physics-threshold rules with hysteresis debouncing (Module 05 Part G).",
        },
        {
            "model_id": "isolation_forest_anomaly",
            "type": "isolation_forest",
            "version": "1.0.0",
            "status": "ACTIVE" if getattr(risk_service.anomaly_detector, "_is_fitted", False) else "UNFITTED_FALLBACK",
            "hazards": ["multivariate_anomaly"],
            "description": "Unsupervised multivariate anomaly scoring over the 55-feature trailing window.",
        },
        {
            "model_id": "xgboost_hazard_classifier",
            "type": "xgboost_classifier",
            "version": "1.0.0",
            "status": "ACTIVE" if getattr(risk_service.xgboost_classifier, "_is_fitted", False) else "UNFITTED_FALLBACK",
            "hazards": ["LOST_CIRCULATION", "STUCK_PIPE", "KICK", "TORQUE_DRAG", "WASHOUT"],
            "description": (
                "Supervised multi-hazard classifier. When unfitted (no trained artifact on disk), "
                "the fusion engine redistributes its weight across the rules/anomaly/historical "
                "pillars rather than silently voting NORMAL -- see risk_fusion_engine.py."
            ),
        },
    ]
