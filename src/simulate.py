"""Scenario engine: remove Georgia facilities, add new ones, compare access.

Only in_state facilities can be removed. Out of state border facilities are
fixed: a Georgia planner cannot close a hospital in Florida or Tennessee, so
they stay in every scenario.
"""

from __future__ import annotations

import pandas as pd

from src.access import compute_access, facility_volumes
from src.config import ACCESS_THRESHOLD_MIN, ACTIVE_STATUS


def removable_facility_names(facilities: pd.DataFrame) -> list[str]:
    """Active Georgia facilities, the only ones a scenario may close."""
    mask = facilities["is_active"] & facilities["in_state"]
    return sorted(facilities.loc[mask, "name"].tolist())


def apply_scenario(facilities: pd.DataFrame, remove_names=None, add_points=None) -> pd.DataFrame:
    """Return the scenario facility table: removals applied, additions appended.

    A name in `remove_names` that is not an active in state facility is ignored,
    so a stale preset can never silently close a border hospital.
    """
    remove_names = set(remove_names or [])
    add_points = list(add_points or [])

    allowed = set(removable_facility_names(facilities))
    to_remove = remove_names & allowed

    kept = facilities[~facilities["name"].isin(to_remove)].copy()

    rows = []
    for point in add_points:
        rows.append(
            {
                "name": point["name"],
                "address": point.get("address", ""),
                "city": point.get("city", ""),
                "state": point.get("state", "GA"),
                "in_state": bool(point.get("in_state", True)),
                "maternal_level": str(point.get("maternal_level", "II")).upper(),
                "status": ACTIVE_STATUS,
                "lat": float(point["lat"]),
                "lon": float(point["lon"]),
                "source": point.get("source", "Scenario: added by planner"),
                "is_active": True,
            }
        )
    if rows:
        kept = pd.concat([kept, pd.DataFrame(rows)], ignore_index=True)
    return kept.reset_index(drop=True)


def run_scenario(facilities: pd.DataFrame, remove_names=None, add_points=None,
                 counties: pd.DataFrame | None = None) -> dict:
    """Compare baseline access with scenario access.

    Returns a dict with:
      before, after            county tables with modeled access columns
      changed                  only the counties whose access flag or minutes moved
      scenario_facilities      the facility table the after run used
      before_volumes, after_volumes   modeled births per facility
      summary                  the headline scenario numbers
    """
    if counties is None:
        raise ValueError("run_scenario needs the county table")

    baseline_active = facilities[facilities["is_active"]].reset_index(drop=True)
    scenario_facilities = apply_scenario(facilities, remove_names, add_points)
    scenario_active = scenario_facilities[scenario_facilities["is_active"]].reset_index(drop=True)

    before = compute_access(counties, baseline_active)
    after = compute_access(counties, scenario_active)

    merged = before[
        ["GEOID", "county", "births", "women_15_44", "minutes", "has_access",
         "nearest_facility", "high_level_minutes"]
    ].merge(
        after[
            ["GEOID", "minutes", "has_access", "nearest_facility", "high_level_minutes"]
        ],
        on="GEOID",
        suffixes=("_before", "_after"),
    )
    merged["minutes_change"] = (merged["minutes_after"] - merged["minutes_before"]).round(1)
    merged["lost_access"] = merged["has_access_before"] & ~merged["has_access_after"]
    merged["gained_access"] = ~merged["has_access_before"] & merged["has_access_after"]

    changed = merged[
        merged["lost_access"] | merged["gained_access"] | (merged["minutes_change"].abs() >= 0.1)
    ].copy()
    changed = changed.sort_values("minutes_change", ascending=False).reset_index(drop=True)

    lost = merged[merged["lost_access"]]
    gained = merged[merged["gained_access"]]
    affected = merged[merged["minutes_change"].abs() >= 0.1]

    total_births = merged["births"].sum()
    avg_before = float((merged["births"] * merged["minutes_before"]).sum() / total_births)
    avg_after = float((merged["births"] * merged["minutes_after"]).sum() / total_births)

    before_volumes = facility_volumes(before, baseline_active)
    after_volumes = facility_volumes(after, scenario_active)

    absorbers = _absorbing_facilities(merged, before_volumes, after_volumes)

    summary = {
        "threshold_minutes": ACCESS_THRESHOLD_MIN,
        "removed": sorted(set(remove_names or []) & set(removable_facility_names(facilities))),
        "added": [p["name"] for p in (add_points or [])],
        "counties_losing_access": int(len(lost)),
        "counties_gaining_access": int(len(gained)),
        "births_losing_access": int(lost["births"].sum()),
        "births_gaining_access": int(gained["births"].sum()),
        "births_affected": int(affected["births"].sum()),
        "women_losing_access": int(lost["women_15_44"].sum()),
        "women_gaining_access": int(gained["women_15_44"].sum()),
        "women_affected": int(affected["women_15_44"].sum()),
        "counties_affected": int(len(affected)),
        "avg_minutes_before": round(avg_before, 1),
        "avg_minutes_after": round(avg_after, 1),
        "avg_minutes_change": round(avg_after - avg_before, 1),
        "absorbing_facilities": absorbers,
        "active_facilities_before": int(len(baseline_active)),
        "active_facilities_after": int(len(scenario_active)),
    }

    return {
        "before": before,
        "after": after,
        "changed": changed,
        "scenario_facilities": scenario_facilities,
        "before_volumes": before_volumes,
        "after_volumes": after_volumes,
        "summary": summary,
    }


def _absorbing_facilities(merged: pd.DataFrame, before_volumes: pd.DataFrame,
                          after_volumes: pd.DataFrame) -> list[dict]:
    """Which facilities pick up the births displaced by the scenario."""
    reassigned = merged[merged["nearest_facility_before"] != merged["nearest_facility_after"]]
    if reassigned.empty:
        return []

    gained = (
        reassigned.groupby("nearest_facility_after")
        .agg(births_absorbed=("births", "sum"), counties_absorbed=("GEOID", "count"))
        .reset_index()
        .rename(columns={"nearest_facility_after": "name"})
    )
    before_map = dict(zip(before_volumes["name"], before_volumes["modeled_births"]))
    after_map = dict(zip(after_volumes["name"], after_volumes["modeled_births"]))

    out = []
    for row in gained.sort_values("births_absorbed", ascending=False).itertuples(index=False):
        name = row[0]
        out.append(
            {
                "name": name,
                "births_absorbed": int(row.births_absorbed),
                "counties_absorbed": int(row.counties_absorbed),
                "modeled_births_before": int(before_map.get(name, 0)),
                "modeled_births_after": int(after_map.get(name, 0)),
            }
        )
    return out
