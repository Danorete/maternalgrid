"""Generate clearly labelled PLACEHOLDER datasets for the MaternalGrid demo.

Every file this script writes carries a _TEST suffix and is synthetic. The app
refuses to treat any of it as real: it shows a yellow banner naming each test
file in use, and it switches to the real file automatically the moment a
same named file without the _TEST suffix appears in data/.

Real sources that were NOT reachable from this build environment
(census.gov is blocked by the egress policy, OASIS and NPPES have no open
mirror), so these stand in until the real extracts land:
  births.csv         Georgia OASIS 2024
  women_15_44.csv    Census ACS 5 year, table B01001
  providers.csv      NPPES NPI Registry, OB/GYN and midwife taxonomies
  mod_benchmark.csv  March of Dimes county access levels

The county geography (data/counties.csv, data/ga_counties.geojson) IS real and
is built separately by scripts/build_base_data.py.

Numbers are deterministic: a fixed seed plus a fixed county weight table, so
two runs produce identical files and the demo never shifts under you.

Usage: python scripts/build_test_data.py
"""

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SEED = 20260919
YEAR = 2024

# Statewide totals the synthetic county values are scaled to hit. These are
# order of magnitude anchors for Georgia so the demo reads plausibly. They are
# still placeholders, not a cited statistic.
TARGET_BIRTHS = 126_000
TARGET_WOMEN_15_44 = 2_200_000
TARGET_DESERT_COUNTIES = 70  # March of Dimes reports 44 percent of GA counties
TARGET_NO_PROVIDER_COUNTIES = 70  # March of Dimes: 44 percent with no OB clinician

# Relative population weight tiers. Tier 1 is metro Atlanta scale, tier 5 is the
# smallest rural counties. Used only to shape the synthetic distribution.
TIERS = {
    1: (["Fulton", "Gwinnett", "Cobb", "DeKalb"], 60.0),
    2: (["Chatham", "Clayton", "Cherokee", "Forsyth", "Henry", "Richmond",
         "Hall", "Muscogee", "Paulding", "Houston", "Bibb", "Columbia"], 22.0),
    3: (["Douglas", "Coweta", "Fayette", "Carroll", "Newton", "Bartow",
         "Lowndes", "Whitfield", "Clarke", "Rockdale", "Dougherty", "Floyd",
         "Walton", "Barrow", "Effingham", "Liberty", "Glynn", "Troup",
         "Camden", "Bulloch", "Spalding", "Jackson", "Gordon", "Catoosa"], 9.0),
    4: (["Laurens", "Thomas", "Walker", "Baldwin", "Colquitt", "Tift", "Ware",
         "Habersham", "Gilmer", "Harris", "Lumpkin", "Oconee", "Peach",
         "Pickens", "Polk", "Putnam", "Sumter", "Toombs", "Upson", "Wayne",
         "White", "Dawson", "Decatur", "Elbert", "Fannin", "Franklin",
         "Grady", "Haralson", "Hart", "Jones", "Lee", "Madison", "McDuffie",
         "Monroe", "Murray", "Bryan", "Butts", "Chattooga", "Coffee", "Cook",
         "Crisp", "Dade", "Dodge", "Emanuel", "Screven", "Stephens",
         "Tattnall", "Union", "Washington", "Worth"], 3.2),
}
DEFAULT_WEIGHT = 1.0  # tier 5: everything not named above

MOD_LEVELS = ["Full access", "Moderate access", "Low access", "Maternity care desert"]

# The placeholder facility list now lives in data/facilities_TEST.csv directly,
# since it is a hand curated set of real Georgia and border hospital locations
# rather than anything generated. This script no longer rewrites it; edit the
# CSV, then run scripts/check_facilities.py to validate it.


def county_weight(name):
    for _tier, (names, weight) in TIERS.items():
        if name in names:
            return weight
    return DEFAULT_WEIGHT


def read_counties():
    with (DATA / "counties.csv").open() as fh:
        return [(r["GEOID"], r["county"]) for r in csv.DictReader(fh)]


def write_csv(path, header, rows):
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


def main():
    rng = random.Random(SEED)
    counties = read_counties()
    if not counties:
        raise SystemExit("data/counties.csv is empty; run build_base_data.py first")

    # Jitter each county's weight a little so the map is not visibly tiered.
    weights = {}
    for geoid, name in counties:
        base = county_weight(name)
        weights[geoid] = base * rng.uniform(0.6, 1.5)
    total_w = sum(weights.values())

    births_rows, women_rows, prov_rows = [], [], []
    for geoid, name in counties:
        share = weights[geoid] / total_w
        births = max(5, round(TARGET_BIRTHS * share))
        women = max(200, round(TARGET_WOMEN_15_44 * share))

        births_rows.append((geoid, name, YEAR, births))
        women_rows.append((geoid, name, women))

    # Provider supply follows birth demand, and the counties with the smallest
    # birth counts are left with no obstetric clinician at all, so the share of
    # zero provider counties lands on the 44 percent March of Dimes reports.
    by_births = sorted(births_rows, key=lambda r: r[3])
    zero_provider = {r[0] for r in by_births[:TARGET_NO_PROVIDER_COUNTIES]}
    for geoid, name, _year, births in births_rows:
        if geoid in zero_provider:
            ob_gyn = midwife = 0
        else:
            ob_gyn = max(1, round(births / rng.uniform(140, 260)))
            midwife = max(0, round(births / rng.uniform(600, 1800)))
        prov_rows.append((geoid, name, ob_gyn, midwife, ob_gyn + midwife))

    # March of Dimes style levels: the smallest birth counts become deserts,
    # so the desert count lands on the reported 70 of 159 counties.
    ordered = sorted(births_rows, key=lambda r: r[3])
    level_by_geoid = {}
    for rank, row in enumerate(ordered):
        if rank < TARGET_DESERT_COUNTIES:
            level = MOD_LEVELS[3]
        elif rank < TARGET_DESERT_COUNTIES + 30:
            level = MOD_LEVELS[2]
        elif rank < TARGET_DESERT_COUNTIES + 65:
            level = MOD_LEVELS[1]
        else:
            level = MOD_LEVELS[0]
        level_by_geoid[row[0]] = level

    mod_rows = [
        (geoid, name, level_by_geoid[geoid], int(level_by_geoid[geoid] == MOD_LEVELS[3]))
        for geoid, name in counties
    ]

    write_csv(DATA / "births_TEST.csv", ["GEOID", "county", "year", "births"], births_rows)
    write_csv(DATA / "women_15_44_TEST.csv", ["GEOID", "county", "women_15_44"], women_rows)
    write_csv(DATA / "providers_TEST.csv",
              ["GEOID", "county", "ob_gyn", "midwives", "ob_providers"], prov_rows)
    write_csv(DATA / "mod_benchmark_TEST.csv",
              ["GEOID", "county", "mod_access_level", "mod_is_desert"], mod_rows)
    print(f"\ntotal synthetic births {sum(r[3] for r in births_rows):,}")
    print(f"total synthetic women 15 to 44 {sum(r[2] for r in women_rows):,}")
    print(f"counties with zero OB providers {sum(1 for r in prov_rows if r[4] == 0)}")
    print(f"March of Dimes style desert counties {sum(r[3] for r in mod_rows)}")


if __name__ == "__main__":
    main()
