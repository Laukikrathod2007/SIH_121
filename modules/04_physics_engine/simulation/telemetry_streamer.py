"""
Physics Engine -- Live Telemetry Streamer & WebSocket Broadcaster.

Implements Module 5 Sections 47-48:
- Asynchronous simulation loop running at 10-20 Hz physics frequency.
- Rate decoupler broadcasting to frontend WebSockets at 5-10 Hz.
- Historian ring buffer storing recent telemetry records.
- Complete simulation lifecycle controls: start, pause, step, reset, speed, scenario injection.
- WITSML interoperability boundary.
"""

from __future__ import annotations

import asyncio
import collections
import json
from typing import Dict, Any, List, Optional, Set
from fastapi import WebSocket

from loguru import logger
from app.modules.physics.simulation.engine import DrillingPhysicsEngine
from app.modules.physics.simulation.faults import ScenarioType
from app.modules.physics.models.telemetry import TelemetryEnvelope


class LiveTelemetryStreamer:
    """Manages real-time simulation execution and WebSocket broadcast."""

    _instance: Optional[LiveTelemetryStreamer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.engine = DrillingPhysicsEngine()
        self.is_running = False
        self.speed_multiplier = 1.0
        self.physics_hz = 25.0      # 40 ms physics timestep
        self.broadcast_hz = 25.0    # 40 ms telemetry broadcast
        self.historian = collections.deque(maxlen=2000)
        self.active_websockets: Set[WebSocket] = set()
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._initialized = True

    async def connect_client(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_websockets.add(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_websockets)}")
        # Send latest record immediately if available
        if self.historian:
            await websocket.send_json(self.historian[-1])

    def disconnect_client(self, websocket: WebSocket) -> None:
        self.active_websockets.discard(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_websockets)}")

    async def broadcast(self, data: Dict[str, Any]) -> None:
        stale = []
        # Snapshot: clients connect/disconnect during the awaits below, and mutating the set
        # mid-iteration raised RuntimeError that killed the whole simulation loop.
        for ws in list(self.active_websockets):
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(ws)
        for s in stale:
            self.active_websockets.discard(s)

    async def start(self) -> None:
        """Starts real-time background simulation loop."""
        async with self._lock:
            if self.is_running:
                return
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Physics simulation streamer started.")

    async def pause(self) -> None:
        """Pauses real-time simulation."""
        async with self._lock:
            self.is_running = False
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                self._task = None
            logger.info("Physics simulation streamer paused.")

    def step_once(self) -> Dict[str, Any]:
        """Performs a single deterministic simulation step."""
        dt = 1.0 / self.physics_hz
        _, envelope = self.engine.step(dt_s=dt)
        data = envelope.model_dump()
        self.historian.append(data)
        return data

    def reset(self, initial_md_m: float = 2500.0) -> Dict[str, Any]:
        """Resets engine to start state."""
        self.engine.reset(initial_md_m=initial_md_m)
        self.historian.clear()
        dt = 1.0 / self.physics_hz
        _, envelope = self.engine.step(dt_s=dt)
        data = envelope.model_dump()
        self.historian.append(data)
        logger.info(f"Physics engine reset to MD={initial_md_m}m")
        return data

    def set_speed(self, multiplier: float) -> None:
        self.speed_multiplier = max(0.1, min(20.0, multiplier))
        logger.info(f"Simulation speed set to {self.speed_multiplier}x")

    def set_operator_inputs(
        self,
        wob_kn: Optional[float] = None,
        rpm: Optional[float] = None,
        flow_in_lpm: Optional[float] = None,
        mud_weight_gcc: Optional[float] = None,
    ) -> Dict[str, float]:
        self.engine.set_operator_inputs(
            wob_kn=wob_kn,
            rpm=rpm,
            flow_in_lpm=flow_in_lpm,
            mud_weight_gcc=mud_weight_gcc,
        )
        return {
            "wob_kn": self.engine.inputs.wob_kn,
            "rpm": self.engine.inputs.rpm,
            "flow_in_lpm": self.engine.inputs.flow_in_lpm,
            "mud_weight_gcc": self.engine.inputs.mud_weight_gcc,
        }

    def inject_scenario(
        self,
        scenario_type: str,
        severity: float = 1.0,
        start_md_m: Optional[float] = None,
        duration_s: Optional[float] = None,
    ) -> str:
        scen_enum = ScenarioType(scenario_type)
        scen_id = self.engine.faults.inject_scenario(
            scenario_type=scen_enum,
            severity=severity,
            start_sim_time_s=self.engine.state.sim_time_s,
            start_md_m=start_md_m,
            duration_s=duration_s,
        )
        logger.warning(f"Injected fault scenario: {scen_id} (Type={scen_enum.value}, Severity={severity})")
        return scen_id

    def clear_scenarios(self) -> None:
        self.engine.faults.clear_scenarios()
        logger.info("Cleared all active fault scenarios.")

    def get_status(self) -> Dict[str, Any]:
        latest = self.historian[-1] if self.historian else None
        return {
            "is_running": self.is_running,
            "speed_multiplier": self.speed_multiplier,
            "physics_hz": self.physics_hz,
            "broadcast_hz": self.broadcast_hz,
            "connected_clients": len(self.active_websockets),
            "historian_records": len(self.historian),
            "sim_time_s": round(self.engine.state.sim_time_s, 2),
            "md_m": round(self.engine.state.md_m, 2),
            "formation": self.engine.state.formation_name,
            "active_scenarios": self.engine.faults.list_active_scenarios(),
            "operator_inputs": {
                "wob_kn": self.engine.inputs.wob_kn,
                "rpm": self.engine.inputs.rpm,
                "flow_in_lpm": self.engine.inputs.flow_in_lpm,
                "mud_weight_gcc": self.engine.inputs.mud_weight_gcc,
            },
            "latest_record": latest,
        }

    async def _run_loop(self) -> None:
        """Internal worker executing physics integration and throttled broadcasting."""
        physics_dt = 1.0 / self.physics_hz
        broadcast_every = max(1, round(self.physics_hz / self.broadcast_hz))
        step_idx = 0

        loop = asyncio.get_event_loop()
        next_tick = loop.time()
        try:
            while self.is_running:
                # Wall-clock cadence is fixed; speed only scales sim_dt (scaling both squared the speed).
                sim_dt = physics_dt * self.speed_multiplier
                _, envelope = self.engine.step(dt_s=sim_dt)
                record = envelope.model_dump()
                self.historian.append(record)

                # Step-count decimation (not wall-clock) so jittery ticks never drop a broadcast.
                step_idx += 1
                if step_idx % broadcast_every == 0:
                    await self.broadcast(record)

                # Deadline scheduling: Windows sleep granularity (~15 ms) overshoots each sleep,
                # so aim at absolute ticks to hold the average rate instead of drifting to ~21 Hz.
                next_tick += physics_dt
                now = loop.time()
                if next_tick < now - 0.25:
                    next_tick = now  # fell far behind (e.g. debugger pause); don't burst to catch up
                await asyncio.sleep(max(0.0, next_tick - now))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception(f"Error in physics simulation loop: {exc}")
            self.is_running = False
