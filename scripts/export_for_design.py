"""Export a self-contained snapshot of MaternalGrid's modeled output.

Design tools cannot read this repo, so this writes one JSON file holding the
statewide summary, a sample of counties, the facility list and both preset
scenario results. Paste it in as sample data so a mock-up renders real shaped
numbers instead of lorem ipsum.

Usage: python scripts/export_for_design.py [out.json]
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.access import compute_access, facility_volumes, statewide_summary  # noqa: E402
from src.config import ACCESS_THRESHOLD_MIN, AVG_SPEED_MPH, ROAD_FACTOR  # noqa: E402
from src.data_loader import (  # noqa: E402
    active_facilities,
    data_status,
    load_counties,
    load_facilities,
    load_geojson,
)
from src.presets import county_add_point, find_lavonia_facility, largest_gap_county  # noqa: E402
from src.simulate import run_scenario  # noqa: E402

COUNTY_COLS = [
    "GEOID", "county", "births", "women_15_44", "ob_providers",
    "births_per_ob_provider", "minutes", "has_access", "nearest_facility",
    "high_level_minutes", "mod_access_level",
]


def scenario_block(result):
    s = result["summary"]
    return {
        "summary": s,
        "changed_counties": json.loads(
            result["changed"][
                ["county", "births", "women_15_44", "minutes_before", "minutes_after",
                 "minutes_change", "nearest_facility_after", "lost_access", "gained_access"]
            ].to_json(orient="records")
        ),
    }


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "design_snapshot.json"

    counties = load_counties()
    facilities = load_facilities()
    geojson = load_geojson()
    active = active_facilities(facilities)
    access = compute_access(counties, active)
    statewide = statewide_summary(access, facilities, geojson)

    lavonia = find_lavonia_facility(facilities)
    gap = largest_gap_county(access)

    payload = {
        "app": "MaternalGrid",
        "subtitle": "Labor and delivery access planning for Georgia",
        "data_status": data_status(),
        "model_assumptions": {
            "road_factor": ROAD_FACTOR,
            "avg_speed_mph": AVG_SPEED_MPH,
            "access_threshold_minutes": ACCESS_THRESHOLD_MIN,
            "note": "All minutes are modeled from straight line distance, not real drive times.",
        },
        "statewide_summary": statewide,
        "counties_sample": json.loads(
            access.sort_values("minutes", ascending=False)[COUNTY_COLS].head(25).to_json(orient="records")
        ),
        "counties_all": json.loads(access[COUNTY_COLS].to_json(orient="records")),
        "facilities": json.loads(
            facilities[
                ["name", "city", "state", "in_state", "maternal_level", "status", "lat", "lon"]
            ].to_json(orient="records")
        ),
        "facility_volumes": json.loads(
            facility_volumes(access, active).to_json(orient="records")
        ),
        "scenarios": {},
    }

    if lavonia:
        payload["scenarios"]["lavonia_closure"] = scenario_block(
            run_scenario(facilities, remove_names=[lavonia], counties=counties)
        )
    if gap is not None:
        payload["scenarios"]["invest_largest_gap"] = scenario_block(
            run_scenario(facilities, add_points=[county_add_point(gap, "III")], counties=counties)
        )

    out_path.write_text(json.dumps(payload, indent=2, default=str))
    size_kb = out_path.stat().st_size / 1024
    print(f"wrote {out_path} ({size_kb:.0f} KB)")
    print(f"  {len(payload['counties_all'])} counties, {len(payload['facilities'])} facilities, "
          f"{len(payload['scenarios'])} scenarios")
    if size_kb > 400:
        print("  note: drop counties_all if you need a smaller paste; counties_sample is the top 25")


if __name__ == "__main__":
    main()
