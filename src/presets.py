"""The two demo presets, kept out of the UI so they can be tested directly."""

from __future__ import annotations

import pandas as pd

LAVONIA_TOKENS = ("lavonia", "sacred heart")


def find_lavonia_facility(facilities: pd.DataFrame) -> str | None:
    """The Lavonia unit, if the facility table happens to contain it."""
    mask = facilities["is_active"] & facilities["in_state"]
    for name in facilities.loc[mask, "name"]:
        lowered = name.lower()
        if any(token in lowered for token in LAVONIA_TOKENS):
            return name
    return None


def largest_gap_county(access: pd.DataFrame) -> pd.Series | None:
    """The county with the most births beyond the access threshold."""
    beyond = access[~access["has_access"]]
    if beyond.empty:
        return None
    return beyond.sort_values("births", ascending=False).iloc[0]


def county_add_point(county_row: pd.Series, level: str = "II") -> dict:
    """A scenario facility placed at a county centroid."""
    return {
        "name": f"New facility: {county_row['county']} County (scenario)",
        "city": f"{county_row['county']} County",
        "state": "GA",
        "in_state": True,
        "maternal_level": level,
        "lat": float(county_row["lat"]),
        "lon": float(county_row["lon"]),
        "source": "Scenario: added at county centroid",
    }
