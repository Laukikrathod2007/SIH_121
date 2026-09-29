"""
NWIS Module 02 — Live Replay Simulation

Closes PS 26121 outcome vi ("Generate real-time alerts and recommendations")
and doubles as Phase 5's "Live Replay Simulation." Before this, the only way
to get an analysis was a synchronous GET request at a caller-supplied depth —
useful, but not "real-time": nothing pushed updates as the bit advanced.

WHAT THIS ACTUALLY REPLAYS, HONESTLY: the depth progression is driven by the
well's full TRAJECTORY (surface to TD) — not the telemetry stream. That's a
deliberate choice, not an oversight: the synthetic telemetry_stream.json has
exactly one well (WELL-HGJ-012) and covers only an 8-metre depth window
(2128.5-2136.0m) over one simulated hour — replaying THAT alone would barely
move and would never cross a risk corridor boundary, which defeats the point
of a lookahead-alert demo. Driving depth from the trajectory instead means
the simulation traverses the well's real depth range and can actually
demonstrate corridors being approached and entered.

The honest consequence: sensor-anomaly scoring (A_sensor in the R_H(t)
composite) only has genuine telemetry to work with while the simulated depth
is inside that same 2128.5-2136.0m window — engines/risk_corridor_engine.py's
compute_sensor_anomaly() already returns 0.0 when fewer than 10 telemetry
records are available for the current depth, which is correct, existing
behavior, not something this module works around. Outside that window,
A_sensor is correctly silent, not faked.
"""

from __future__ import annotations
import asyncio
from typing import AsyncGenerator, Optional

from app.core.logging import logger
from app.modules.well_intelligence.services.data_store import NWISDataStore
from app.modules.well_intelligence.services.orchestrator import NWISOrchestrator

DEFAULT_TICKS = 80          # how many depth steps across the full replay
DEFAULT_TICK_SECONDS = 0.5  # real seconds between pushed updates


async def replay_well(
    store: NWISDataStore,
    well_id: str,
    n_ticks: int = DEFAULT_TICKS,
    tick_seconds: float = DEFAULT_TICK_SECONDS,
    start_depth_m: Optional[float] = None,
    end_depth_m: Optional[float] = None,
    is_disconnected=None,
) -> AsyncGenerator[dict, None]:
    """
    Async generator: yields one compact analysis summary per tick as the
    simulated bit depth advances from start_depth_m to end_depth_m (default:
    the well's full trajectory range). `is_disconnected` is an optional
    zero-arg async callable (FastAPI's Request.is_disconnected) — checked
    each tick so an abandoned client doesn't leave this loop running forever
    server-side.
    """
    traj = store.all_trajectories.get(well_id)
    if traj is None or not traj.stations:
        raise ValueError(f"No trajectory data for well '{well_id}' — cannot replay")

    depth = start_depth_m if start_depth_m is not None else traj.stations[0].md_m
    depth_end = end_depth_m if end_depth_m is not None else traj.stations[-1].md_m
    if depth_end <= depth:
        raise ValueError(f"end_depth_m ({depth_end}) must be greater than start_depth_m ({depth})")

    step = (depth_end - depth) / max(n_ticks, 1)
    orchestrator = NWISOrchestrator(store)

    logger.info(
        f"Live replay starting: well={well_id} depth {depth:.0f}m -> {depth_end:.0f}m "
        f"in {n_ticks} ticks ({step:.1f}m/tick, {tick_seconds}s/tick)"
    )

    for tick in range(n_ticks + 1):
        if is_disconnected is not None and await is_disconnected():
            logger.info(f"Live replay for {well_id}: client disconnected at tick {tick}, stopping")
            return

        current_depth = min(depth + tick * step, depth_end)
        try:
            result = orchestrator.analyze(active_well_id=well_id, current_depth_m=current_depth)
        except Exception as exc:
            logger.warning(f"Live replay analysis failed at depth {current_depth:.1f}m: {exc}")
            await asyncio.sleep(tick_seconds)
            continue

        from app.modules.well_intelligence.services.alert_center import AlertCenter
        raised = AlertCenter().evaluate(result, source="live_replay")

        yield {
            "alerts": [
                {k: a[k] for k in ("alert_id", "hazard_type", "severity", "title", "message", "lead_distance_m", "offset_wells")}
                for a in raised
            ],
            "corridors_ahead": [
                {
                    "hazard_type": c.hazard_type.value,
                    "from_m": c.depth_start_m,
                    "to_m": c.depth_end_m,
                    "lead_distance_m": c.lead_distance_m,
                    "wells": c.contributing_wells,
                    "event_count": c.event_count,
                }
                for c in result.active_risk_corridors
                if c.lead_distance_m is not None and c.lead_distance_m >= -(c.depth_end_m - c.depth_start_m)
            ][:8],
            "top_offsets": [
                {"well_id": r.well_id, "well_name": r.well_name, "distance_km": r.distance_km, "score": r.dors_score}
                for r in result.offset_rankings[:5]
            ],
            "tick": tick,
            "well_id": well_id,
            "depth_m": round(current_depth, 1),
            "formation_at_bit": result.formation_at_bit,
            "overall_risk_level": result.overall_risk_level.value,
            "alert_message": result.alert_message,
            "hazard_summary": [
                {
                    "hazard_type": h.hazard_type.value,
                    "risk_level": h.risk_level.value,
                    "composite_score": h.composite_score,
                    "m_ml_source": h.m_ml_source,
                }
                for h in result.hazard_assessments
            ],
        }

        await asyncio.sleep(tick_seconds)

    logger.info(f"Live replay for {well_id} complete ({n_ticks} ticks)")
