"""The modeled access layer: distances, travel minutes and statewide rollups.

Every minute value produced here is modeled. It is straight line distance from
a county centroid to the nearest active facility, multiplied by ROAD_FACTOR and
converted at AVG_SPEED_MPH. It is not a real drive time.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.config import (
    ACCESS_THRESHOLD_MIN,
    AVG_SPEED_MPH,
    EARTH_RADIUS_MI,
    HIGH_LEVEL_FACILITY_LEVELS,
    ROAD_FACTOR,
)


def haversine_matrix(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Great circle miles between every county (rows) and facility (columns)."""
    lat1 = np.radians(np.asarray(lat1, dtype=float))[:, None]
    lon1 = np.radians(np.asarray(lon1, dtype=float))[:, None]
    lat2 = np.radians(np.asarray(lat2, dtype=float))[None, :]
    lon2 = np.radians(np.asarray(lon2, dtype=float))[None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_MI * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def miles_to_minutes(miles) -> np.ndarray:
    """Road adjusted minutes at the assumed average speed."""
    return np.asarray(miles, dtype=float) * ROAD_FACTOR / AVG_SPEED_MPH * 60.0


def compute_access(counties: pd.DataFrame, facilities: pd.DataFrame) -> pd.DataFrame:
    """Attach modeled travel columns to a county table.

    `facilities` must already be filtered to active facilities. Returns a copy
    with nearest_facility, modeled minutes, access flag, and the same pair of
    values for the nearest Level III or IV facility.
    """
    out = counties.copy()
    n = len(out)

    if facilities.empty:
        out["nearest_facility"] = "none"
        out["nearest_miles"] = np.nan
        out["minutes"] = np.nan
        out["has_access"] = False
        out["nearest_high_facility"] = "none"
        out["high_level_minutes"] = np.nan
        out["has_high_level_access"] = False
        return out

    miles = haversine_matrix(
        out["lat"].to_numpy(), out["lon"].to_numpy(),
        facilities["lat"].to_numpy(), facilities["lon"].to_numpy(),
    )
    nearest_idx = miles.argmin(axis=1)
    nearest_miles = miles[np.arange(n), nearest_idx]

    out["nearest_facility"] = facilities["name"].to_numpy()[nearest_idx]
    out["nearest_miles"] = np.round(nearest_miles, 2)
    out["minutes"] = np.round(miles_to_minutes(nearest_miles), 1)
    out["has_access"] = out["minutes"] <= ACCESS_THRESHOLD_MIN

    high = facilities["maternal_level"].isin(HIGH_LEVEL_FACILITY_LEVELS).to_numpy()
    if high.any():
        high_miles_all = miles[:, high]
        high_names = facilities.loc[high, "name"].to_numpy()
        h_idx = high_miles_all.argmin(axis=1)
        h_miles = high_miles_all[np.arange(n), h_idx]
        out["nearest_high_facility"] = high_names[h_idx]
        out["high_level_minutes"] = np.round(miles_to_minutes(h_miles), 1)
    else:
        out["nearest_high_facility"] = "none"
        out["high_level_minutes"] = np.nan
    out["has_high_level_access"] = out["high_level_minutes"] <= ACCESS_THRESHOLD_MIN

    return out


@st.cache_data(show_spinner=False)
def compute_access_cached(counties: pd.DataFrame, facilities: pd.DataFrame) -> pd.DataFrame:
    """Cached wrapper for the baseline run, which is recomputed on every rerun."""
    return compute_access(counties, facilities)


def facility_volumes(access: pd.DataFrame, facilities: pd.DataFrame) -> pd.DataFrame:
    """Modeled birth volume per facility: births of every county nearest to it."""
    grouped = (
        access.groupby("nearest_facility")
        .agg(
            modeled_births=("births", "sum"),
            modeled_women_15_44=("women_15_44", "sum"),
            counties_served=("GEOID", "count"),
        )
        .reset_index()
        .rename(columns={"nearest_facility": "name"})
    )
    out = facilities[["name", "city", "state", "maternal_level", "in_state"]].merge(
        grouped, on="name", how="left"
    )
    for col in ("modeled_births", "modeled_women_15_44", "counties_served"):
        out[col] = out[col].fillna(0).astype(int)
    return out.sort_values("modeled_births", ascending=False).reset_index(drop=True)


def _point_in_ring(lon: float, lat: float, ring) -> bool:
    """Ray casting test for one linear ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def _point_in_geometry(lon: float, lat: float, geometry) -> bool:
    polys = (
        [geometry["coordinates"]]
        if geometry["type"] == "Polygon"
        else geometry["coordinates"]
    )
    for poly in polys:
        if not poly:
            continue
        if _point_in_ring(lon, lat, poly[0]) and not any(
            _point_in_ring(lon, lat, hole) for hole in poly[1:]
        ):
            return True
    return False


@st.cache_data(show_spinner=False)
def facility_county_geoids(facilities: pd.DataFrame, geojson: dict) -> dict:
    """Map each facility name to the GEOID of the county it sits in, or None.

    Out of state border facilities fall outside every Georgia polygon and map
    to None, which is what we want: they never make a Georgia county count as
    having a facility of its own.
    """
    features = geojson["features"]
    result = {}
    for name, lat, lon in zip(facilities["name"], facilities["lat"], facilities["lon"]):
        geoid = None
        for feat in features:
            if _point_in_geometry(lon, lat, feat["geometry"]):
                geoid = feat["properties"]["GEOID"]
                break
        result[name] = geoid
    return result


def statewide_summary(access: pd.DataFrame, facilities: pd.DataFrame, geojson: dict) -> dict:
    """The four headline numbers shown at the top of the app."""
    total_counties = len(access)
    active = facilities[facilities["is_active"]]
    in_county = set(
        geoid for geoid in facility_county_geoids(active, geojson).values() if geoid
    )
    counties_with_facility = len(in_county & set(access["GEOID"]))

    beyond = access[~access["has_access"]]
    total_births = access["births"].sum()
    weighted_minutes = (
        float((access["births"] * access["minutes"]).sum() / total_births)
        if total_births > 0
        else float("nan")
    )

    return {
        "total_counties": total_counties,
        "counties_no_facility": total_counties - counties_with_facility,
        "pct_counties_no_facility": 100.0 * (total_counties - counties_with_facility) / total_counties,
        "counties_no_ob_provider": int((access["ob_providers"] == 0).sum()),
        "pct_counties_no_ob_provider": 100.0 * float((access["ob_providers"] == 0).mean()),
        "women_beyond_threshold": int(beyond["women_15_44"].sum()),
        "births_beyond_threshold": int(beyond["births"].sum()),
        "counties_beyond_threshold": int(len(beyond)),
        "births_weighted_avg_minutes": weighted_minutes,
        "active_facility_count": int(len(active)),
        "active_in_state_count": int(active["in_state"].sum()),
    }
