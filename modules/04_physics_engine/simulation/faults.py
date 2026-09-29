"""
Physics Engine -- Fault & Scenario Engine.

Implements Module 5 Sections 38-43 fault perturbations:
- NORMAL
- LOST_CIRCULATION
- KICK_OVERPRESSURE
- STUCK_PIPE
- STICK_SLIP
- WASHOUT
- POOR_HOLE_CLEANING

CORE PHILOSOPHY:
Faults modify PHYSICAL PARAMETERS consumed by the mechanics, hydraulics,
and mass-balance equations. They NEVER directly modify sensor readings or telemetry!
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class ScenarioType(str, Enum):
    NORMAL = "NORMAL"
    LOST_CIRCULATION = "LOST_CIRCULATION"
    KICK_OVERPRESSURE = "KICK_OVERPRESSURE"
    STUCK_PIPE = "STUCK_PIPE"
    STICK_SLIP = "STICK_SLIP"
    WASHOUT = "WASHOUT"
    POOR_HOLE_CLEANING = "POOR_HOLE_CLEANING"


@dataclass
class ScenarioDefinition:
    scenario_id: str
    scenario_type: ScenarioType
    severity: float = 1.0  # Multiplier [0.0 .. 3.0+]
    start_sim_time_s: Optional[float] = None
    start_md_m: Optional[float] = None
    duration_s: Optional[float] = None  # None = permanent until cleared
    custom_parameters: Dict[str, float] = field(default_factory=dict)


class FaultEngine:
    """
    Manages active scenarios and evaluates physical parameter multipliers
    for each simulation step.
    """

    def __init__(self):
        self.active_scenarios: Dict[str, ScenarioDefinition] = {}

    def inject_scenario(
        self,
        scenario_type: ScenarioType,
        severity: float = 1.0,
        start_sim_time_s: Optional[float] = None,
        start_md_m: Optional[float] = None,
        duration_s: Optional[float] = None,
        custom_params: Optional[Dict[str, float]] = None,
    ) -> str:
        """Injects a scenario into the active fault registry."""
        scenario_id = f"{scenario_type.value}_{len(self.active_scenarios) + 1}"
        definition = ScenarioDefinition(
            scenario_id=scenario_id,
            scenario_type=scenario_type,
            severity=severity,
            start_sim_time_s=start_sim_time_s,
            start_md_m=start_md_m,
            duration_s=duration_s,
            custom_parameters=custom_params or {},
        )
        self.active_scenarios[scenario_id] = definition
        return scenario_id

    def clear_scenarios(self) -> None:
        """Clears all active scenarios back to NORMAL state."""
        self.active_scenarios.clear()

    clear_all = clear_scenarios
    clear = clear_scenarios

    def remove_scenario(self, scenario_id: str) -> bool:
        if scenario_id in self.active_scenarios:
            del self.active_scenarios[scenario_id]
            return True
        return False

    def evaluate_multipliers(
        self,
        sim_time_s: float,
        md_m: float,
    ) -> Dict[str, float]:
        """
        Calculates composite physical parameter multipliers for the active simulation step.
        """
        multipliers = {
            "leakoff_multiplier": 1.0,
            "fracture_pressure_multiplier": 1.0,
            "pore_pressure_multiplier": 1.0,
            "influx_multiplier": 1.0,
            "friction_multiplier": 1.0,
            "cuttings_drag_multiplier": 1.0,
            "torsional_damping_multiplier": 1.0,
            "static_friction_multiplier": 1.0,
            "washout_severity": 0.0,
            "cuttings_slip_multiplier": 1.0,
            "dysfunction_factor": 1.0,
        }

        for scen in list(self.active_scenarios.values()):
            # Check time trigger
            if scen.start_sim_time_s is not None and sim_time_s < scen.start_sim_time_s:
                continue
            # Check depth trigger
            if scen.start_md_m is not None and md_m < scen.start_md_m:
                continue
            # Check expiry
            if scen.duration_s is not None and scen.start_sim_time_s is not None:
                if sim_time_s > (scen.start_sim_time_s + scen.duration_s):
                    continue

            sev = max(0.1, scen.severity)

            if scen.scenario_type == ScenarioType.LOST_CIRCULATION:
                # Weakened/depleted fracture threshold and high leakoff coefficient
                multipliers["fracture_pressure_multiplier"] = max(0.60, 1.0 - 0.22 * sev)
                multipliers["leakoff_multiplier"] *= (4.0 * sev)
            elif scen.scenario_type == ScenarioType.KICK_OVERPRESSURE:
                # Elevates formation pore pressure above mud overbalance (e.g. gas charged / overpressured zone)
                multipliers["pore_pressure_multiplier"] = 1.35 + 0.10 * (sev - 1.0)
                multipliers["influx_multiplier"] *= (3.0 * sev)
            elif scen.scenario_type == ScenarioType.STUCK_PIPE:
                # Multiplies wall friction, increases cuttings drag, impairs penetration
                multipliers["friction_multiplier"] *= (2.8 * sev)
                multipliers["cuttings_drag_multiplier"] *= (2.2 * sev)
                multipliers["dysfunction_factor"] *= max(0.05, 1.0 / (2.5 * sev))
            elif scen.scenario_type == ScenarioType.STICK_SLIP:
                # Increases static-to-dynamic friction difference and lowers torsional damping
                multipliers["static_friction_multiplier"] = 2.2 * sev
                multipliers["torsional_damping_multiplier"] = max(0.1, 0.25 / sev)
            elif scen.scenario_type == ScenarioType.WASHOUT:
                # Hydraulic nozzle/pipe breach
                multipliers["washout_severity"] += (1.0 * sev)
            elif scen.scenario_type == ScenarioType.POOR_HOLE_CLEANING:
                # Particle slip velocity increases, annular solids bed forms
                multipliers["cuttings_slip_multiplier"] *= (2.0 * sev)
                multipliers["cuttings_drag_multiplier"] *= (1.8 * sev)

            # Apply any explicit custom overrides
            for k, v in scen.custom_parameters.items():
                multipliers[k] = v

        return multipliers

    def list_active_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "scenario_id": s.scenario_id,
                "type": s.scenario_type.value,
                "severity": s.severity,
                "start_sim_time_s": s.start_sim_time_s,
                "start_md_m": s.start_md_m,
                "duration_s": s.duration_s,
            }
            for s in self.active_scenarios.values()
        ]
