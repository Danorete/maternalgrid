"""Validate a compiled facilities CSV before the app depends on it.

Usage: python scripts/check_facilities.py data/facilities_andre.csv

Reports errors (the app will misbehave or silently drop rows) and warnings
(probably not what you meant). Exits 1 if there are any errors.
"""

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import ACTIVE_STATUS, FACILITY_LEVELS  # noqa: E402

REQUIRED = ["name", "in_state", "maternal_level", "status", "lat", "lon"]
TRUEISH = {"true", "1", "yes", "y", "t"}

# Georgia's bounding box, generous enough to include the border hospitals a
# planner would legitimately list in neighbouring states.
LAT_RANGE = (29.5, 37.0)
LON_RANGE = (-87.5, -79.5)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: check_facilities.py <path to facilities csv>")
    path = Path(sys.argv[1])
    if not path.exists():
        raise SystemExit(f"no such file: {path}")

    df = pd.read_csv(path)
    errors, warnings = [], []

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        errors.append(f"missing required column(s): {', '.join(missing)}")
        print_report(path, df, errors, warnings)
        raise SystemExit(1)

    names = df["name"].astype(str).str.strip()
    if (names == "").any():
        errors.append(f"{int((names == '').sum())} row(s) have an empty name")
    dupes = [n for n, c in Counter(names).items() if c > 1]
    if dupes:
        errors.append(
            "duplicate name(s), which would merge into one facility in the modeled "
            f"volume table: {', '.join(dupes[:5])}"
        )

    lat = pd.to_numeric(df["lat"], errors="coerce")
    lon = pd.to_numeric(df["lon"], errors="coerce")
    bad_coords = lat.isna() | lon.isna()
    if bad_coords.any():
        errors.append(
            f"{int(bad_coords.sum())} row(s) have unreadable lat or lon and would be "
            f"dropped silently: {', '.join(names[bad_coords].head(5))}"
        )
    off_map = (~bad_coords) & (
        ~lat.between(*LAT_RANGE) | ~lon.between(*LON_RANGE)
    )
    if off_map.any():
        warnings.append(
            f"{int(off_map.sum())} row(s) sit outside the Georgia region; check for "
            f"a swapped lat/lon or a missing minus sign: {', '.join(names[off_map].head(5))}"
        )

    levels = df["maternal_level"].astype(str).str.strip().str.upper().str.replace(
        "LEVEL ", "", regex=False
    )
    bad_levels = ~levels.isin(FACILITY_LEVELS)
    if bad_levels.any():
        errors.append(
            f"{int(bad_levels.sum())} row(s) have a maternal_level outside "
            f"{', '.join(FACILITY_LEVELS)}: {', '.join(levels[bad_levels].unique()[:5])}"
        )

    status = df["status"].astype(str).str.strip().str.title()
    active = status == ACTIVE_STATUS
    if not active.any():
        errors.append(
            f'no row has status "{ACTIVE_STATUS}", so every county would show as '
            "having no facility at all"
        )
    odd_status = ~status.isin({ACTIVE_STATUS, "Inactive", "Closed"})
    if odd_status.any():
        warnings.append(
            f"{int(odd_status.sum())} row(s) have a status that is not Active, "
            f"Inactive or Closed and will count as not active: "
            f"{', '.join(status[odd_status].unique()[:5])}"
        )

    in_state = df["in_state"].astype(str).str.strip().str.lower()
    odd_bool = ~in_state.isin(TRUEISH | {"false", "0", "no", "n", "f"})
    if odd_bool.any():
        warnings.append(
            f"{int(odd_bool.sum())} row(s) have an in_state value that is not clearly "
            f"true or false and will be read as false, meaning fixed border facility: "
            f"{', '.join(in_state[odd_bool].unique()[:5])}"
        )
    ga_active = int((in_state.isin(TRUEISH) & active).sum())
    if ga_active == 0:
        errors.append("no active Georgia facility, so no scenario could close anything")

    print_report(path, df, errors, warnings, ga_active, int(active.sum()), levels[active])
    raise SystemExit(1 if errors else 0)


def print_report(path, df, errors, warnings, ga_active=None, total_active=None, active_levels=None):
    print(f"\n{path}  ({len(df)} rows)")
    if ga_active is not None:
        print(f"  active facilities        {total_active}  "
              f"({ga_active} Georgia, {total_active - ga_active} border)")
        counts = Counter(active_levels)
        print("  active by maternal level " +
              ", ".join(f"{lvl}: {counts.get(lvl, 0)}" for lvl in FACILITY_LEVELS))
        high = sum(counts.get(lvl, 0) for lvl in ("III", "IV"))
        if high == 0:
            print("  note: no active Level III or IV, so that map metric will be empty")

    if errors:
        print(f"\n  {len(errors)} ERROR(S), the app will not behave correctly:")
        for e in errors:
            print(f"    - {e}")
    if warnings:
        print(f"\n  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    - {w}")
    if not errors and not warnings:
        print("\n  looks good, no problems found")
    print()


if __name__ == "__main__":
    main()
