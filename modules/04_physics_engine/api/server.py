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
  GET    /api/v3/predictive/alerts/{well_id}/history
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
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Imports use the canonical `app.modules.physics` / `app.modules.predictive_analytics`
# packages (adapters whose __path__ point at modules/04_physics_engine and
# modules/05_predictive_analytics -- see Backend/app/modules/*/__init__.py),
# so no sys.path manipulation is needed or performed.
# ---------------------------------------------------------------------------
MODULE_04_ROOT = Path(__file__).resolve().parent.parent

from app.modules.physics.simulation.engine import DrillingPhysicsEngine
from app.modules.physics.simulation.faults import ScenarioType
from app.modules.physics.simulation.ertmac_adapter import ERTMACAdapter, ERTMACFeedSource
from app.modules.physics.api.auth import require_api_key, rate_limit, auth_enabled, RATE_LIMIT_ENABLED, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
# API_KEY is intentionally NOT imported as a bare name here: `from ... import
# API_KEY` binds the value at import time, so a test (or anything else)
# patching app.core.auth.API_KEY afterwards would never be seen by this
# module -- auth_enabled() avoids this already (it's a function, so it
# always reads the live module global); physics_stream() below needs the
# current value too, so it goes through this same module reference instead.
import app.core.auth as _shared_auth

from app.modules.predictive_analytics.predictive.realtime_inference import RealTimeRiskInferenceService  # noqa: E402

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
ertmac_adapter = ERTMACAdapter()

_engine_lock = asyncio.Lock()
# RealTimeRiskInferenceService.process_telemetry_point() appends to a rolling
# history buffer on the instance, so the singleton above is NOT safe to call
# concurrently. Inference now runs in a worker thread (to keep sklearn/XGBoost
# off the event loop), which makes that reachable, so serialise it.
_risk_lock = threading.Lock()
_historian: deque = deque(maxlen=2000)
_ws_clients: set = set()
# Caps concurrent WS connections -- previously unbounded, which combined
# with the lack of auth below made /api/v3/physics/stream an unmitigated
# resource-exhaustion surface. Override with NWIS_WS_MAX_CLIENTS.
MAX_WS_CLIENTS = int(os.environ.get("NWIS_WS_MAX_CLIENTS", "50"))
# Last known {md, formation} per well_id, populated by /predictive/evaluate.
# ActiveAlert (Module 05/06) does not carry depth/formation on the alert
# object itself -- only the fused risk payload that produced it does -- so
# this small cache is what lets GET /predictive/alerts/{well_id} answer the
# frontend AlertAdvisory contract's measured_depth_m/formation fields.
_last_known_position: Dict[str, Dict[str, Any]] = {}


class _SimRuntime:
    is_running: bool = False
    # Wall-clock monotonic deadline after which _sim_loop pauses itself.
    # None whenever the sim is not running.
    auto_pause_at: float | None = None


runtime = _SimRuntime()

# The continuously-running twin is a demo/analysis affordance, not a process
# that needs to advance unattended forever: nothing reads the twin once the
# operator navigates away, and on a small single-worker host an indefinitely
# stepping background task is the one piece of work that keeps running with
# no client left to serve it. So a run started over HTTP carries a deadline
# and the loop pauses itself when it expires -- clicking start again simply
# extends it. 0 disables the deadline entirely (an unattended long-run rig
# deployment would set that, having the resources for it).
SIM_MAX_RUN_SECONDS = float(os.environ.get("NWIS_SIM_MAX_RUN_SECONDS", "900"))

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
    if ertmac_adapter.active_source != ERTMACFeedSource.DIGITAL_TWIN:
        env_dict = ertmac_adapter.step_witsml()
    else:
        _, envelope = engine.step()
        env_dict = envelope.model_dump()
        curr_rop = env_dict.get("channels", {}).get("rop_m_hr", 8.0)
        curr_md = env_dict.get("depth", {}).get("md_m", engine.state.md_m)
        env_dict["dynamic_lead_time"] = ertmac_adapter.compute_dynamic_lead_time(
            current_md_m=curr_md,
            current_rop_m_hr=curr_rop,
        )
    _historian.append(env_dict)
    with _risk_lock:
        risk_service.process_telemetry_point(env_dict)
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
    # Every iteration is wrapped: this task is created once, at startup, and
    # nothing ever awaits it, so an exception escaping here would cancel the
    # loop permanently and silently -- the twin would simply stop advancing
    # for the life of the process, with is_running still reporting True and
    # no traceback anywhere. Containing it per-iteration keeps one bad step
    # (a transient engine or broadcast error) from being terminal, and makes
    # it visible in the log instead.
    while True:
        interval = 0.15
        try:
            if runtime.is_running:
                if (
                    runtime.auto_pause_at is not None
                    and time.monotonic() >= runtime.auto_pause_at
                ):
                    runtime.is_running = False
                    runtime.auto_pause_at = None
                    logger.info(
                        f"Simulation auto-paused after {SIM_MAX_RUN_SECONDS:.0f}s "
                        "(NWIS_SIM_MAX_RUN_SECONDS); POST /api/v3/physics/start to resume"
                    )
                else:
                    async with _engine_lock:
                        env_dict = _step_and_record()
                    await _broadcast(env_dict)
                    interval = engine.config.dt_s / max(0.1, engine.config.speed_multiplier)
                    interval = max(0.02, min(interval, 1.0))
        except asyncio.CancelledError:
            # Shutdown (lifespan cancels this task) -- must propagate, not
            # be swallowed as "one bad iteration".
            raise
        except Exception:
            logger.exception("Simulation step failed; pausing the twin")
            runtime.is_running = False
            runtime.auto_pause_at = None
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

# CORS is configured once, centrally, in Backend/app/main.py -- this
# module's own `app` instance only ever runs standalone (e.g. direct
# module-level dev/test invocation), never as the real served app
# (Backend/app/integrations/_mount.py copies only `.router.routes` from
# this app onto the gateway, never its middleware), so a CORSMiddleware
# registered here was dead code in the one place CORS actually matters.


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
    engine_ok = engine is not None and getattr(engine, "state", None) is not None
    anom_ok = bool(getattr(risk_service.anomaly_detector, "_is_fitted", False))
    xgb_ok = bool(getattr(risk_service.xgboost_classifier, "_is_fitted", False))
    is_healthy = engine_ok and anom_ok and xgb_ok

    return {
        "service": "NWIS Physics Digital Twin & Predictive Risk API",
        "version": "1.0.0",
        "status": "healthy" if is_healthy else "degraded",
        "engine": {
            "well_id": engine.well_id,
            "is_running": runtime.is_running,
            "sim_time_s": round(engine.state.sim_time_s, 2),
            "md_m": round(engine.state.md_m, 2),
            "active_scenarios": len(engine.faults.active_scenarios),
            "historian_size": len(_historian),
            "ws_clients": len(_ws_clients),
            "ertmac": ertmac_adapter.get_status(),
        },
        "predictive": {
            "anomaly_detector_fitted": anom_ok,
            "xgboost_fitted": xgb_ok,
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
        # Seconds left before the twin pauses itself, so a client can show
        # the deadline rather than having the sim appear to stop on its own.
        # None when not running, or when the deadline is disabled.
        "auto_pause_in_s": (
            round(max(0.0, runtime.auto_pause_at - time.monotonic()), 1)
            if runtime.is_running and runtime.auto_pause_at is not None
            else None
        ),
    }


@app.get("/api/v3/physics/status", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_status():
    return _status_dict()


@app.post("/api/v3/physics/start", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_start():
    runtime.is_running = True
    # Starting (or re-starting) always extends the deadline from now, so an
    # operator actively driving the sim is never cut off mid-session -- only
    # a run everybody has walked away from reaches it.
    runtime.auto_pause_at = (
        time.monotonic() + SIM_MAX_RUN_SECONDS if SIM_MAX_RUN_SECONDS > 0 else None
    )
    return _status_dict()


@app.post("/api/v3/physics/pause", tags=["Physics"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def physics_pause():
    runtime.is_running = False
    runtime.auto_pause_at = None
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
# A browser WebSocket constructor cannot set custom headers, so the shared
# NWIS_API_KEY is accepted as a `?api_key=` query parameter instead of the
# X-API-Key header every other route uses -- same shared-key model,
# different transport (the same limitation Module 02's SSE live_replay()
# faced, solved there by using fetch()+ReadableStream instead of the native
# EventSource constructor; no equivalent manual socket API exists in the
# browser for WebSocket, so a query-param token is the standard fallback).
# Rejected BEFORE accept() with WS close code 1008 (policy violation), not
# after, so an unauthenticated client never receives a single frame.
# ---------------------------------------------------------------------------

@app.websocket("/api/v3/physics/stream")
async def physics_stream(websocket: WebSocket, api_key: Optional[str] = Query(default=None)):
    if auth_enabled() and not (api_key and secrets.compare_digest(api_key, _shared_auth.API_KEY)):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing or invalid api_key.")
        return

    if len(_ws_clients) >= MAX_WS_CLIENTS:
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="Server is at capacity.")
        return

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
def predictive_evaluate(body: EvaluateRequest):
    telemetry = body.telemetry
    if not isinstance(telemetry, dict) or not telemetry:
        raise HTTPException(status_code=400, detail="telemetry payload is required")

    # risk_service is a module-level singleton whose process_telemetry_point()
    # appends to a rolling history buffer on the instance, so it is not safe to
    # run concurrently. This handler is a plain `def`, which FastAPI runs in its
    # threadpool, so two in-flight evaluates really can land here at once.
    with _risk_lock:
        fused_output = risk_service.process_telemetry_point(telemetry_envelope=telemetry)

    well_id = fused_output.get("well_id", "DEFAULT")
    _last_known_position[well_id] = {
        "md": fused_output.get("md", 0.0),
        "formation": fused_output.get("formation", "Unknown"),
    }

    raw_alerts = fused_output.get("alerts", [])

    # Pass 4: best-effort write-through of this telemetry tick + any alerts
    # it produced into the canonical PostgreSQL schema. Already decimated
    # to the frontend's ~1 Hz evaluate cadence (see db/__init__.py's module
    # docstring) -- never raises on a database outage.
    #
    # It DOES block for the duration of the write, and this comment used to
    # claim otherwise. That was harmless only because the write stayed off the
    # event loop: this handler is a plain `def`, so FastAPI runs it in a worker
    # thread. It must stay a plain `def` -- as an `async def` the SELECT+INSERT
    # below would run ON the event loop and stall every other request, the
    # physics loop and the platform healthcheck along with it.
    try:
        from app.modules.physics.db import service as db_sync
        db_sync.sync_evaluation(telemetry, raw_alerts)
    except Exception as exc:
        logger.debug(f"Telemetry/alert write-through raised unexpectedly (non-fatal): {exc}")

    fused_output["alerts"] = [_alert_to_advisory(a) for a in raw_alerts]
    return fused_output


@app.get("/api/v3/predictive/alerts/{well_id:path}/history", tags=["Predictive"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
def predictive_get_alert_history(well_id: str, limit: int = 100):
    """Read path for the persisted `alerts` table (Pass 6) -- distinct
    from predictive_get_alerts below, which reflects the live in-memory
    advisory engine's current session only. Three honest states: see
    db/service.py::get_alert_history's own docstring. "unavailable" (DB
    configured but unreachable) is a 503 with no `alerts` key, never a
    silently-empty 200 -- same never-silent-fallback contract module 02's
    migrated routes already use.

    Registered BEFORE predictive_get_alerts below: both use a `:path`
    converter for well_id (well IDs like "15/9-F-12" contain slashes), and
    Starlette matches routes in registration order -- the plain
    `{well_id:path}` route would otherwise greedily swallow ".../history"
    into well_id itself and this route would never be reached. Confirmed
    live: this exact failure mode happened once during this pass with the
    routes in the other order (well_id resolved to "15/9-F-12/history")."""
    from app.modules.physics.db import service as db_sync
    result = db_sync.get_alert_history(well_id, limit=limit)
    if result["status"] == "unavailable":
        raise HTTPException(status_code=503, detail="Alert history is temporarily unavailable")
    return result


@app.get("/api/v3/predictive/alerts/{well_id:path}", tags=["Predictive"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
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


# ---------------------------------------------------------------------------
# eRTMAC (Real-Time Monitoring and Analysis Center) & WITSML Feed Endpoints
# ---------------------------------------------------------------------------

class ERTMACSelectRequest(BaseModel):
    source: str
    well_id: Optional[str] = None


@app.get("/api/v3/ertmac/status", tags=["eRTMAC"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def ertmac_status():
    """Returns the live status, active well, and replay stats for the eRTMAC WITSML adapter."""
    return ertmac_adapter.get_status()


@app.get("/api/v3/ertmac/sources", tags=["eRTMAC"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def ertmac_sources():
    """Lists available eRTMAC real-time feed sources (Digital Twin, Volve real WITSML, external feed)."""
    return [
        {
            "id": ERTMACFeedSource.DIGITAL_TWIN.value,
            "name": "Drilling Physics Digital Twin (Simulated Rig)",
            "type": "SIMULATED",
            "description": "High-fidelity mathematical digital twin with hydraulics, mechanics, and fault scenarios.",
        },
        {
            "id": ERTMACFeedSource.VOLVE_15_9_F12.value,
            "name": "Equinor Volve 15/9-F-12 (Real WITSML Stream)",
            "type": "REAL_WITSML",
            "description": "Real WITSML 1.4.1.1 depth trajectory and log stream from Equinor Volve Field well 15/9-F-12.",
        },
        {
            "id": ERTMACFeedSource.VOLVE_15_9_F1.value,
            "name": "Equinor Volve 15/9-F-1 (Real WITSML Stream)",
            "type": "REAL_WITSML",
            "description": "Real WITSML 1.4.1.1 trajectory and drilling log stream from Equinor Volve Field well 15/9-F-1.",
        },
        {
            "id": ERTMACFeedSource.EXTERNAL_WITSML.value,
            "name": "Live Rig WITSML / ETP Stream",
            "type": "EXTERNAL",
            "description": "Live production rig connectivity via WITSML 1.4.1.1 or Energistics Transfer Protocol (ETP).",
        },
    ]


@app.post("/api/v3/ertmac/select", tags=["eRTMAC"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def ertmac_select_source(req: ERTMACSelectRequest):
    """Switches the active eRTMAC real-time feed source between digital twin and real Volve WITSML streams."""
    try:
        source_enum = ERTMACFeedSource(req.source)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source '{req.source}'. Available: {[s.value for s in ERTMACFeedSource]}",
        )
    return ertmac_adapter.select_source(source_enum, req.well_id)


@app.get("/api/v3/ertmac/lead-time", tags=["eRTMAC"], dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def ertmac_dynamic_lead_time(
    depth_m: float = Query(..., description="Current bit measured depth (m)"),
    rop_m_hr: float = Query(..., description="Current drilling penetration rate (m/hr)"),
    hazard_depth_m: Optional[float] = Query(None, description="Target hazard depth (m)"),
):
    """Calculates real-time dynamic lead time to nearest risk corridor: Delta_t = (MD_hazard - MD_bit) / ROP."""
    return ertmac_adapter.compute_dynamic_lead_time(
        current_md_m=depth_m,
        current_rop_m_hr=rop_m_hr,
        hazard_depth_m=hazard_depth_m,
    )

