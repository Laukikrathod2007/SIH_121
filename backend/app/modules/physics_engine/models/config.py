"""
Physics Engine -- Simulator Configuration.

Per Module 5 sections 10-11: configurable timestep, playback speed, and
deterministic seeding. Playback speed affects only the scheduler (how much
sim-time elapses per wall-clock step when run live); it must never change
the physical equations themselves -- callers that just want deterministic
physics ticks (tests, batch generation) call `engine.step(dt_s)` directly
and can ignore `speed_multiplier` entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SimulatorConfig:
    # Physics integration timestep, seconds. Module 5 recommends 50-100ms
    # (10-20 Hz) for the physics solver itself.
    dt_s: float = 0.1

    # Playback speed multiplier for live/streaming use (1x, 2x, 5x, 10x...).
    # Does not alter dt_s or any equation; purely a scheduler concern for
    # callers driving the engine in wall-clock time.
    speed_multiplier: float = 1.0

    # Deterministic seed. All stochastic behavior in the engine (sensor
    # noise, fault randomization) must derive from a numpy Generator seeded
    # from this value so runs are reproducible.
    seed: Optional[int] = 42

    # Hydraulic / geometry defaults (SI internally; see Module 5 section 51
    # for the canonical-unit convention)
    hole_diameter_m: float = 0.2159       # 8.5 in
    pipe_od_m: float = 0.127              # 5 in drill pipe OD
    bit_diameter_m: float = 0.2159
    bit_area_m2: float = 0.0366           # pi/4 * bit_diameter^2, precomputed default

    friction_factor: float = 0.03         # Fanning-ish lumped annular friction factor
    flow_length_m: float = 1.0            # placeholder; actual length derives from md_m each step

    gravity_m_s2: float = 9.80665

    # Wellhead elevation for TVDSS conversion (m above MSL)
    wellhead_elevation_m: float = 20.0

    def __post_init__(self):
        import math
        dh = self.hole_diameter_m
        dp = self.pipe_od_m
        self.annulus_area_m2 = (math.pi / 4.0) * (dh**2 - dp**2)
        self.bit_area_m2 = (math.pi / 4.0) * self.bit_diameter_m**2
