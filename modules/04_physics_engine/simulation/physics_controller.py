"""
Physics Engine -- Controller Layer.

Bridges FastAPI endpoints to the LiveTelemetryStreamer singleton.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from simulation.telemetry_streamer import LiveTelemetryStreamer


class PhysicsController:
    """Controller providing high-level operations for drilling digital twin simulation."""

    def __init__(self):
        self.streamer = LiveTelemetryStreamer()

    async def start_simulation(self) -> Dict[str, Any]:
        await self.streamer.start()
        return {"status": "started", "details": self.streamer.get_status()}

    async def pause_simulation(self) -> Dict[str, Any]:
        await self.streamer.pause()
        return {"status": "paused", "details": self.streamer.get_status()}

    def step_simulation(self) -> Dict[str, Any]:
        record = self.streamer.step_once()
        return {"status": "stepped", "telemetry": record}

    def reset_simulation(self, initial_md_m: float = 2500.0) -> Dict[str, Any]:
        record = self.streamer.reset(initial_md_m=initial_md_m)
        return {"status": "reset", "initial_md_m": initial_md_m, "telemetry": record}

    def set_speed(self, multiplier: float) -> Dict[str, Any]:
        self.streamer.set_speed(multiplier)
        return {"status": "success", "speed_multiplier": self.streamer.speed_multiplier}

    def set_operator_inputs(
        self,
        wob_kn: Optional[float] = None,
        rpm: Optional[float] = None,
        flow_in_lpm: Optional[float] = None,
        mud_weight_gcc: Optional[float] = None,
    ) -> Dict[str, Any]:
        updated = self.streamer.set_operator_inputs(
            wob_kn=wob_kn,
            rpm=rpm,
            flow_in_lpm=flow_in_lpm,
            mud_weight_gcc=mud_weight_gcc,
        )
        return {"status": "success", "operator_inputs": updated}

    def inject_scenario(
        self,
        scenario_type: str,
        severity: float = 1.0,
        start_md_m: Optional[float] = None,
        duration_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        scen_id = self.streamer.inject_scenario(
            scenario_type=scenario_type,
            severity=severity,
            start_md_m=start_md_m,
            duration_s=duration_s,
        )
        return {
            "status": "injected",
            "scenario_id": scen_id,
            "scenario_type": scenario_type,
            "severity": severity,
        }

    def clear_scenarios(self) -> Dict[str, Any]:
        self.streamer.clear_scenarios()
        return {"status": "cleared", "active_scenarios": []}

    def get_status(self) -> Dict[str, Any]:
        return self.streamer.get_status()

    def get_historian(self, limit: int = 100) -> List[Dict[str, Any]]:
        records = list(self.streamer.historian)
        return records[-limit:]
