"""
Physics Engine -- REST and WebSocket API Routes.

Exposes:
- POST /api/v1/physics/start
- POST /api/v1/physics/pause
- POST /api/v1/physics/reset
- POST /api/v1/physics/step
- POST /api/v1/physics/speed
- POST /api/v1/physics/operator-inputs
- POST /api/v1/physics/scenario
- DELETE /api/v1/physics/scenario
- GET /api/v1/physics/status
- GET /api/v1/physics/historian
- WebSocket /api/v1/physics/stream
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.modules.physics_engine.controllers.physics_controller import PhysicsController

physics_router = APIRouter(prefix="/physics", tags=["Physics Digital Twin"])
controller = PhysicsController()


class OperatorInputsRequest(BaseModel):
    wob_kn: Optional[float] = Field(None, description="Weight on bit, kN")
    rpm: Optional[float] = Field(None, description="Rotary speed, rpm")
    flow_in_lpm: Optional[float] = Field(None, description="Mud pump flow rate, L/min")
    mud_weight_gcc: Optional[float] = Field(None, description="Active mud weight, g/cc")


class SpeedRequest(BaseModel):
    speed_multiplier: float = Field(..., ge=0.1, le=20.0, description="Simulation speed multiplier")


class ResetRequest(BaseModel):
    initial_md_m: float = Field(2500.0, ge=0.0, description="Initial measured depth in meters")


class ScenarioRequest(BaseModel):
    scenario_type: str = Field(..., description="NORMAL, LOST_CIRCULATION, KICK_OVERPRESSURE, STUCK_PIPE, STICK_SLIP, WASHOUT, POOR_HOLE_CLEANING")
    severity: float = Field(1.0, ge=0.1, le=5.0, description="Fault severity multiplier")
    start_md_m: Optional[float] = Field(None, description="Optional depth trigger")
    duration_s: Optional[float] = Field(None, description="Optional duration in seconds")


@physics_router.post("/start")
async def start_simulation():
    """Start continuous background physics simulation loop."""
    return await controller.start_simulation()


@physics_router.post("/pause")
async def pause_simulation():
    """Pause background physics simulation loop."""
    return await controller.pause_simulation()


@physics_router.post("/step")
def step_simulation():
    """Perform one discrete physics integration step and return canonical telemetry."""
    return controller.step_simulation()


@physics_router.post("/reset")
def reset_simulation(req: ResetRequest):
    """Reset the digital twin to initial state."""
    return controller.reset_simulation(initial_md_m=req.initial_md_m)


@physics_router.post("/speed")
def set_simulation_speed(req: SpeedRequest):
    """Set simulation playback speed multiplier (1x, 2x, 5x, 10x...)."""
    return controller.set_speed(req.speed_multiplier)


@physics_router.post("/operator-inputs")
def update_operator_inputs(req: OperatorInputsRequest):
    """Update surface operator controls (WOB, RPM, Flow Rate, Mud Weight)."""
    return controller.set_operator_inputs(
        wob_kn=req.wob_kn,
        rpm=req.rpm,
        flow_in_lpm=req.flow_in_lpm,
        mud_weight_gcc=req.mud_weight_gcc,
    )


@physics_router.post("/scenario")
def inject_fault_scenario(req: ScenarioRequest):
    """Inject a physical fault perturbation scenario."""
    return controller.inject_scenario(
        scenario_type=req.scenario_type,
        severity=req.severity,
        start_md_m=req.start_md_m,
        duration_s=req.duration_s,
    )


@physics_router.delete("/scenario")
def clear_fault_scenarios():
    """Clear all active fault scenarios back to NORMAL drilling."""
    return controller.clear_scenarios()


@physics_router.get("/status")
def get_simulation_status():
    """Get full state, active scenarios, rates, and latest telemetry."""
    return controller.get_status()


@physics_router.get("/historian")
def get_telemetry_historian(limit: int = Query(100, ge=1, le=1000)):
    """Retrieve recent telemetry records from the in-memory historian buffer."""
    return controller.get_historian(limit=limit)


@physics_router.websocket("/stream")
async def websocket_telemetry_stream(websocket: WebSocket):
    """WebSocket stream publishing live 5-10 Hz canonical telemetry envelopes."""
    await controller.streamer.connect_client(websocket)
    try:
        while True:
            # Keep connection open; receive optional ping or client control messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        controller.streamer.disconnect_client(websocket)
    except Exception:
        controller.streamer.disconnect_client(websocket)
