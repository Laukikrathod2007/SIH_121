"""
Physics Engine -- Telemetry Models & Canonical Contracts.

Implements the official Module 5 Section 46-47 Telemetry Schema.
Standardizes channels, quality flags, engineering units, and envelopes.
Compatible with WITSML Log objects and real-time streaming buses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field


class ChannelQuality(str, Enum):
    GOOD = "GOOD"
    SUSPECT = "SUSPECT"
    BAD = "BAD"
    IMPUTED = "IMPUTED"


class ProvenanceTier(str, Enum):
    OBSERVED = "OBSERVED"
    SYNTHETIC = "SYNTHETIC"
    INFERRED = "INFERRED"


class DepthRecord(BaseModel):
    md_m: float = Field(..., description="Measured depth in meters")
    tvd_m: float = Field(..., description="True vertical depth in meters")
    tvdss_m: float = Field(..., description="True vertical depth subsea in meters")


class FormationRecord(BaseModel):
    name: str = Field("Unknown", description="Active formation name")
    xi: float = Field(0.0, description="Stratigraphic dimensionless coordinate [0..1]")
    top_tvdss_m: float = Field(0.0, description="Formation top TVDSS in meters")
    base_tvdss_m: float = Field(0.0, description="Formation base TVDSS in meters")


class TelemetryChannels(BaseModel):
    # Drilling mechanics
    rop_m_hr: float = Field(0.0, description="Rate of penetration, m/hr")
    rpm: float = Field(0.0, description="Surface rotary speed, rpm")
    bit_rpm: float = Field(0.0, description="Downhole bit rotary speed, rpm")
    wob_kn: float = Field(0.0, description="Weight on bit, kN")
    torque_kn_m: float = Field(0.0, description="Surface drilling torque, kN.m")
    hookload_kn: float = Field(0.0, description="Hookload, kN")
    overpull_kn: float = Field(0.0, description="Mechanical drag / overpull, kN")
    mse_mpa: float = Field(0.0, description="Mechanical specific energy, MPa")
    d_exponent: float = Field(1.0, description="Corrected d-exponent, dimensionless")
    stick_slip_index: float = Field(0.0, description="Stick-slip severity index [0..1+]")

    # Hydraulics
    flow_in_lpm: float = Field(0.0, description="Mud pump flow rate in, L/min")
    flow_out_lpm: float = Field(0.0, description="Mud return flow rate out, L/min")
    standpipe_pressure_bar: float = Field(0.0, description="Standpipe pressure, bar")
    annular_pressure_bar: float = Field(0.0, description="Bottomhole annular pressure, bar")
    bhp_bar: float = Field(0.0, description="Bottomhole pressure, bar")
    pit_volume_m3: float = Field(0.0, description="Active pit volume, m3")
    mud_weight_gcc: float = Field(1.20, description="Surface mud weight, g/cc")
    ecd_gcc: float = Field(1.20, description="Equivalent circulating density, g/cc")

    # Pressure Margins
    pp_margin_bar: float = Field(0.0, description="Pore pressure margin (BHP - P_pore), bar")
    fg_margin_bar: float = Field(0.0, description="Fracture gradient margin (P_frac - BHP), bar")

    # Flow rates for influx & loss
    q_loss_lpm: float = Field(0.0, description="Formation fluid loss rate, L/min")
    q_influx_lpm: float = Field(0.0, description="Formation kick/influx rate, L/min")

    # Hole Cleaning
    cuttings_concentration: float = Field(0.0, description="Annular solids concentration [0..1]")

    # Trajectory & Environment
    inclination_deg: float = Field(0.0, description="Wellbore inclination, degrees")
    azimuth_deg: float = Field(0.0, description="Wellbore azimuth, degrees")
    temperature_c: float = Field(50.0, description="Circulating temperature at bit, deg C")


class TelemetryQuality(BaseModel):
    overall: float = Field(1.0, description="Overall telemetry health [0..1]")
    channel_qualities: Dict[str, float] = Field(default_factory=dict)
    flagged_channels: Dict[str, ChannelQuality] = Field(default_factory=dict)


class TelemetryEnvelope(BaseModel):
    """
    Canonical Telemetry Message Envelope for eRTMAC-NWIS streaming bus.
    Matches Module 5 Section 47 specification.
    """
    well_id: str
    wellbore_id: str = "DEFAULT"
    sequence: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    simulation_time_s: float
    depth: DepthRecord
    formation: FormationRecord
    channels: TelemetryChannels
    quality: TelemetryQuality
    provenance: Dict[str, str] = Field(
        default_factory=lambda: {
            "source": "NWIS_PHYSICS_ENGINE",
            "tier": ProvenanceTier.SYNTHETIC.value,
            "version": "1.0.0",
        }
    )
