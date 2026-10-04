"""
Physics Engine -- Sensor Model Subsystem.

Implements Module 5 Sections 44-45:
Observes internal ground truth and applies real-world measurement effects:
- Latency / time delay (FIFO buffer)
- Scale & static bias
- Gaussian noise (sigma)
- Continuous drift
- Quantization / resolution
- Saturation / clip bounds
- Random dropout
- Sensor health quality evaluation [0.0 .. 1.0]

Ensures the physical state and observed telemetry remain strictly separate.
"""

from __future__ import annotations

import collections
import math
import random
from typing import Dict, Any, Optional, Tuple
from app.modules.physics.models.telemetry import ChannelQuality


class ChannelSensor:
    """Simulates one physical sensor channel with real-world sensor imperfections."""

    def __init__(
        self,
        name: str,
        unit: str,
        scale: float = 1.0,
        bias: float = 0.0,
        noise_sigma: float = 0.0,
        drift_rate_per_sec: float = 0.0,
        delay_steps: int = 0,
        resolution: Optional[float] = None,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        dropout_probability: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.name = name
        self.unit = unit
        self.scale = scale
        self.bias = bias
        self.noise_sigma = noise_sigma
        self.drift_rate = drift_rate_per_sec
        self.delay_steps = max(0, delay_steps)
        self.resolution = resolution
        self.min_val = min_val
        self.max_val = max_val
        self.dropout_probability = dropout_probability

        self._rng = random.Random(seed)
        self._delay_buffer = collections.deque(maxlen=self.delay_steps + 1)
        self._last_valid_value = 0.0
        self._total_drift = 0.0

    def sample(self, true_value: float, dt_s: float) -> Tuple[float, float, ChannelQuality]:
        """
        Samples the sensor given the internal true physical value.
        
        Returns:
        - measured_value: observed value
        - quality: confidence/quality score [0.0 .. 1.0]
        - status: ChannelQuality enum (GOOD, SUSPECT, BAD)
        """
        # 1. Update drift
        self._total_drift += self.drift_rate * dt_s

        # 2. Latency buffer (delay_steps)
        self._delay_buffer.append(true_value)
        if len(self._delay_buffer) <= self.delay_steps:
            val_delayed = true_value
        else:
            val_delayed = self._delay_buffer[0]

        # 3. Check random sensor dropout
        if self.dropout_probability > 0.0 and self._rng.random() < self.dropout_probability:
            # Dropout event: sensor loses lock or holds stale value
            return self._last_valid_value, 0.20, ChannelQuality.BAD

        # 4. Scale, Bias, Drift, and Noise
        measured = (val_delayed * self.scale) + self.bias + self._total_drift
        if self.noise_sigma > 0.0:
            measured += self._rng.gauss(0.0, self.noise_sigma)

        # 5. Quantization
        if self.resolution and self.resolution > 0.0:
            measured = round(measured / self.resolution) * self.resolution

        # 6. Saturation / Clip bounds
        quality = 1.0
        status = ChannelQuality.GOOD

        if self.min_val is not None and measured < self.min_val:
            measured = self.min_val
            quality = 0.50
            status = ChannelQuality.SUSPECT

        if self.max_val is not None and measured > self.max_val:
            measured = self.max_val
            quality = 0.50
            status = ChannelQuality.SUSPECT

        self._last_valid_value = measured
        return measured, quality, status


class SensorArray:
    """Manages the full suite of surface and downhole sensors."""

    def __init__(self, seed: Optional[int] = 42):
        self.seed = seed
        self.sensors: Dict[str, ChannelSensor] = {}
        self._init_default_sensors()

    def _init_default_sensors(self) -> None:
        s = self.seed
        # Surface Drilling Mechanics Sensors
        self.sensors["rop_m_hr"] = ChannelSensor("rop_m_hr", "m/hr", noise_sigma=0.3, resolution=0.1, min_val=0.0, seed=s)
        self.sensors["rpm"] = ChannelSensor("rpm", "rpm", noise_sigma=0.5, resolution=0.5, min_val=0.0, seed=s + 1 if s else None)
        self.sensors["wob_kn"] = ChannelSensor("wob_kn", "kN", noise_sigma=1.2, resolution=0.5, min_val=0.0, seed=s + 2 if s else None)
        self.sensors["torque_kn_m"] = ChannelSensor("torque_kn_m", "kN.m", noise_sigma=0.25, resolution=0.1, min_val=0.0, seed=s + 3 if s else None)
        self.sensors["hookload_kn"] = ChannelSensor("hookload_kn", "kN", noise_sigma=2.0, resolution=1.0, min_val=0.0, seed=s + 4 if s else None)

        # Downhole MWD Sensors (higher latency due to mud-pulse / EM transmission ~ 2-5 sec delay)
        self.sensors["bit_rpm"] = ChannelSensor("bit_rpm", "rpm", noise_sigma=1.5, delay_steps=2, resolution=1.0, min_val=0.0, seed=s + 5 if s else None)
        self.sensors["annular_pressure_bar"] = ChannelSensor("annular_pressure_bar", "bar", noise_sigma=0.4, delay_steps=2, resolution=0.1, min_val=0.0, seed=s + 6 if s else None)

        # Hydraulics & Pit Sensors
        self.sensors["flow_in_lpm"] = ChannelSensor("flow_in_lpm", "L/min", noise_sigma=6.0, resolution=1.0, min_val=0.0, seed=s + 7 if s else None)
        self.sensors["flow_out_lpm"] = ChannelSensor("flow_out_lpm", "L/min", noise_sigma=12.0, resolution=2.0, min_val=0.0, seed=s + 8 if s else None)
        self.sensors["standpipe_pressure_bar"] = ChannelSensor("standpipe_pressure_bar", "bar", noise_sigma=0.6, resolution=0.2, min_val=0.0, seed=s + 9 if s else None)
        self.sensors["pit_volume_m3"] = ChannelSensor("pit_volume_m3", "m3", noise_sigma=0.08, resolution=0.05, min_val=0.0, seed=s + 10 if s else None)
        self.sensors["mud_weight_gcc"] = ChannelSensor("mud_weight_gcc", "g/cc", noise_sigma=0.005, resolution=0.01, min_val=0.5, seed=s + 11 if s else None)

    def observe(self, true_state_dict: Dict[str, float], dt_s: float) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, ChannelQuality]]:
        """
        Passes true physical variables through sensor models to generate telemetry.
        """
        observed_values: Dict[str, float] = {}
        qualities: Dict[str, float] = {}
        statuses: Dict[str, ChannelQuality] = {}

        for channel, sensor in self.sensors.items():
            true_val = true_state_dict.get(channel, 0.0)
            obs, q, st = sensor.sample(true_val, dt_s)
            observed_values[channel] = obs
            qualities[channel] = q
            statuses[channel] = st

        return observed_values, qualities, statuses
