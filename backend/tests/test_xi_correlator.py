"""
Unit tests for the Module 4 xi (xi) stratigraphic correlation engine.

The primary fixture reproduces the worked example from
SIH26121_Module_4_Research_and_Implementation_Plan.md section 8.3 / 9
exactly:

    Active well NHK-412, MD = 3200m
    Formation: Barail Lower Sand, top=2940 base=3380 TVDSS (thickness 440m)
    Active TVDSS ~= 2986m  =>  xi ~= 0.105

    Offset well NHK-089
    Barail Lower Sand top=3180 base=3640 TVDSS (thickness 460m)
    equivalent_tvdss = 3180 + 0.105 * 460 ~= 3228m
    search window (+/-50m) => 3178-3278m TVDSS
    Expected historical event: LOST_CIRCULATION at 3228m TVDSS

This numeric result is produced entirely by the calculation pipeline in
xi_correlator.py -- it is not hardcoded in production code. Only this test
fixture encodes the MD's example numbers, as a regression check.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

from app.modules.well_intelligence.models.schemas import (
    DrillingEvent,
    FormationTop,
    HazardType,
    SurveyStation,
    Well,
    WellTrajectory,
    WellType,
)
from app.modules.well_intelligence.services.xi_correlator import (
    compute_correlation_confidence,
    compute_xi,
    compute_xi_for_well,
    correlate_across_offsets,
    correlate_offset_well,
    find_formation_by_tvdss,
    formation_base_tvdss,
    formation_top_tvdss,
    map_xi_to_offset,
    search_historical_events,
    xi_to_tvdss,
)
from app.modules.well_intelligence.services.stratigraphic_correlator import tvdss_at_md


# ---------------------------------------------------------------------------
# Fixtures reproducing the Module 4 worked example
# ---------------------------------------------------------------------------

KB_ELEVATION = 0.0  # keep TVD == TVDSS in the fixture so the worked example's
                     # published TVDSS numbers apply directly to TVD as well


def make_vertical_trajectory(well_id: str, well_name: str, max_md: float) -> WellTrajectory:
    """A purely vertical well: TVD == MD at every station."""
    stations = [
        SurveyStation(
            md_m=md, inclination_deg=0.0, azimuth_deg=0.0,
            tvd_m=md, ns_m=0.0, ew_m=0.0, tvdss_m=md - KB_ELEVATION,
        )
        for md in (0.0, max_md / 2, max_md)
    ]
    return WellTrajectory(
        well_id=well_id, well_name=well_name, method="VERTICAL_ASSUMPTION",
        well_type=WellType.VERTICAL, stations=stations,
    )


@pytest.fixture
def active_well() -> Well:
    return Well(
        well_id="NHK-412", well_name="NHK-412", field="Nahorkatiya",
        field_code="NHK", operator="OIL", surface_lat=27.29, surface_lon=95.34,
        kb_elevation_m=KB_ELEVATION, total_depth_md_m=4000.0,
        well_type=WellType.VERTICAL,
    )


@pytest.fixture
def active_trajectory_exact() -> WellTrajectory:
    """Two-point trajectory that puts MD=3200 exactly at TVDSS=2986 (deviated well)."""
    stations = [
        SurveyStation(md_m=0.0, inclination_deg=0.0, azimuth_deg=0.0, tvd_m=0.0, ns_m=0.0, ew_m=0.0, tvdss_m=0.0),
        SurveyStation(md_m=3200.0, inclination_deg=15.0, azimuth_deg=45.0, tvd_m=2986.0, ns_m=50.0, ew_m=50.0, tvdss_m=2986.0),
        SurveyStation(md_m=4000.0, inclination_deg=15.0, azimuth_deg=45.0, tvd_m=3700.0, ns_m=80.0, ew_m=80.0, tvdss_m=3700.0),
    ]
    return WellTrajectory(
        well_id="NHK-412", well_name="NHK-412", method="MINIMUM_CURVATURE",
        well_type=WellType.J_TYPE, stations=stations,
    )


@pytest.fixture
def active_tops() -> list[FormationTop]:
    return [
        FormationTop(
            well_id="NHK-412", well_name="NHK-412", formation_name="Barail Lower Sand",
            top_md_m=2940.0, top_tvd_m=2940.0, base_md_m=3380.0, thickness_m=440.0,
            confidence=0.95,
        ),
    ]


@pytest.fixture
def offset_well() -> Well:
    return Well(
        well_id="NHK-089", well_name="NHK-089", field="Nahorkatiya",
        field_code="NHK", operator="OIL", surface_lat=27.30, surface_lon=95.35,
        kb_elevation_m=KB_ELEVATION, total_depth_md_m=4000.0,
        well_type=WellType.VERTICAL,
    )


@pytest.fixture
def offset_trajectory() -> WellTrajectory:
    return make_vertical_trajectory("NHK-089", "NHK-089", max_md=4000.0)


@pytest.fixture
def offset_tops() -> list[FormationTop]:
    return [
        FormationTop(
            well_id="NHK-089", well_name="NHK-089", formation_name="Barail Lower Sand",
            top_md_m=3180.0, top_tvd_m=3180.0, base_md_m=3640.0, thickness_m=460.0,
            confidence=0.90,
        ),
    ]


@pytest.fixture
def offset_events() -> list[DrillingEvent]:
    return [
        DrillingEvent(
            event_id="EVT-NHK089-01", well_id="NHK-089", event_type=HazardType.MUD_LOSS,
            severity="HIGH", depth_start_md_m=3228.0, formation="Barail Lower Sand",
            raw_narrative="Total mud losses encountered", npt_hours=6.0,
            mitigation_description="Nut plug pill", confidence=0.9,
            source_document="DDR-2015-089", source_page=17,
        ),
        # A distractor event far outside the search window
        DrillingEvent(
            event_id="EVT-NHK089-02", well_id="NHK-089", event_type=HazardType.KICK,
            severity="LOW", depth_start_md_m=3900.0, formation="Barail Lower Sand",
            raw_narrative="Minor gas show", npt_hours=1.0, confidence=0.8,
        ),
    ]


# ---------------------------------------------------------------------------
# Core xi formula
# ---------------------------------------------------------------------------

class TestComputeXi:
    def test_worked_example_xi(self):
        xi = compute_xi(depth_tvdss=2986.0, formation_top_tvdss_m=2940.0, formation_base_tvdss_m=3380.0)
        assert round(xi, 3) == 0.105

    def test_xi_at_top_is_zero(self):
        assert compute_xi(2940.0, 2940.0, 3380.0) == 0.0

    def test_xi_at_base_is_one(self):
        assert compute_xi(3380.0, 2940.0, 3380.0) == 1.0

    def test_xi_midpoint_is_half(self):
        assert compute_xi(3160.0, 2940.0, 3380.0) == 0.5

    def test_xi_above_formation_is_negative(self):
        xi = compute_xi(2900.0, 2940.0, 3380.0)
        assert xi < 0

    def test_xi_below_formation_exceeds_one(self):
        xi = compute_xi(3400.0, 2940.0, 3380.0)
        assert xi > 1

    def test_zero_thickness_raises(self):
        with pytest.raises(ValueError):
            compute_xi(3000.0, 3000.0, 3000.0)

    def test_inverted_bounds_raises(self):
        with pytest.raises(ValueError):
            compute_xi(3000.0, 3380.0, 2940.0)


# ---------------------------------------------------------------------------
# xi -> offset equivalent depth
# ---------------------------------------------------------------------------

class TestXiToTvdss:
    def test_worked_example_equivalent_depth(self):
        equiv = xi_to_tvdss(xi=0.105, offset_top_tvdss=3180.0, offset_thickness_m=460.0)
        assert round(equiv, 0) == 3228.0

    def test_equivalent_depth_at_xi_zero_equals_offset_top(self):
        assert xi_to_tvdss(0.0, 3180.0, 460.0) == 3180.0

    def test_equivalent_depth_at_xi_one_equals_offset_base(self):
        assert xi_to_tvdss(1.0, 3180.0, 460.0) == 3640.0

    def test_map_xi_to_offset_missing_formation_returns_none(self, offset_well):
        result = map_xi_to_offset(
            xi_active=0.105, formation_name="Kopili Formation",
            offset_well=offset_well, offset_tops=[],
        )
        assert result is None


# ---------------------------------------------------------------------------
# Formation identification by TVDSS
# ---------------------------------------------------------------------------

class TestFormationLookup:
    def test_finds_formation_containing_depth(self, active_tops, active_well):
        fm = find_formation_by_tvdss(active_tops, active_well, 2986.0)
        assert fm is not None
        assert fm.formation_name == "Barail Lower Sand"

    def test_depth_above_all_formations_returns_none(self, active_tops, active_well):
        assert find_formation_by_tvdss(active_tops, active_well, 100.0) is None

    def test_depth_below_all_formations_returns_none(self, active_tops, active_well):
        assert find_formation_by_tvdss(active_tops, active_well, 5000.0) is None

    def test_base_is_exclusive_top_is_inclusive(self, active_tops, active_well):
        # top boundary belongs to the formation
        assert find_formation_by_tvdss(active_tops, active_well, 2940.0) is not None
        # exact base boundary belongs to the *next* formation, not this one
        assert find_formation_by_tvdss(active_tops, active_well, 3380.0) is None

    def test_formation_base_tvdss_helper(self, active_tops, active_well):
        top = active_tops[0]
        assert formation_base_tvdss(top, active_well) == 3380.0
        assert formation_top_tvdss(top, active_well) == 2940.0


# ---------------------------------------------------------------------------
# Full pipeline: vertical well
# ---------------------------------------------------------------------------

class TestVerticalWellPipeline:
    def test_compute_xi_for_well_vertical(self, active_well, active_tops):
        traj = make_vertical_trajectory("NHK-412", "NHK-412", max_md=4000.0)
        result = compute_xi_for_well(active_well, traj, active_tops, md=3200.0)
        assert result is not None
        # Vertical well: TVDSS == MD (KB elevation = 0), so formation lookup
        # uses TVDSS=3200 directly -> xi = (3200-2940)/440
        assert round(result.xi, 3) == round((3200.0 - 2940.0) / 440.0, 3)
        assert result.in_bounds is True

    def test_md_outside_any_formation_returns_none(self, active_well, active_tops):
        traj = make_vertical_trajectory("NHK-412", "NHK-412", max_md=4000.0)
        result = compute_xi_for_well(active_well, traj, active_tops, md=100.0)
        assert result is None


# ---------------------------------------------------------------------------
# Full pipeline: deviated well (worked example, exact numbers)
# ---------------------------------------------------------------------------

class TestDeviatedWellWorkedExample:
    def test_active_tvdss_matches_worked_example(self, active_well, active_trajectory_exact):
        tvdss = tvdss_at_md(active_trajectory_exact, active_well, 3200.0)
        assert round(tvdss, 0) == 2986.0

    def test_xi_matches_worked_example(self, active_well, active_trajectory_exact, active_tops):
        result = compute_xi_for_well(active_well, active_trajectory_exact, active_tops, md=3200.0)
        assert result is not None
        assert result.formation_name == "Barail Lower Sand"
        assert round(result.xi, 3) == 0.105

    def test_full_correlation_matches_worked_example(
        self, active_well, active_trajectory_exact, active_tops,
        offset_well, offset_trajectory, offset_tops, offset_events,
    ):
        result = correlate_offset_well(
            active_well=active_well,
            active_trajectory=active_trajectory_exact,
            active_tops=active_tops,
            active_md=3200.0,
            offset_well=offset_well,
            offset_trajectory=offset_trajectory,
            offset_tops=offset_tops,
            offset_events=offset_events,
        )
        assert result["status"] == "correlated"
        # MD worked example states xi ~= 0.105 (2986-2940)/440 = 0.104545...;
        # assert to the documented 3-decimal precision with tolerance rather
        # than exact round() to sidestep float rounding-mode edge cases.
        assert abs(result["active_xi"]["xi"] - 0.105) < 0.001
        assert round(result["offset_mapping"]["equivalent_tvdss_m"], 0) == 3228.0
        lo, hi = result["search_interval_tvdss_m"]
        assert abs(lo - 3178.0) < 0.2
        assert abs(hi - 3278.0) < 0.2
        assert result["events_found"] == 1
        assert result["events"][0]["event_type"] == "MUD_LOSS"
        assert result["events"][0]["event_id"] == "EVT-NHK089-01"


# ---------------------------------------------------------------------------
# Missing survey / vertical fallback
# ---------------------------------------------------------------------------

class TestMissingSurveyFallback:
    def test_empty_trajectory_falls_back_to_md_as_tvd(self, active_well, active_tops):
        empty_traj = WellTrajectory(well_id="NHK-412", well_name="NHK-412", stations=[])
        result = compute_xi_for_well(active_well, empty_traj, active_tops, md=3200.0)
        # tvd_at_md() falls back to `return target_md` when there are no stations
        assert result is not None
        assert round(result.xi, 3) == round((3200.0 - 2940.0) / 440.0, 3)

    def test_search_historical_events_without_offset_trajectory_uses_md(
        self, offset_well, offset_events,
    ):
        events = search_historical_events(
            events=offset_events, offset_well=offset_well, offset_trajectory=None,
            equivalent_tvdss=3228.0, window_m=50.0,
        )
        assert len(events) == 1
        assert events[0]["depth_method"] == "VERTICAL_ASSUMPTION"


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

class TestInterpolation:
    def test_tvdss_interpolates_between_stations(self, active_well, active_trajectory_exact):
        # Halfway between MD=0 (TVD=0) and MD=3200 (TVD=2986). Interpolation
        # follows the minimum-curvature shape (inclination builds 0 -> 15 deg),
        # so the midpoint sits slightly above the linear midpoint, while the
        # recorded station TVDs are still honoured exactly.
        mid = tvdss_at_md(active_trajectory_exact, active_well, 1600.0)
        assert 2986.0 / 2 <= mid < 2986.0 / 2 + 0.01 * 2986.0
        assert round(tvdss_at_md(active_trajectory_exact, active_well, 3200.0), 1) == 2986.0


# ---------------------------------------------------------------------------
# Formation boundaries
# ---------------------------------------------------------------------------

class TestFormationBoundaries:
    def test_xi_zero_at_exact_top(self, active_well, active_tops):
        traj = make_vertical_trajectory("NHK-412", "NHK-412", max_md=4000.0)
        result = compute_xi_for_well(active_well, traj, active_tops, md=2940.0)
        assert result is not None
        assert result.xi == 0.0

    def test_xi_near_one_just_inside_base(self, active_well, active_tops):
        traj = make_vertical_trajectory("NHK-412", "NHK-412", max_md=4000.0)
        result = compute_xi_for_well(active_well, traj, active_tops, md=3379.999)
        assert result is not None
        assert result.xi < 1.0
        assert result.in_bounds is True


# ---------------------------------------------------------------------------
# xi out of [0, 1] bounds (explicit XiResult.in_bounds checks)
# ---------------------------------------------------------------------------

class TestXiBounds:
    def test_in_bounds_true_within_formation(self, active_well, active_tops):
        traj = make_vertical_trajectory("NHK-412", "NHK-412", max_md=4000.0)
        result = compute_xi_for_well(active_well, traj, active_tops, md=3200.0)
        assert result.in_bounds is True

    def test_xi_less_than_zero_flagged_out_of_bounds(self):
        xi = compute_xi(2900.0, 2940.0, 3380.0)
        assert xi < 0
        # Directly constructing XiResult to check the flag without needing
        # a formation lookup to select an out-of-range depth (the normal
        # pipeline never selects a formation for an out-of-range depth).
        from app.modules.well_intelligence.services.xi_correlator import XiResult
        result = XiResult("Barail Lower Sand", 2900.0, 2940.0, 3380.0, 440.0, xi, 0.9)
        assert result.in_bounds is False

    def test_xi_greater_than_one_flagged_out_of_bounds(self):
        from app.modules.well_intelligence.services.xi_correlator import XiResult
        xi = compute_xi(3400.0, 2940.0, 3380.0)
        result = XiResult("Barail Lower Sand", 3400.0, 2940.0, 3380.0, 440.0, xi, 0.9)
        assert result.in_bounds is False


# ---------------------------------------------------------------------------
# Missing formation in offset well
# ---------------------------------------------------------------------------

class TestMissingFormationInOffset:
    def test_offset_without_formation_returns_unavailable_status(
        self, active_well, active_trajectory_exact, active_tops, offset_well, offset_trajectory,
    ):
        result = correlate_offset_well(
            active_well=active_well,
            active_trajectory=active_trajectory_exact,
            active_tops=active_tops,
            active_md=3200.0,
            offset_well=offset_well,
            offset_trajectory=offset_trajectory,
            offset_tops=[],  # offset never penetrated any formation
            offset_events=[],
        )
        assert result["status"] == "formation_unavailable_in_offset"
        # Must not fabricate a depth
        assert "offset_mapping" not in result

    def test_active_depth_outside_any_formation_returns_no_active_formation(
        self, active_well, active_trajectory_exact, offset_well, offset_trajectory, offset_tops,
    ):
        result = correlate_offset_well(
            active_well=active_well,
            active_trajectory=active_trajectory_exact,
            active_tops=[],  # active well has no formation data at all
            active_md=3200.0,
            offset_well=offset_well,
            offset_trajectory=offset_trajectory,
            offset_tops=offset_tops,
            offset_events=[],
        )
        assert result["status"] == "no_active_formation"


# ---------------------------------------------------------------------------
# Historical event search
# ---------------------------------------------------------------------------

class TestHistoricalEventSearch:
    def test_event_inside_window_is_found(self, offset_well, offset_trajectory, offset_events):
        events = search_historical_events(
            offset_events, offset_well, offset_trajectory, equivalent_tvdss=3228.0, window_m=50.0,
        )
        assert len(events) == 1
        assert events[0]["event_id"] == "EVT-NHK089-01"

    def test_event_outside_window_is_excluded(self, offset_well, offset_trajectory, offset_events):
        events = search_historical_events(
            offset_events, offset_well, offset_trajectory, equivalent_tvdss=3228.0, window_m=50.0,
        )
        found_ids = {e["event_id"] for e in events}
        assert "EVT-NHK089-02" not in found_ids

    def test_widening_window_includes_more_events(self, offset_well, offset_trajectory, offset_events):
        events = search_historical_events(
            offset_events, offset_well, offset_trajectory, equivalent_tvdss=3228.0, window_m=700.0,
        )
        assert len(events) == 2

    def test_no_events_in_window_returns_empty_list(self, offset_well, offset_trajectory):
        events = search_historical_events(
            [], offset_well, offset_trajectory, equivalent_tvdss=3228.0, window_m=50.0,
        )
        assert events == []

    def test_events_sorted_by_distance_to_equivalent_depth(self, offset_well, offset_trajectory):
        events_in = [
            DrillingEvent(
                event_id="FAR", well_id="NHK-089", event_type=HazardType.MUD_LOSS,
                depth_start_md_m=3260.0, confidence=0.9,
            ),
            DrillingEvent(
                event_id="NEAR", well_id="NHK-089", event_type=HazardType.MUD_LOSS,
                depth_start_md_m=3230.0, confidence=0.9,
            ),
        ]
        events = search_historical_events(
            events_in, offset_well, offset_trajectory, equivalent_tvdss=3228.0, window_m=50.0,
        )
        assert [e["event_id"] for e in events] == ["NEAR", "FAR"]

    def test_events_from_other_wells_are_excluded(self, offset_well, offset_trajectory):
        events_in = [
            DrillingEvent(
                event_id="OTHER-WELL", well_id="SOME-OTHER-WELL", event_type=HazardType.MUD_LOSS,
                depth_start_md_m=3228.0, confidence=0.9,
            ),
        ]
        events = search_historical_events(
            events_in, offset_well, offset_trajectory, equivalent_tvdss=3228.0, window_m=50.0,
        )
        assert events == []


# ---------------------------------------------------------------------------
# Malformed survey data
# ---------------------------------------------------------------------------

class TestMalformedSurveyData:
    def test_single_station_trajectory_does_not_crash(self, active_well, active_tops):
        traj = WellTrajectory(
            well_id="NHK-412", well_name="NHK-412",
            stations=[SurveyStation(md_m=0.0, inclination_deg=0.0, azimuth_deg=0.0, tvd_m=0.0, ns_m=0.0, ew_m=0.0, tvdss_m=0.0)],
        )
        # Should not raise; falls back to extrapolation/last-station logic
        result = compute_xi_for_well(active_well, traj, active_tops, md=3200.0)
        # With only one station at MD=0, tvd_at_md extrapolates using frac=md/first_md
        # which divides by ~0 -> huge TVD, landing outside any known formation.
        assert result is None or result.formation_name == "Barail Lower Sand"

    def test_out_of_order_stations_do_not_crash(self, active_well, active_tops):
        # Stations deliberately out of MD order
        traj = WellTrajectory(
            well_id="NHK-412", well_name="NHK-412",
            stations=[
                SurveyStation(md_m=3200.0, inclination_deg=15.0, azimuth_deg=45.0, tvd_m=2986.0, ns_m=0, ew_m=0, tvdss_m=2986.0),
                SurveyStation(md_m=0.0, inclination_deg=0.0, azimuth_deg=0.0, tvd_m=0.0, ns_m=0, ew_m=0, tvdss_m=0.0),
            ],
        )
        # Must not raise even though iteration logic assumes ascending MD
        try:
            compute_xi_for_well(active_well, traj, active_tops, md=1600.0)
        except (ZeroDivisionError, IndexError):
            pytest.fail("compute_xi_for_well raised on out-of-order survey stations")

    def test_zero_thickness_formation_is_never_selected(self, active_well):
        """
        A zero-thickness top/base window (top == base) can never contain a
        depth under the `top <= depth < base` matching rule, so
        find_formation_by_tvdss safely returns no match -- the malformed
        record is silently excluded rather than causing a crash or a
        fabricated xi. compute_xi() itself still raises ValueError if ever
        called directly with equal top/base bounds (see TestComputeXi).
        """
        traj = make_vertical_trajectory("NHK-412", "NHK-412", max_md=4000.0)
        bad_tops = [
            FormationTop(
                well_id="NHK-412", well_name="NHK-412", formation_name="Degenerate Formation",
                top_md_m=3000.0, top_tvd_m=3000.0, base_md_m=3000.0, thickness_m=0.0,
            ),
        ]
        result = compute_xi_for_well(active_well, traj, bad_tops, md=3000.0)
        assert result is None


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

class TestCorrelationConfidence:
    def test_confidence_penalized_when_out_of_bounds(self, active_well, active_tops):
        from app.modules.well_intelligence.services.xi_correlator import XiResult
        in_bounds = XiResult("Barail Lower Sand", 3200.0, 2940.0, 3380.0, 440.0, 0.5, 0.9)
        out_of_bounds = XiResult("Barail Lower Sand", 3500.0, 2940.0, 3380.0, 440.0, 1.5, 0.9)

        conf_in = compute_correlation_confidence(in_bounds, offset_formation_confidence=0.9, events_found=3)
        conf_out = compute_correlation_confidence(out_of_bounds, offset_formation_confidence=0.9, events_found=3)
        assert conf_out < conf_in

    def test_confidence_increases_with_more_evidence(self):
        from app.modules.well_intelligence.services.xi_correlator import XiResult
        result = XiResult("Barail Lower Sand", 3200.0, 2940.0, 3380.0, 440.0, 0.5, 0.9)
        conf_low = compute_correlation_confidence(result, 0.9, events_found=0)
        conf_high = compute_correlation_confidence(result, 0.9, events_found=5)
        assert conf_high > conf_low


# ---------------------------------------------------------------------------
# Multi-offset correlation
# ---------------------------------------------------------------------------

class TestCorrelateAcrossOffsets:
    def test_returns_one_result_per_offset_well(
        self, active_well, active_trajectory_exact, active_tops,
        offset_well, offset_trajectory, offset_tops, offset_events,
    ):
        second_offset = Well(
            well_id="NHK-145", well_name="NHK-145", field="Nahorkatiya",
            field_code="NHK", operator="OIL", surface_lat=27.31, surface_lon=95.36,
            kb_elevation_m=0.0, total_depth_md_m=4000.0, well_type=WellType.VERTICAL,
        )
        second_traj = make_vertical_trajectory("NHK-145", "NHK-145", max_md=4000.0)

        result = correlate_across_offsets(
            active_well=active_well,
            active_trajectory=active_trajectory_exact,
            active_tops=active_tops,
            active_md=3200.0,
            offset_wells=[active_well, offset_well, second_offset],
            offset_trajectories={
                "NHK-412": active_trajectory_exact,
                "NHK-089": offset_trajectory,
                "NHK-145": second_traj,
            },
            offset_tops_map={"NHK-089": offset_tops, "NHK-145": []},
            offset_events_map={"NHK-089": offset_events, "NHK-145": []},
        )
        assert result["status"] == "correlated"
        offset_ids = {o["offset_well_id"] for o in result["offsets"]}
        # Active well excluded from its own offset list
        assert "NHK-412" not in offset_ids
        assert offset_ids == {"NHK-089", "NHK-145"}

        nhk089_result = next(o for o in result["offsets"] if o["offset_well_id"] == "NHK-089")
        assert nhk089_result["status"] == "correlated"
        nhk145_result = next(o for o in result["offsets"] if o["offset_well_id"] == "NHK-145")
        assert nhk145_result["status"] == "formation_unavailable_in_offset"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
