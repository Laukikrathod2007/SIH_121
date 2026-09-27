"""
NWIS Engine 04 — Stratigraphic Depth (ξ) Correlation & Horizon Alignment Engine.

Implements the complete Module 4 subsurface correlation chain:

    MD -> Directional Trajectory (Minimum Curvature) -> TVD -> TVDSS
       -> Formation Identification (top <= depth < base)
       -> Stratigraphic Coordinate ξ = (d_tvdss - top_tvdss) / thickness
       -> Formation Uncertainty Propagation (sigma_xi)
       -> Structural Fault-Block Barrier Gating (POSSIBLE_FAULT_BOUNDARY)
       -> Equivalent Offset TVDSS = offset_top + ξ * offset_thickness
       -> Historical Event & NPT Horizon Search (baseline ±50m TVDSS window)
       -> Traceable Provenance & Visual Bounding Box Evidence

Mathematical Formulations:
  Stratigraphic Coordinate (ξ):
    ξ(d) = (d_tvdss - Z_top) / (Z_base - Z_top) ∈ [0.0, 1.0]
    ξ = 0.0 -> exact formation top
    ξ = 0.5 -> exact formation midpoint
    ξ = 1.0 -> exact formation base
    ξ < 0.0 or ξ > 1.0 -> outside formation bounds

  Uncertainty Propagation:
    sigma_xi = sqrt((sigma_top / thickness)^2 + (sigma_thick * (d - top) / thickness^2)^2)

  Offset Horizon Mapping:
    d_offset_tvdss = offset_top + ξ * offset_thickness
    (returns NOT_AVAILABLE if formation unpenetrated in offset)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Any, Tuple

from app.modules.well_intelligence.models.schemas import (
    DrillingEvent,
    FormationTop,
    Well,
    WellTrajectory,
    StructuralFaultStatus,
)
from app.modules.well_intelligence.services.stratigraphic_correlator import (
    tvd_at_md,
    tvdss_at_md,
    formation_at_tvdss,
)

# Baseline historical event search window around the equivalent horizon (Module 4 Sec 10 Step 5)
DEFAULT_SEARCH_WINDOW_M = 50.0


# ---------------------------------------------------------------------------
# Formation TVDSS Bounds & Helpers
# ---------------------------------------------------------------------------

def formation_top_tvdss(top: FormationTop, well: Well) -> float:
    """Returns True Vertical Depth Subsea of formation top."""
    if top.top_tvdss_m is not None:
        return top.top_tvdss_m
    return top.top_tvd_m - well.kb_elevation_m


def formation_base_tvdss(top: FormationTop, well: Well) -> float:
    """Returns True Vertical Depth Subsea of formation base."""
    if top.base_tvdss_m is not None:
        return top.base_tvdss_m
    return formation_top_tvdss(top, well) + top.thickness_m


def find_formation_by_tvdss(
    tops: List[FormationTop],
    well: Well,
    depth_tvdss: float,
) -> Optional[FormationTop]:
    """
    Identifies which formation the given TVDSS falls within.
    Standard rule: top_tvdss <= depth_tvdss < base_tvdss.
    Deepest formation includes the base boundary.
    """
    return formation_at_tvdss(tops, well, depth_tvdss)


# ---------------------------------------------------------------------------
# Stratigraphic Coordinate (ξ) Calculation & Uncertainty
# ---------------------------------------------------------------------------

class XiResult:
    """Result of computing stratigraphic coordinate xi with propagated uncertainty."""

    __slots__ = (
        "formation_name",
        "depth_tvdss",
        "top_tvdss",
        "base_tvdss",
        "thickness_m",
        "xi",
        "in_bounds",
        "confidence",
        "uncertainty_m",
        "uncertainty_xi",
        "provenance_tier",
    )

    def __init__(
        self,
        formation_name: str,
        depth_tvdss: float,
        top_tvdss: float,
        base_tvdss: float,
        thickness_m: float,
        xi: float,
        confidence: float,
        uncertainty_m: float = 5.0,
        uncertainty_xi: float = 0.01,
        provenance_tier: str = "OBSERVED",
    ):
        self.formation_name = formation_name
        self.depth_tvdss = depth_tvdss
        self.top_tvdss = top_tvdss
        self.base_tvdss = base_tvdss
        self.thickness_m = thickness_m
        self.xi = xi
        self.in_bounds = (0.0 <= xi <= 1.0)
        self.confidence = confidence
        self.uncertainty_m = uncertainty_m
        self.uncertainty_xi = uncertainty_xi
        self.provenance_tier = provenance_tier

    def to_dict(self) -> dict:
        return {
            "formation_name": self.formation_name,
            "depth_tvdss_m": round(self.depth_tvdss, 2),
            "top_tvdss_m": round(self.top_tvdss, 2),
            "base_tvdss_m": round(self.base_tvdss, 2),
            "thickness_m": round(self.thickness_m, 2),
            "xi": round(self.xi, 4),
            "in_bounds": self.in_bounds,
            "confidence": round(self.confidence, 4),
            "uncertainty_m": round(self.uncertainty_m, 2),
            "uncertainty_xi": round(self.uncertainty_xi, 4),
            "provenance_tier": self.provenance_tier,
        }


def compute_xi(depth_tvdss: float, formation_top_tvdss_m: float, formation_base_tvdss_m: float) -> float:
    """
    xi = (depth_tvdss - top_tvdss) / thickness
    
    xi == 0.0 -> exact formation top
    xi == 0.5 -> exact formation middle
    xi == 1.0 -> exact formation base
    xi < 0.0  -> above formation
    xi > 1.0  -> below formation
    """
    thickness = formation_base_tvdss_m - formation_top_tvdss_m
    if thickness <= 0:
        raise ValueError(f"Invalid formation thickness ({thickness}m): base must exceed top")
    return (depth_tvdss - formation_top_tvdss_m) / thickness


def xi_to_tvdss(xi: float, offset_top_tvdss: float, offset_thickness_m: float) -> float:
    """
    Given active xi, offset formation top TVDSS, and offset formation thickness,
    calculates offset equivalent TVDSS = offset_top + xi * offset_thickness.
    """
    return offset_top_tvdss + xi * offset_thickness_m


def compute_xi_uncertainty(
    depth_tvdss: float,
    top_tvdss: float,
    thickness: float,
    sigma_top: float = 5.0,
    sigma_thickness: float = 10.0,
) -> float:
    """
    Propagates top and thickness uncertainties into xi uncertainty:
    sigma_xi = sqrt((sigma_top / thickness)^2 + (sigma_thickness * (depth - top) / thickness^2)^2)
    """
    if thickness <= 0:
        return 1.0
    term1 = (sigma_top / thickness) ** 2
    term2 = (sigma_thickness * abs(depth_tvdss - top_tvdss) / (thickness ** 2)) ** 2
    return math.sqrt(term1 + term2)


def compute_xi_for_well(
    well: Well,
    trajectory: Optional[WellTrajectory],
    tops: List[FormationTop],
    md: float,
) -> Optional[XiResult]:
    """
    Full pipeline: MD -> Trajectory (Minimum Curvature) -> TVDSS -> Formation -> xi.
    Returns None if MD is outside all mapped formations.
    """
    depth_tvdss = tvdss_at_md(trajectory, well, md)
    fm = find_formation_by_tvdss(tops, well, depth_tvdss)
    if fm is None:
        return None

    top_z = formation_top_tvdss(fm, well)
    base_z = formation_base_tvdss(fm, well)
    thickness = fm.thickness_m if fm.thickness_m > 0 else (base_z - top_z)
    xi = compute_xi(depth_tvdss, top_z, base_z)

    # Uncertainty propagation
    sigma_top = getattr(fm, "uncertainty_m", 5.0)
    sigma_thick = sigma_top * 1.5
    u_xi = compute_xi_uncertainty(depth_tvdss, top_z, thickness, sigma_top, sigma_thick)

    # Boundary proximity penalty
    confidence = fm.confidence
    if not (0.0 <= xi <= 1.0):
        confidence *= 0.5  # Out of bounds penalty

    prov = getattr(fm, "provenance_tier", "OBSERVED")
    if hasattr(prov, "value"):
        prov = prov.value

    return XiResult(
        formation_name=fm.formation_name,
        depth_tvdss=depth_tvdss,
        top_tvdss=top_z,
        base_tvdss=base_z,
        thickness_m=thickness,
        xi=xi,
        confidence=confidence,
        uncertainty_m=sigma_top,
        uncertainty_xi=u_xi,
        provenance_tier=str(prov),
    )


# ---------------------------------------------------------------------------
# Equivalent Offset Depth Mapping
# ---------------------------------------------------------------------------

def xi_to_tvdss(xi: float, offset_top_tvdss: float, offset_thickness_m: float) -> float:
    """
    Maps active stratigraphic coordinate xi into offset well TVDSS:
    offset_equivalent_tvdss = offset_top + xi * offset_thickness
    """
    return offset_top_tvdss + xi * offset_thickness_m


def check_structural_fault_heuristic(
    active_top_tvdss: float,
    offset_top_tvdss: float,
    distance_km: float,
    max_normal_dip_deg: float = 6.0,
) -> str:
    """
    Heuristic check for potential structural fault boundary.
    If elevation offset exceeds regional structural dip projection by > 150m throw,
    flags as POSSIBLE_FAULT_BOUNDARY (never CONFIRMED_FAULT without seismic proof).
    """
    dist_m = distance_km * 1000.0
    expected_elevation_diff = dist_m * math.tan(math.radians(max_normal_dip_deg))
    actual_diff = abs(active_top_tvdss - offset_top_tvdss)

    if actual_diff > expected_elevation_diff + 150.0:
        return "POSSIBLE_FAULT_BOUNDARY"
    return "SAME_FAULT_BLOCK"


def detect_structural_fault_status(
    active_top_tvdss: float,
    offset_top_tvdss: float,
    distance_km: float,
    max_dip_deg: float = 6.0,
) -> Tuple[StructuralFaultStatus, float]:
    """
    Evaluates vertical throw against structural dip threshold.
    Returns (StructuralFaultStatus, throw_meters).
    """
    throw = abs(active_top_tvdss - offset_top_tvdss)
    status_str = check_structural_fault_heuristic(
        active_top_tvdss=active_top_tvdss,
        offset_top_tvdss=offset_top_tvdss,
        distance_km=distance_km,
        max_normal_dip_deg=max_dip_deg,
    )
    if status_str == "POSSIBLE_FAULT_BOUNDARY":
        return StructuralFaultStatus.POSSIBLE_FAULT_BOUNDARY, throw
    return StructuralFaultStatus.SAME_FAULT_BLOCK, throw


def map_xi_to_offset(
    xi_active: float,
    formation_name: str,
    offset_well: Well,
    offset_tops: List[FormationTop],
    distance_km: float = 1.0,
    active_top_tvdss: Optional[float] = None,
) -> Optional[dict]:
    """
    Finds formation_name in offset well's tops and maps active well's xi.
    Returns None if offset well did NOT penetrate the formation (correlation unavailable).
    """
    offset_top = next((t for t in offset_tops if t.formation_name == formation_name), None)
    if offset_top is None:
        return None

    top_z = formation_top_tvdss(offset_top, offset_well)
    base_z = formation_base_tvdss(offset_top, offset_well)
    thickness = offset_top.thickness_m if offset_top.thickness_m > 0 else (base_z - top_z)
    equiv_tvdss = xi_to_tvdss(xi_active, top_z, thickness)

    structural_status = "SAME_FAULT_BLOCK"
    if active_top_tvdss is not None:
        structural_status = check_structural_fault_heuristic(active_top_tvdss, top_z, distance_km)

    return {
        "well_id": offset_well.well_id,
        "well_name": offset_well.well_name,
        "formation_name": formation_name,
        "offset_top_tvdss_m": round(top_z, 2),
        "offset_base_tvdss_m": round(base_z, 2),
        "offset_thickness_m": round(thickness, 2),
        "equivalent_tvdss_m": round(equiv_tvdss, 2),
        "xi_used": round(xi_active, 4),
        "formation_confidence": offset_top.confidence,
        "uncertainty_m": getattr(offset_top, "uncertainty_m", 5.0),
        "provenance_tier": str(getattr(offset_top, "provenance_tier", "OBSERVED")),
        "structural_status": structural_status,
        "correlation_status": "AVAILABLE",
    }


# ---------------------------------------------------------------------------
# Historical Event Correlation (Horizon Search)
# ---------------------------------------------------------------------------

def search_historical_events(
    events: List[DrillingEvent],
    offset_well: Well,
    offset_trajectory: Optional[WellTrajectory],
    equivalent_tvdss: float,
    window_m: float = DEFAULT_SEARCH_WINDOW_M,
) -> List[dict]:
    """
    Searches historical NPT events in offset well within ±window_m TVDSS of equivalent horizon.
    Returns structured evidence cards with document provenance, page, and bounding box.
    """
    lo = equivalent_tvdss - window_m
    hi = equivalent_tvdss + window_m

    results = []
    for event in events:
        if event.well_id != offset_well.well_id:
            continue

        # Determine event TVDSS
        if event.depth_tvdss_m is not None:
            event_tvdss = event.depth_tvdss_m
            depth_method = "EXPLICIT_TVDSS"
        elif offset_trajectory is not None and offset_trajectory.stations:
            event_tvdss = tvdss_at_md(offset_trajectory, offset_well, event.depth_start_md_m)
            depth_method = "MINIMUM_CURVATURE"
        else:
            event_tvdss = event.depth_start_md_m - offset_well.kb_elevation_m
            depth_method = "VERTICAL_ASSUMPTION"

        if lo <= event_tvdss <= hi:
            delta_depth = abs(event_tvdss - equivalent_tvdss)
            prov = getattr(event, "provenance_tier", "OBSERVED")
            if hasattr(prov, "value"):
                prov = prov.value

            results.append(
                {
                    "event_id": event.event_id,
                    "well_id": event.well_id,
                    "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                    "severity": event.severity,
                    "depth_tvdss_m": round(event_tvdss, 2),
                    "depth_md_m": round(event.depth_start_md_m, 2),
                    "depth_method": depth_method,
                    "delta_to_horizon_m": round(delta_depth, 2),
                    "formation": event.formation,
                    "description": event.raw_narrative,
                    "mitigation": event.mitigation_description,
                    "npt_hours": event.npt_hours,
                    "iadc_npt_code": event.iadc_npt_code,
                    "confidence": event.confidence,
                    "provenance_tier": str(prov),
                    "source_document": event.source_document,
                    "source_page": event.source_page,
                    "bbox": getattr(event, "bbox", None),
                }
            )

    results.sort(key=lambda r: r["delta_to_horizon_m"])
    return results


def compute_correlation_confidence(
    xi_result: XiResult,
    offset_formation_confidence: float,
    events_found: int,
    structural_status: str = "SAME_FAULT_BLOCK",
) -> float:
    """
    Composite correlation confidence score.
    Accounts for formation uncertainties, boundary validity, corroborating events,
    and structural fault penalties (0.20 barrier multiplier if fault boundary).
    """
    bounds_factor = 1.0 if xi_result.in_bounds else 0.5
    evidence_factor = min(1.0, 0.6 + 0.1 * events_found)
    fault_factor = 0.5 if structural_status == "POSSIBLE_FAULT_BOUNDARY" else 1.0

    base = (xi_result.confidence + offset_formation_confidence) / 2.0
    return round(base * bounds_factor * evidence_factor * fault_factor, 4)


# ---------------------------------------------------------------------------
# High-Level Correlation Orchestration
# ---------------------------------------------------------------------------

def correlate_offset_well(
    active_well: Well,
    active_trajectory: Optional[WellTrajectory],
    active_tops: List[FormationTop],
    active_md: float,
    offset_well: Well,
    offset_trajectory: Optional[WellTrajectory],
    offset_tops: List[FormationTop],
    offset_events: List[DrillingEvent],
    distance_km: float = 1.0,
    window_m: float = DEFAULT_SEARCH_WINDOW_M,
) -> dict:
    """
    Executes complete correlation chain for one active-offset well pair.
    """
    xi_result = compute_xi_for_well(active_well, active_trajectory, active_tops, active_md)
    if xi_result is None:
        return {
            "status": "no_active_formation",
            "correlation_status": "NO_ACTIVE_FORMATION",
            "active_well_id": active_well.well_id,
            "offset_well_id": offset_well.well_id,
            "active_md_m": active_md,
            "equivalent_depth_tvdss_m": None,
            "events_found": 0,
            "events": [],
        }

    mapping = map_xi_to_offset(
        xi_active=xi_result.xi,
        formation_name=xi_result.formation_name,
        offset_well=offset_well,
        offset_tops=offset_tops,
        distance_km=distance_km,
        active_top_tvdss=xi_result.top_tvdss,
    )
    if mapping is None:
        return {
            "status": "formation_unavailable_in_offset",
            "correlation_status": "NOT_AVAILABLE",
            "reason": "FORMATION_UNAVAILABLE_IN_OFFSET",
            "active_well_id": active_well.well_id,
            "offset_well_id": offset_well.well_id,
            "active_md_m": active_md,
            "active_xi": xi_result.to_dict(),
            "equivalent_depth_tvdss_m": None,
            "events_found": 0,
            "events": [],
        }

    events = search_historical_events(
        events=offset_events,
        offset_well=offset_well,
        offset_trajectory=offset_trajectory,
        equivalent_tvdss=mapping["equivalent_tvdss_m"],
        window_m=window_m,
    )

    offset_top = next(t for t in offset_tops if t.formation_name == xi_result.formation_name)
    confidence = compute_correlation_confidence(
        xi_result, offset_top.confidence, len(events), mapping["structural_status"]
    )

    return {
        "status": "correlated",
        "correlation_status": "AVAILABLE",
        "active_well_id": active_well.well_id,
        "offset_well_id": offset_well.well_id,
        "active_md_m": active_md,
        "active_xi": xi_result.to_dict(),
        "offset_mapping": mapping,
        "search_window_m": window_m,
        "search_interval_tvdss_m": [
            round(mapping["equivalent_tvdss_m"] - window_m, 2),
            round(mapping["equivalent_tvdss_m"] + window_m, 2),
        ],
        "events_found": len(events),
        "events": events,
        "correlation_confidence": confidence,
    }


def correlate_across_offsets(
    active_well: Well,
    active_trajectory: Optional[WellTrajectory],
    active_tops: List[FormationTop],
    active_md: float,
    offset_wells: List[Well],
    offset_trajectories: Dict[str, Optional[WellTrajectory]],
    offset_tops_map: Dict[str, List[FormationTop]],
    offset_events_map: Dict[str, List[DrillingEvent]],
    window_m: float = DEFAULT_SEARCH_WINDOW_M,
) -> dict:
    """
    Correlates active well against multiple offset wells.
    Excludes the active well from its own offset list.
    """
    xi_result = compute_xi_for_well(active_well, active_trajectory, active_tops, active_md)
    if xi_result is None:
        return {
            "status": "no_active_formation",
            "correlation_status": "NO_ACTIVE_FORMATION",
            "active_well_id": active_well.well_id,
            "active_md_m": active_md,
            "offsets": [],
        }

    offset_results = []
    for ow in offset_wells:
        if ow.well_id == active_well.well_id:
            continue
        o_traj = offset_trajectories.get(ow.well_id)
        o_tops = offset_tops_map.get(ow.well_id, [])
        o_events = offset_events_map.get(ow.well_id, [])
        res = correlate_offset_well(
            active_well=active_well,
            active_trajectory=active_trajectory,
            active_tops=active_tops,
            active_md=active_md,
            offset_well=ow,
            offset_trajectory=o_traj,
            offset_tops=o_tops,
            offset_events=o_events,
            window_m=window_m,
        )
        offset_results.append(res)

    return {
        "status": "correlated",
        "correlation_status": "AVAILABLE",
        "active_well_id": active_well.well_id,
        "active_md_m": active_md,
        "active_xi": xi_result.to_dict(),
        "offsets": offset_results,
    }

