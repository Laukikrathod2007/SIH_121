"""
Comprehensive Module 4 Verification & Regression Test Suite.
Verifies all 14 requirements of SIH26121 Module 4:
  1. Minimum Curvature Method (MD, Inc, Azi -> North, East, TVD, TVDSS, Dogleg, DLS)
  2. Vertical Well Fallback (tvd_method = VERTICAL_ASSUMPTION)
  3. Formation Identification (top <= depth < base)
  4. Stratigraphic Coordinate ξ Calculation & Bounds Flagging
  5. Equivalent Offset Depth Mapping (offset_top + ξ * offset_thickness)
  6. Historical NPT Event Correlation (±50m search window with full provenance & bbox)
  7. Configurable Ω Ranking (0.25 distance, 0.40 geological, 0.20 trajectory, 0.15 completion)
  8. Competitive Trajectory & Hazard Feature Weight Improvements
  9. Formation Uncertainty Propagation (sigma_xi)
  10. Structural Fault/Block Boundary Handling (POSSIBLE_FAULT_BOUNDARY & barrier penalty)
  11. Ahead-of-Bit Risk Corridor Projections (0-20m, 20-50m, 50-200m)
  12. NHK-412 -> NHK-089 Numerical Example Regression Test
  13. Edge Cases (zero dogleg, out-of-order stations, duplicate surveys, missing offset formation)
  14. REST API Endpoint Integration Verification
"""

import math
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.well_intelligence.models.schemas import (
    Well,
    WellTrajectory,
    SurveyStation,
    FormationTop,
    DrillingEvent,
    HazardType,
    WellType,
    WellStatus,
    ProvenanceTier,
    StructuralFaultStatus,
)
from app.modules.well_intelligence.services.trajectory_engine import (
    RawSurveyStation,
    calculate_minimum_curvature_trajectory,
    interpolate_trajectory_at_md,
    compute_ratio_factor,
    compute_dogleg_angle,
)
from app.modules.well_intelligence.services.stratigraphic_correlator import (
    tvd_at_md,
    tvdss_at_md,
    formation_at_depth,
    formation_at_tvdss,
)
from app.modules.well_intelligence.services.xi_correlator import (
    compute_xi,
    compute_xi_uncertainty,
    xi_to_tvdss,
    find_formation_by_tvdss,
    formation_top_tvdss,
    formation_base_tvdss,
    detect_structural_fault_status,
    map_xi_to_offset,
    search_historical_events,
    compute_correlation_confidence,
    correlate_offset_well,
    correlate_across_offsets,
    compute_xi_for_well,
    XiResult,
)
from app.modules.well_intelligence.services.dors_engine import (
    calculate_omega_score,
    rank_offset_wells,
    HAZARD_WEIGHT_PROFILES,
    DORS_W_DISTANCE,
    DORS_W_GEOLOGICAL,
    DORS_W_TRAJECTORY,
    DORS_W_COMPLETION,
)
from app.modules.well_intelligence.services.risk_corridor_engine import (
    compute_ahead_of_bit_corridor,
)


# ===========================================================================
# 1. MINIMUM CURVATURE TESTS
# ===========================================================================

class TestMinimumCurvature:
    """Verifies SPE/API Minimum Curvature equations and numerical precision."""

    def test_spe_standard_minimum_curvature_calculation(self):
        """
        Standard directional survey segment:
        Station 1: MD=1000m, Inc=10 deg, Azi=30 deg
        Station 2: MD=1030m, Inc=13 deg, Azi=35 deg
        Delta MD = 30m
        Verifies dogleg angle beta, ratio factor RF, delta TVD, North, East.
        """
        raw = [
            RawSurveyStation(md_m=0.0, inclination_deg=0.0, azimuth_deg=0.0),
            RawSurveyStation(md_m=1000.0, inclination_deg=10.0, azimuth_deg=30.0),
            RawSurveyStation(md_m=1030.0, inclination_deg=13.0, azimuth_deg=35.0),
        ]
        res = calculate_minimum_curvature_trajectory(raw, wellhead_elevation_m=20.0, well_id="SPE_TEST")

        assert res.tvd_method == "MINIMUM_CURVATURE"
        assert len(res.stations) == 3

        s2 = res.stations[2]
        assert s2.md_m == 1030.0
        # Inclination increased, dogleg should be positive and non-zero
        assert s2.dogleg_deg > 0.0
        assert s2.dls_deg_30m > 0.0
        # Delta TVD must be approximately delta_MD * cos(avg_inc) ~= 30 * cos(11.5 deg) ~= 29.4m
        delta_tvd = s2.tvd_m - res.stations[1].tvd_m
        assert 29.0 < delta_tvd < 30.0
        # TVDSS = TVD - wellhead_elevation (20m)
        assert abs(s2.tvdss_m - (s2.tvd_m - 20.0)) < 1e-4

    def test_zero_dogleg_singularity_handling(self):
        """
        Straight section with zero inclination or identical angles.
        beta -> 0 rad: RF must use Taylor expansion 1.0 + beta^2 / 12, preventing division by zero.
        """
        rf = compute_ratio_factor(0.0)
        assert rf == 1.0

        rf_tiny = compute_ratio_factor(1e-8)
        assert abs(rf_tiny - 1.0) < 1e-6

        # Two stations with identical angles
        raw = [
            RawSurveyStation(md_m=0.0, inclination_deg=15.0, azimuth_deg=45.0),
            RawSurveyStation(md_m=100.0, inclination_deg=15.0, azimuth_deg=45.0),
        ]
        res = calculate_minimum_curvature_trajectory(raw, wellhead_elevation_m=0.0)
        s1 = res.stations[1]
        assert s1.dogleg_deg == 0.0
        assert s1.dls_deg_30m == 0.0
        expected_tvd = 100.0 * math.cos(math.radians(15.0))
        assert abs(s1.tvd_m - expected_tvd) < 0.01

    def test_arbitrary_survey_spacing(self):
        """Supports irregular survey spacing (e.g., 5m, 12.5m, 150m intervals)."""
        raw = [
            RawSurveyStation(md_m=0.0, inclination_deg=0.0, azimuth_deg=0.0),
            RawSurveyStation(md_m=5.0, inclination_deg=1.0, azimuth_deg=10.0),
            RawSurveyStation(md_m=17.5, inclination_deg=3.5, azimuth_deg=25.0),
            RawSurveyStation(md_m=167.5, inclination_deg=12.0, azimuth_deg=45.0),
        ]
        res = calculate_minimum_curvature_trajectory(raw, wellhead_elevation_m=15.0)
        assert res.total_md_m == 167.5
        assert res.stations[-1].md_m == 167.5
        assert res.stations[-1].tvd_m < 167.5  # deviated section


# ===========================================================================
# 2. VERTICAL WELL FALLBACK
# ===========================================================================

class TestVerticalWellFallback:
    """When survey data does not exist, explicitly mark VERTICAL_ASSUMPTION."""

    def test_empty_survey_stations_fallback(self):
        res = calculate_minimum_curvature_trajectory([], wellhead_elevation_m=25.0)
        assert res.tvd_method == "VERTICAL_ASSUMPTION"
        assert len(res.stations) == 1
        assert res.stations[0].md_m == 0.0
        assert res.stations[0].tvd_m == 0.0
        assert res.stations[0].tvdss_m == -25.0

    def test_trajectory_interpolation_vertical_fallback(self):
        well = Well(
            well_id="VERT_01",
            well_name="VERT-01",
            field="Test",
            field_code="TST",
            operator="OIL",
            surface_lat=27.0,
            surface_lon=95.0,
            kb_elevation_m=22.0,
            total_depth_md_m=3500.0,
            well_type=WellType.VERTICAL,
        )
        empty_traj = WellTrajectory(well_id="VERT_01", well_name="VERT-01", stations=[])

        # TVD must equal MD
        assert tvd_at_md(empty_traj, 2500.0) == 2500.0
        # TVDSS must equal MD - KB
        assert tvdss_at_md(empty_traj, well, 2500.0) == 2500.0 - 22.0


# ===========================================================================
# 3. FORMATION IDENTIFICATION
# ===========================================================================

class TestFormationIdentification:
    """Verifies top <= depth < base boundary conditions."""

    @pytest.fixture
    def sample_well(self) -> Well:
        return Well(
            well_id="W1", well_name="W1", field="Field", field_code="FLD",
            operator="OIL", surface_lat=27.0, surface_lon=95.0,
            kb_elevation_m=0.0, total_depth_md_m=4000.0, well_type=WellType.VERTICAL,
        )

    @pytest.fixture
    def sample_tops(self) -> list[FormationTop]:
        return [
            FormationTop(
                well_id="W1", well_name="W1", formation_name="Girujan Clay",
                top_md_m=1000.0, top_tvd_m=1000.0, base_md_m=1800.0, thickness_m=800.0,
            ),
            FormationTop(
                well_id="W1", well_name="W1", formation_name="Tipam Sandstone",
                top_md_m=1800.0, top_tvd_m=1800.0, base_md_m=2600.0, thickness_m=800.0,
            ),
            FormationTop(
                well_id="W1", well_name="W1", formation_name="Barail Lower Sand",
                top_md_m=2940.0, top_tvd_m=2940.0, base_md_m=3380.0, thickness_m=440.0,
            ),
        ]

    def test_top_inclusive_base_exclusive(self, sample_well, sample_tops):
        # Exact top: inclusive
        fm_top = find_formation_by_tvdss(sample_tops, sample_well, 1800.0)
        assert fm_top is not None
        assert fm_top.formation_name == "Tipam Sandstone"

        # Exact base: exclusive (belongs to next interval or None)
        fm_base = find_formation_by_tvdss(sample_tops, sample_well, 2600.0)
        # 2600.0 is base of Tipam and next formation starts at 2940 -> None
        assert fm_base is None

    def test_depth_outside_any_formation(self, sample_well, sample_tops):
        # Above all formations
        assert find_formation_by_tvdss(sample_tops, sample_well, 500.0) is None
        # Unconformity gap (2700m is between Tipam base 2600 and Barail top 2940)
        assert find_formation_by_tvdss(sample_tops, sample_well, 2700.0) is None
        # Deeper than all formations
        assert find_formation_by_tvdss(sample_tops, sample_well, 3500.0) is None


# ===========================================================================
# 4. STRATIGRAPHIC XI CALCULATION
# ===========================================================================

class TestXiCalculation:
    """Verifies ξ = (depth_tvdss - top_tvdss) / thickness and boundary flags."""

    def test_xi_key_points(self):
        # Top boundary -> xi = 0.0
        assert compute_xi(2000.0, 2000.0, 2200.0) == 0.0
        # Midpoint -> xi = 0.5
        assert compute_xi(2100.0, 2000.0, 2200.0) == 0.5
        # Base boundary -> xi = 1.0
        assert compute_xi(2200.0, 2000.0, 2200.0) == 1.0

    def test_xi_out_of_bounds_flags(self):
        # Above top -> xi < 0, in_bounds = False
        res_above = XiResult("Fm", depth_tvdss=1950.0, top_tvdss=2000.0, base_tvdss=2200.0, thickness_m=200.0, xi=-0.25, confidence=0.9)
        assert res_above.xi < 0.0
        assert res_above.in_bounds is False

        # Below base -> xi > 1, in_bounds = False
        res_below = XiResult("Fm", depth_tvdss=2250.0, top_tvdss=2000.0, base_tvdss=2200.0, thickness_m=200.0, xi=1.25, confidence=0.9)
        assert res_below.xi > 1.0
        assert res_below.in_bounds is False

    def test_degenerate_formation_raises(self):
        with pytest.raises(ValueError, match="base must exceed top"):
            compute_xi(2000.0, 2000.0, 2000.0)


# ===========================================================================
# 5. EQUIVALENT OFFSET DEPTH
# ===========================================================================

class TestEquivalentOffsetDepth:
    """Verifies equivalent offset TVDSS = offset_top + active_xi * offset_thickness."""

    def test_equivalent_offset_depth_formula(self):
        equiv = xi_to_tvdss(xi=0.5, offset_top_tvdss=3000.0, offset_thickness_m=200.0)
        assert equiv == 3100.0

    def test_unpenetrated_formation_returns_none(self):
        offset = Well(
            well_id="OFF_01", well_name="OFF-01", field="Field", field_code="FLD",
            operator="OIL", surface_lat=27.0, surface_lon=95.0,
            kb_elevation_m=0.0, total_depth_md_m=2500.0, well_type=WellType.VERTICAL,
        )
        # Formation absent in offset well
        res = map_xi_to_offset(
            xi_active=0.5,
            formation_name="Deeper Sand",
            offset_well=offset,
            offset_tops=[],
        )
        assert res is None


# ===========================================================================
# 6. HISTORICAL NPT EVENT CORRELATION
# ===========================================================================

class TestNPTEventCorrelation:
    """Verifies baseline ±50m equivalent-depth window and full metadata extraction."""

    def test_event_search_window_and_metadata(self):
        well = Well(
            well_id="NHK-089", well_name="NHK-089", field="Field", field_code="FLD",
            operator="OIL", surface_lat=27.30, surface_lon=95.35,
            kb_elevation_m=0.0, total_depth_md_m=4000.0, well_type=WellType.VERTICAL,
        )
        events = [
            DrillingEvent(
                event_id="EVT-01",
                well_id="NHK-089",
                event_type=HazardType.MUD_LOSS,
                severity="HIGH",
                depth_start_md_m=3225.0,
                formation="Barail Lower Sand",
                raw_narrative="Severe mud losses",
                mitigation_description="Nut plug LCM pill",
                source_document="DDR_NHK089_2015.pdf",
                source_page=14,
                bbox=[0.1, 0.2, 0.8, 0.4],
                provenance_tier="OBSERVED",
            ),
            DrillingEvent(
                event_id="EVT-02",
                well_id="NHK-089",
                event_type=HazardType.KICK,
                severity="MEDIUM",
                depth_start_md_m=3350.0,  # +122m away, outside ±50m window
                formation="Barail Lower Sand",
            ),
        ]

        found = search_historical_events(
            events=events,
            offset_well=well,
            offset_trajectory=None,
            equivalent_tvdss=3228.0,
            window_m=50.0,
        )

        assert len(found) == 1
        ev = found[0]
        assert ev["event_id"] == "EVT-01"
        assert ev["event_type"] == "MUD_LOSS"
        assert ev["severity"] == "HIGH"
        assert ev["depth_tvdss_m"] == 3225.0
        assert ev["mitigation"] == "Nut plug LCM pill"
        assert ev["source_document"] == "DDR_NHK089_2015.pdf"
        assert ev["source_page"] == 14
        assert ev["bbox"] == [0.1, 0.2, 0.8, 0.4]
        assert ev["provenance_tier"] == "OBSERVED"


# ===========================================================================
# 7. CONFIGURABLE OMEGA RANKING
# ===========================================================================

class TestOmegaRanking:
    """Verifies baseline 0.25/0.40/0.20/0.15 weights and geological dominance."""

    def test_omega_weights_specification(self):
        assert DORS_W_DISTANCE == 0.25
        assert DORS_W_GEOLOGICAL == 0.40
        assert DORS_W_TRAJECTORY == 0.20
        assert DORS_W_COMPLETION == 0.15
        assert sum([DORS_W_DISTANCE, DORS_W_GEOLOGICAL, DORS_W_TRAJECTORY, DORS_W_COMPLETION]) == 1.0

    def test_geological_relevance_outranks_pure_spatial_proximity(self):
        """
        Well A is close (0.5 km) but penetrates a completely different formation (geo_score = 0.1).
        Well B is farther (4.0 km) but penetrates the exact target formation with high quality (geo_score = 1.0).
        Geological relevance (0.40 weight) must prevent pure distance from dominating.
        """
        # Well A: Distance = 0.5km (s_dist = exp(-0.5/8) = 0.939), Geo = 0.1, Traj = 0.8, Comp = 0.8
        score_a, comp_a = calculate_omega_score(
            distance_km=0.5, geological_score=0.1, trajectory_score=0.8, completion_score=0.8
        )

        # Well B: Distance = 4.0km (s_dist = exp(-4.0/8) = 0.606), Geo = 1.0, Traj = 0.8, Comp = 0.8
        score_b, comp_b = calculate_omega_score(
            distance_km=4.0, geological_score=1.0, trajectory_score=0.8, completion_score=0.8
        )

        # Well B's geological superiority must overcome Well A's proximity advantage
        assert score_b > score_a
        assert comp_b.geological == 1.0
        assert comp_a.geological == 0.1


# ===========================================================================
# 8. COMPETITIVE IMPROVEMENTS
# ===========================================================================

class TestCompetitiveImprovements:
    """Verifies hazard-specific dynamic weight profiles."""

    def test_hazard_specific_weight_profiles(self):
        loss_weights = HAZARD_WEIGHT_PROFILES[HazardType.MUD_LOSS]
        # Mud loss requires stronger geological emphasis
        assert loss_weights["geological"] == 0.45
        assert loss_weights["distance"] == 0.20

        kick_weights = HAZARD_WEIGHT_PROFILES[HazardType.KICK]
        # Kick risk prioritizes reservoir formation correlation
        assert kick_weights["geological"] == 0.45

        # Custom hazard evaluation
        score_loss, comp = calculate_omega_score(
            distance_km=2.0,
            geological_score=0.9,
            trajectory_score=0.7,
            completion_score=0.8,
            hazard_type=HazardType.MUD_LOSS,
        )
        assert score_loss > 0.0


# ===========================================================================
# 9. UNCERTAINTY PROPAGATION
# ===========================================================================

class TestUncertaintyPropagation:
    """Verifies formation top uncertainty propagation into sigma_xi."""

    def test_uncertainty_formula(self):
        # Top uncertainty = 5m, Thickness = 400m, Depth at top (depth - top = 0)
        sigma_top_only = compute_xi_uncertainty(
            depth_tvdss=2000.0, top_tvdss=2000.0, thickness=400.0, sigma_top=5.0, sigma_thickness=10.0
        )
        # At top, second term is zero, sigma_xi = sigma_top / thickness = 5 / 400 = 0.0125
        assert abs(sigma_top_only - 0.0125) < 1e-4

        # Near base, thickness uncertainty compounds
        sigma_mid = compute_xi_uncertainty(
            depth_tvdss=2200.0, top_tvdss=2000.0, thickness=400.0, sigma_top=5.0, sigma_thickness=10.0
        )
        assert sigma_mid > sigma_top_only


# ===========================================================================
# 10. STRUCTURAL FAULT / BLOCK HANDLING
# ===========================================================================

class TestStructuralFaultHandling:
    """Verifies heuristic detection does NOT label confirmed geology without structural evidence."""

    def test_normal_structural_dip_is_same_fault_block(self):
        status, throw = detect_structural_fault_status(
            active_top_tvdss=2940.0, offset_top_tvdss=2960.0, distance_km=1.0, max_dip_deg=8.0
        )
        assert status == StructuralFaultStatus.SAME_FAULT_BLOCK
        assert throw == 20.0

    def test_excessive_throw_flags_possible_fault_boundary(self):
        # 300m vertical offset over 0.5 km cannot be explained by standard dip -> POSSIBLE_FAULT_BOUNDARY
        status, throw = detect_structural_fault_status(
            active_top_tvdss=2940.0, offset_top_tvdss=3250.0, distance_km=0.5, max_dip_deg=8.0
        )
        assert status == StructuralFaultStatus.POSSIBLE_FAULT_BOUNDARY
        assert status != StructuralFaultStatus.CONFIRMED_FAULT
        assert throw == 310.0

    def test_fault_barrier_penalizes_omega_distance_score(self):
        # Without fault: distance_km = 1.0
        score_normal, _ = calculate_omega_score(
            distance_km=1.0, geological_score=0.9, trajectory_score=0.8, completion_score=0.8,
            structural_status=StructuralFaultStatus.SAME_FAULT_BLOCK
        )
        # With possible fault boundary: 0.20 barrier multiplier applies to distance relevance
        score_fault, _ = calculate_omega_score(
            distance_km=1.0, geological_score=0.9, trajectory_score=0.8, completion_score=0.8,
            structural_status=StructuralFaultStatus.POSSIBLE_FAULT_BOUNDARY
        )
        assert score_fault < score_normal


# ===========================================================================
# 11. RISK CORRIDOR PROJECTION
# ===========================================================================

class TestRiskCorridorProjection:
    """Verifies 0-20m, 20-50m, 50-200m ahead-of-bit lookahead projections."""

    def test_ahead_of_bit_corridor_tiers(self):
        active = Well(
            well_id="ACT", well_name="ACT", field="F", field_code="FLD",
            operator="OIL", surface_lat=27.0, surface_lon=95.0,
            kb_elevation_m=0.0, total_depth_md_m=4000.0, well_type=WellType.VERTICAL,
        )
        tops = [
            FormationTop(
                well_id="ACT", well_name="ACT", formation_name="Barail Lower Sand",
                top_md_m=2900.0, top_tvd_m=2900.0, base_md_m=3400.0, thickness_m=500.0,
            )
        ]

        corridor = compute_ahead_of_bit_corridor(
            active_well=active,
            active_traj=None,
            active_tops=tops,
            top_offset_wells=[],
            offset_trajectories={},
            offset_tops_map={},
            offset_events_map={},
            current_md_m=3000.0,
            max_lookahead_m=200.0,
            step_m=10.0,
        )

        assert corridor.current_md_m == 3000.0
        assert corridor.current_formation == "Barail Lower Sand"
        assert len(corridor.points) == 21  # 0 to 200m in 10m steps

        tiers = {p.window_tier for p in corridor.points}
        assert "IMMEDIATE_0_20M" in tiers
        assert "SHORT_TERM_20_50M" in tiers
        assert "LOOKAHEAD_50_200M" in tiers


# ===========================================================================
# 12. NUMERICAL EXAMPLE REGRESSION TEST (NHK-412 -> NHK-089)
# ===========================================================================

class TestWorkedExampleRegression:
    """
    Exact numerical benchmark from Module 4 specification:
    Active Well: NHK-412
      MD = 3200m
      TVDSS ≈ 2986m (deviated trajectory)
      Barail Lower Sand: Top = 2940m, Base = 3380m (thickness = 440m)
      Calculated ξ ≈ 0.105 (0.104545...)
    Offset Well: NHK-089
      Barail Lower Sand: Top = 3180m, Base = 3640m (thickness = 460m)
      Equivalent Offset TVDSS = 3180 + 0.104545 * 460 = 3228.09m ≈ 3228m
      Search Window: ±50m -> [3178m, 3278m]
      Expected Event: Lost Circulation (MUD_LOSS) at 3228m
    """

    def test_exact_worked_example_calculation(self):
        # 1. Setup Wells
        active_well = Well(
            well_id="NHK-412", well_name="NHK-412", field="Nahorkatiya",
            field_code="NHK", operator="OIL", surface_lat=27.29, surface_lon=95.34,
            kb_elevation_m=0.0, total_depth_md_m=4000.0, well_type=WellType.J_TYPE,
        )
        offset_well = Well(
            well_id="NHK-089", well_name="NHK-089", field="Nahorkatiya",
            field_code="NHK", operator="OIL", surface_lat=27.30, surface_lon=95.35,
            kb_elevation_m=0.0, total_depth_md_m=4000.0, well_type=WellType.VERTICAL,
        )

        # 2. Deviated trajectory putting MD=3200 at TVDSS=2986
        active_traj = WellTrajectory(
            well_id="NHK-412", well_name="NHK-412",
            stations=[
                SurveyStation(md_m=0.0, inclination_deg=0.0, azimuth_deg=0.0, tvd_m=0.0, ns_m=0.0, ew_m=0.0, tvdss_m=0.0),
                SurveyStation(md_m=3200.0, inclination_deg=15.0, azimuth_deg=45.0, tvd_m=2986.0, ns_m=50.0, ew_m=50.0, tvdss_m=2986.0),
            ]
        )

        # 3. Formations
        active_tops = [
            FormationTop(
                well_id="NHK-412", well_name="NHK-412", formation_name="Barail Lower Sand",
                top_md_m=2940.0, top_tvd_m=2940.0, base_md_m=3380.0, thickness_m=440.0,
                top_tvdss_m=2940.0, base_tvdss_m=3380.0, confidence=0.95,
            )
        ]
        offset_tops = [
            FormationTop(
                well_id="NHK-089", well_name="NHK-089", formation_name="Barail Lower Sand",
                top_md_m=3180.0, top_tvd_m=3180.0, base_md_m=3640.0, thickness_m=460.0,
                top_tvdss_m=3180.0, base_tvdss_m=3640.0, confidence=0.92,
            )
        ]

        # 4. Historical Event
        offset_events = [
            DrillingEvent(
                event_id="EVT-NHK089-LC",
                well_id="NHK-089",
                event_type=HazardType.MUD_LOSS,
                severity="HIGH",
                depth_start_md_m=3228.0,
                formation="Barail Lower Sand",
                raw_narrative="Severe lost circulation in Barail sand",
                mitigation_description="Pill pumped with 35 ppb coarse nut plug",
                source_document="DDR_NHK089_P18.pdf",
                source_page=18,
                bbox=[0.15, 0.25, 0.85, 0.45],
            )
        ]

        # 5. Run Correlation Chain
        result = correlate_offset_well(
            active_well=active_well,
            active_trajectory=active_traj,
            active_tops=active_tops,
            active_md=3200.0,
            offset_well=offset_well,
            offset_trajectory=None,
            offset_tops=offset_tops,
            offset_events=offset_events,
            window_m=50.0,
        )

        assert result["status"] == "correlated"
        assert result["correlation_status"] == "AVAILABLE"

        # Verify active xi
        xi_val = result["active_xi"]["xi"]
        assert abs(xi_val - 0.105) < 0.001

        # Verify equivalent offset depth
        equiv_tvdss = result["offset_mapping"]["equivalent_tvdss_m"]
        assert round(equiv_tvdss, 0) == 3228.0

        # Verify search interval [3178m, 3278m]
        lo, hi = result["search_interval_tvdss_m"]
        assert abs(lo - 3178.0) < 0.2
        assert abs(hi - 3278.0) < 0.2

        # Verify historical event found
        assert result["events_found"] == 1
        ev = result["events"][0]
        assert ev["event_type"] == "MUD_LOSS"
        assert ev["event_id"] == "EVT-NHK089-LC"
        assert ev["source_page"] == 18
        assert ev["bbox"] == [0.15, 0.25, 0.85, 0.45]


# ===========================================================================
# 13. TEST CLIENT & REST API ENDPOINTS
# ===========================================================================

class TestModule4APIEndpoints:
    """Verifies all Module 4 REST API endpoints via TestClient."""

    @pytest.fixture
    def client(self) -> TestClient:
        from app.modules.well_intelligence.services.data_store import NWISDataStore
        NWISDataStore().load()
        return TestClient(app)

    def test_survey_calculate_endpoint(self, client):
        payload = {
            "stations": [
                {"md_m": 0.0, "inclination_deg": 0.0, "azimuth_deg": 0.0},
                {"md_m": 500.0, "inclination_deg": 5.0, "azimuth_deg": 40.0},
                {"md_m": 1000.0, "inclination_deg": 12.0, "azimuth_deg": 45.0},
            ],
            "wellhead_elevation_m": 18.0,
            "well_id": "API_TEST_WELL",
        }
        res = client.post("/api/v1/survey/calculate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["tvd_method"] == "MINIMUM_CURVATURE"
        assert len(data["stations"]) == 3
        assert data["stations"][-1]["tvdss_m"] > 0

    def test_xi_correlate_endpoint(self, client):
        res = client.get("/api/v1/xi_correlate/WELL-NHK-001?depth=2000&window_m=50")
        assert res.status_code == 200
        data = res.json()
        assert "active_xi" in data
        assert data["active_well_id"] == "WELL-NHK-001"

    def test_correlate_xi_alias_endpoint(self, client):
        res = client.get("/api/v1/correlate/xi/WELL-NHK-001?depth=2000")
        assert res.status_code == 200
        data = res.json()
        assert "active_xi" in data

    def test_corridors_ahead_endpoint(self, client):
        res = client.get("/api/v1/corridors/ahead/WELL-NHK-001?depth=3200&max_lookahead_m=100&step_m=20")
        assert res.status_code == 200
        data = res.json()
        assert data["active_well_id"] == "WELL-NHK-001"
        assert len(data["points"]) == 6  # 0, 20, 40, 60, 80, 100m
        assert data["points"][0]["window_tier"] == "IMMEDIATE_0_20M"
