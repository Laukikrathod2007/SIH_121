"""
Physics Engine -- Torsional Dynamics & Stick-Slip Subsystem.

Implements a true 2nd-order torsional oscillator with nonlinear bit friction:
I * theta_ddot + c * theta_dot + k * theta = T_surface - T_bit

State variables:
- theta (twist angle of drillstring, radians)
- theta_dot (difference between surface velocity and bit velocity: omega_surf - omega_bit)

Nonlinear Stribeck Friction:
- Sticking phase: bit is locked (omega_bit = 0). Drillstring twists up as
  surface continues rotating. Torque accumulates: T_reactive = k * theta.
- Slip phase: Once k * theta exceeds static friction threshold T_static,
  bit breaks loose with explosive acceleration (omega_bit spikes to 2x-3x surface RPM).
- Coulomb / viscous decay returns bit toward sticking threshold.

Produces authentic mechanical oscillations, NOT decorative sine waves!
"""

from __future__ import annotations

import math
from typing import Tuple, Dict, Any
from app.modules.physics_engine.models.state import FormationParams, OperatorInputs
from app.modules.physics_engine.models.config import SimulatorConfig


class TorsionalDynamicsEngine:
    """Solves torsional drillstring oscillations, bit stick-slip, and torque vibration."""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        # Drillstring torsional parameters (for ~3000m 5-inch pipe)
        # Rotational inertia of BHA & lower string: I ~ 450 kg.m2
        self.inertia_kg_m2 = 450.0
        # Torsional stiffness: k = (G * J) / L ~ 800 - 1500 N.m/rad for 3000m
        self.base_stiffness_n_m_rad = 1100.0
        # Torsional damping ratio: c ~ 120 N.m.s/rad
        self.base_damping_n_m_s = 140.0
        # History window for stick-slip index calculation
        self._rpm_history = []
        self._history_window = 100

    def step(
        self,
        surface_rpm: float,
        base_torque_kn_m: float,
        formation: FormationParams,
        wob_kn: float,
        current_twist_rad: float,
        current_bit_rpm: float,
        dt_s: float,
        damping_multiplier: float = 1.0,
        static_friction_multiplier: float = 1.0,
    ) -> Dict[str, float]:
        """
        Advances torsional oscillator by dt_s.
        
        Returns:
        - bit_rpm
        - twist_angle_rad
        - dynamic_torque_kn_m
        - stick_slip_index
        - is_stuck (boolean flag)
        """
        omega_surf_rad_s = (surface_rpm * 2.0 * math.pi) / 60.0
        wob_n = max(0.0, wob_kn * 1000.0)
        db_m = self.config.bit_diameter_m

        k = self.base_stiffness_n_m_rad
        c = self.base_damping_n_m_s * max(0.1, damping_multiplier)
        inertia = self.inertia_kg_m2

        # Bit friction torque thresholds
        # T_dynamic = (1/3) * mu_dynamic * WOB * D_bit
        mu_dyn = formation.friction_coefficient
        t_dynamic_n_m = (1.0 / 3.0) * mu_dyn * wob_n * db_m

        # T_static is higher than T_dynamic (Stribeck effect)
        # Multiplied by fault scenario parameter when STICK_SLIP is injected
        stribeck_ratio = 1.5 * max(0.5, static_friction_multiplier)
        t_static_n_m = t_dynamic_n_m * stribeck_ratio

        # Current state:
        theta = current_twist_rad
        omega_bit = (current_bit_rpm * 2.0 * math.pi) / 60.0

        # Sub-step integration loop if dt_s > 0.05s for numerical stability
        sub_dt = 0.02
        steps = max(1, int(math.ceil(dt_s / sub_dt)))
        actual_dt = dt_s / steps

        is_stuck = False
        sticking_velocity_threshold = 0.05  # rad/s (~0.5 RPM)

        for _ in range(steps):
            omega_s = 4.0 * max(1.0, static_friction_multiplier)
            decay = math.exp(-(omega_bit / omega_s))
            t_bit_effective = t_dynamic_n_m + (t_static_n_m - t_dynamic_n_m) * decay

            torque_spring_n_m = k * theta
            if omega_bit < 0.5 and torque_spring_n_m < t_static_n_m:
                # Bit is locked to rock face (Stick phase)
                is_stuck = True
                omega_bit = 0.0
                theta += omega_surf_rad_s * actual_dt
            else:
                is_stuck = False
                torque_net = (k * theta) + (c * (omega_surf_rad_s - omega_bit)) - t_bit_effective
                alpha_bit = torque_net / inertia

                omega_bit = max(0.0, omega_bit + alpha_bit * actual_dt)
                theta += (omega_surf_rad_s - omega_bit) * actual_dt

        # Downhole bit RPM
        bit_rpm = max(0.0, (omega_bit * 60.0) / (2.0 * math.pi))

        # Dynamic torque at surface: Base torque (including wall friction) + spring dynamic fluctuation
        torque_spring_kn_m = (k * theta) / 1000.0
        steady_bit_torque_kn_m = t_dynamic_n_m / 1000.0
        dynamic_fluctuation_kn_m = torque_spring_kn_m - steady_bit_torque_kn_m
        torque_total_kn_m = max(0.1, base_torque_kn_m + 0.5 * dynamic_fluctuation_kn_m)

        # Track history for Stick-Slip Index (SSI)
        if not self._rpm_history and surface_rpm > 0.0:
            self._rpm_history = [surface_rpm] * 20
        self._rpm_history.append(bit_rpm)
        if len(self._rpm_history) > self._history_window:
            self._rpm_history.pop(0)

        # SSI = (RPM_max - RPM_min) / (2 * RPM_mean)
        if len(self._rpm_history) >= 20 and surface_rpm > 5.0:
            rpm_max = max(self._rpm_history)
            rpm_min = min(self._rpm_history)
            rpm_mean = sum(self._rpm_history) / len(self._rpm_history)
            ssi = (rpm_max - rpm_min) / max(1.0, 2.0 * rpm_mean)
        else:
            ssi = 0.0

        return {
            "bit_rpm": bit_rpm,
            "twist_angle_rad": theta,
            "dynamic_torque_kn_m": torque_total_kn_m,
            "stick_slip_index": round(min(2.5, ssi), 3),
            "is_stuck": is_stuck,
        }
