#!/usr/bin/env python3
"""
MaternalGrid ETL — turns the raw GDPH/OASIS and March of Dimes exports into
load-ready CSVs for TigerData.

Inputs (raw, as downloaded):
  dph_wq_Number_of_Births_by_Residence_*.xlsx   GDPH OASIS, births by county 2015-2024
  mod_benchmark.csv                             March of Dimes 2026 access tiers
  maternitycaredesert_GA_2026.csv               same data, alternate shape (redundant)

Outputs (data/):
  counties.csv            159 rows  - GEOID, name  (centroids NOT yet populated)
  county_births.csv     1,590 rows  - GEOID, year, births  (long format)
  mod_access_tiers.csv    159 rows  - GEOID, tier, is_desert

Run:  python3 etl/build_csvs.py --raw <dir-with-raw-files> --out data/
"""
import argparse, csv, glob, os, re, sys
import openpyxl

TIER_MAP = {
    "Access to Maternity Care":  "full",
    "Moderate Access to Care":   "moderate",
    "Low Access to Care":        "low",
    "Maternity Care Desert":     "desert",
}

def load_oasis_births(path):
    """OASIS export: 3 header rows, 159 county rows, then a footer block."""
    ws = openpyxl.load_workbook(path, data_only=True)["Data"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[2]                                   # Geography | FIPS | 2015..2024 | Selected Years Total
    years = [str(c) for c in header[2:] if c and re.fullmatch(r"\d{4}", str(c))]
    out, seen = [], set()
    for r in rows[4:]:
        geoid = str(r[1]).strip() if r[1] is not None else ""
        if not geoid.isdigit() or len(geoid) != 5:     # stops at the footer block
            continue
        if geoid in seen:
            raise ValueError(f"duplicate GEOID {geoid}")
        seen.add(geoid)
        name = str(r[0]).strip()
        for i, y in enumerate(years):
            v = r[2 + i]
            out.append((geoid, name, int(y), None if v is None else int(v)))
    return out, years

def load_mod_tiers(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            geoid = (rec.get("GEOID") or "").strip().zfill(5)
            if not geoid.isdigit():
                continue
            level = (rec.get("mod_access_level") or "").strip()
            if level not in TIER_MAP:
                raise ValueError(f"unmapped MoD tier {level!r} for {geoid}")
            rows.append((geoid, TIER_MAP[level], level,
                         str(rec.get("mod_is_desert", "")).strip().lower() == "true"))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", default="data")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    xlsx = glob.glob(os.path.join(a.raw, "*Number_of_Births_by_Residence*.xlsx"))
    if not xlsx:
        sys.exit("no OASIS births xlsx found in --raw")
    births, years = load_oasis_births(xlsx[0])

    counties = sorted({(g, n) for g, n, _, _ in births})
    with open(f"{a.out}/counties.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["geoid", "name", "centroid_lat", "centroid_lon"])
        for g, n in counties:
            w.writerow([g, n, "", ""])          # centroids filled from TIGER later

    with open(f"{a.out}/county_births.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["geoid", "year", "births"])
        for g, _, y, v in births:
            w.writerow([g, y, "" if v is None else v])

    mod_src = glob.glob(os.path.join(a.raw, "*mod_benchmark*.csv"))
    if not mod_src:
        sys.exit("no mod_benchmark.csv found in --raw")
    tiers = load_mod_tiers(mod_src[0])
    with open(f"{a.out}/mod_access_tiers.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["geoid", "tier", "tier_label", "is_desert"])
        for g, t, lbl, d in tiers:
            w.writerow([g, t, lbl, str(d).lower()])

    # Reconcile: every county must carry a tier, and vice versa.
    cg, tg = {g for g, _ in counties}, {g for g, _, _, _ in tiers}
    if cg != tg:
        raise ValueError(f"county/tier GEOID mismatch: only-births={cg-tg} only-mod={tg-cg}")

    print(f"counties.csv          {len(counties):>5} rows")
    print(f"county_births.csv     {len(births):>5} rows  ({years[0]}-{years[-1]})")
    print(f"mod_access_tiers.csv  {len(tiers):>5} rows")
    print(f"reconciled: {len(cg)} GEOIDs consistent across both sources")

if __name__ == "__main__":
    main()
