"""
Data Pipeline -- Stratigraphic Coordinate (xi) Helpers.

The full Module 4 correlation engine (formation-top lookup, offset-well
mapping, historical event search) lives in the well_intelligence module and
is out of scope for this port. `alignment.py` and the test suite only need
the two pure coordinate-mapping formulas below, so they are reproduced here
rather than creating a cross-module dependency on well_intelligence.
"""

from __future__ import annotations


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
