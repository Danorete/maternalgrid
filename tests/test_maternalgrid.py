"""Model tests for MaternalGrid: the access maths and the scenario engine."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.access import (  # noqa: E402
    compute_access,
    facility_volumes,
    haversine_matrix,
    miles_to_minutes,
    statewide_summary,
)
from src.config import ACCESS_THRESHOLD_MIN, AVG_SPEED_MPH, ROAD_FACTOR  # noqa: E402
from src.data_loader import (  # noqa: E402
    active_facilities,
    load_counties,
    load_facilities,
    load_geojson,
)
from src.presets import county_add_point, find_lavonia_facility, largest_gap_county  # noqa: E402
from src.simulate import apply_scenario, removable_facility_names, run_scenario  # noqa: E402


@pytest.fixture(scope="module")
def data():
    counties = load_counties()
    facilities = load_facilities()
    geojson = load_geojson()
    access = compute_access(counties, active_facilities(facilities))
    return counties, facilities, geojson, access


# ------------------------------------------------------------------ travel model

def test_haversine_zero_distance_to_self():
    d = haversine_matrix([33.0], [-84.0], [33.0], [-84.0])
    assert d.shape == (1, 1)
    assert d[0, 0] == pytest.approx(0.0, abs=1e-6)


def test_haversine_one_degree_of_latitude_is_about_69_miles():
    d = haversine_matrix([33.0], [-84.0], [34.0], [-84.0])
    assert d[0, 0] == pytest.approx(69.0, abs=0.5)


def test_minutes_apply_road_factor_and_speed():
    # 45 miles straight line at a 1.3 road factor and 45 mph is 78 minutes.
    assert miles_to_minutes([45.0])[0] == pytest.approx(
        45.0 * ROAD_FACTOR / AVG_SPEED_MPH * 60.0
    )
    assert miles_to_minutes([45.0])[0] == pytest.approx(78.0)


# ------------------------------------------------------------------ county table

def test_all_159_georgia_counties_load(data):
    counties, _f, _gj, _a = data
    assert len(counties) == 159
    assert counties["GEOID"].str.len().eq(5).all()
    assert counties["GEOID"].str.startswith("13").all()
    assert counties["GEOID"].is_unique


def test_access_columns_are_consistent(data):
    _c, _f, _gj, access = data
    assert access["minutes"].notna().all()
    assert (access["has_access"] == (access["minutes"] <= ACCESS_THRESHOLD_MIN)).all()
    # A county hosting a facility sits essentially on top of it.
    assert access["minutes"].min() < 5


def test_births_per_ob_provider_is_missing_not_infinite(data):
    _c, _f, _gj, access = data
    no_provider = access[access["ob_providers"] == 0]
    assert len(no_provider) > 0
    assert no_provider["births_per_ob_provider"].isna().all()


def test_facility_volumes_conserve_total_births(data):
    _c, facilities, _gj, access = data
    volumes = facility_volumes(access, active_facilities(facilities))
    assert volumes["modeled_births"].sum() == access["births"].sum()


def test_inactive_facilities_never_serve_a_county(data):
    _c, facilities, _gj, access = data
    inactive = set(facilities.loc[~facilities["is_active"], "name"])
    assert inactive, "fixture should contain at least one inactive facility"
    assert not inactive & set(access["nearest_facility"])


def test_statewide_summary_shape(data):
    _c, facilities, geojson, access = data
    s = statewide_summary(access, facilities, geojson)
    assert s["total_counties"] == 159
    assert 0 <= s["pct_counties_no_facility"] <= 100
    assert 0 <= s["pct_counties_no_ob_provider"] <= 100
    assert s["women_beyond_threshold"] >= 0
    assert s["births_weighted_avg_minutes"] > 0


# ------------------------------------------------------------------ scenarios

def test_only_in_state_active_facilities_are_removable(data):
    _c, facilities, _gj, _a = data
    removable = set(removable_facility_names(facilities))
    border = set(facilities.loc[~facilities["in_state"], "name"])
    inactive = set(facilities.loc[~facilities["is_active"], "name"])
    assert removable and not removable & border and not removable & inactive


def test_removing_a_border_facility_is_ignored(data):
    _c, facilities, _gj, _a = data
    border_name = facilities.loc[~facilities["in_state"], "name"].iloc[0]
    after = apply_scenario(facilities, remove_names=[border_name])
    assert border_name in set(after["name"])
    assert len(after) == len(facilities)


def test_closure_never_improves_access(data):
    counties, facilities, _gj, _a = data
    target = removable_facility_names(facilities)[0]
    result = run_scenario(facilities, remove_names=[target], counties=counties)
    summary = result["summary"]
    assert summary["counties_gaining_access"] == 0
    assert summary["avg_minutes_change"] >= 0
    assert summary["active_facilities_after"] == summary["active_facilities_before"] - 1
    # Nobody's modeled travel time can fall when a facility disappears.
    assert (result["changed"]["minutes_change"] >= 0).all()


def test_addition_never_worsens_access(data):
    counties, facilities, _gj, access = data
    gap = largest_gap_county(access)
    result = run_scenario(
        facilities, add_points=[county_add_point(gap, "III")], counties=counties
    )
    summary = result["summary"]
    assert summary["counties_losing_access"] == 0
    assert summary["avg_minutes_change"] <= 0
    assert (result["changed"]["minutes_change"] <= 0).all()
    # The county that received the facility now sits on top of it.
    after = result["after"]
    assert after.loc[after["GEOID"] == gap["GEOID"], "minutes"].iloc[0] == pytest.approx(0.0)


def test_empty_scenario_changes_nothing(data):
    counties, facilities, _gj, _a = data
    result = run_scenario(facilities, counties=counties)
    assert result["changed"].empty
    assert result["summary"]["avg_minutes_change"] == 0.0


def test_displaced_births_are_fully_absorbed(data):
    counties, facilities, _gj, _a = data
    lavonia = find_lavonia_facility(facilities)
    assert lavonia is not None
    result = run_scenario(facilities, remove_names=[lavonia], counties=counties)

    before_volume = dict(
        zip(result["before_volumes"]["name"], result["before_volumes"]["modeled_births"])
    )[lavonia]
    absorbed = sum(a["births_absorbed"] for a in result["summary"]["absorbing_facilities"])
    assert absorbed == before_volume
    assert lavonia not in set(result["after"]["nearest_facility"])


def test_scenario_before_table_matches_the_baseline(data):
    counties, facilities, _gj, access = data
    result = run_scenario(
        facilities, remove_names=removable_facility_names(facilities)[:1], counties=counties
    )
    pd.testing.assert_series_equal(
        result["before"]["minutes"], access["minutes"], check_names=False
    )
