#!/usr/bin/env python3
"""
Ingest georgia_facilities.json -> data/facilities.csv (load-ready for TigerData).

Input shape (one object per facility):
    {"name","city","state","in_state","maternal_level","status","lat","lon"}

Optionally merges the out-of-state border roster recovered from the hackathon
blueprint (data/facilities_partial.csv). Border rows have no coordinates, so
they are written with empty lat/lon and EXCLUDED from the active set until
geocoded -- the travel matrix guard in 004 will not accept them.

The expected-count assertions below come from the roster summary. They are a
tripwire: if the file you hand it does not match what the roster claims, the
load stops rather than silently importing a different dataset.

    python3 etl/ingest_facilities.py --json georgia_facilities.json --out data/
    python3 etl/ingest_facilities.py --json georgia_facilities.json --out data/ \
            --merge-border data/facilities_partial.csv
"""
import argparse, csv, json, re, sys
from collections import Counter

EXPECT_TOTAL   = 66
EXPECT_ACTIVE  = 62
EXPECT_CLOSED  = 4
EXPECT_LEVELS  = {"IV": 7, "III": 14, "II": 24, "I": 21}
EXPECT_CLOSED_NAMES = {
    "Elbert Memorial Hospital",
    "Washington County Regional Medical Center",
    "Dorminy Medical Center",
    "Wayne Memorial Hospital",
}
# Georgia's bounding box, generously padded. Catches swapped lat/lon, which is
# the single most common failure in hand-assembled geospatial data.
GA_BBOX = dict(lat=(30.3, 35.1), lon=(-85.7, -80.8))

COLS = ["facility_id","name","city","state_code","is_border_facility","maternal_level",
        "level_is_designated","status","lat","lon","source_citation"]

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:48]

def fail(msg):
    print(f"  FAIL  {msg}", file=sys.stderr)
    return 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", default="data")
    ap.add_argument("--merge-border")
    ap.add_argument("--allow-count-mismatch", action="store_true",
                    help="downgrade count assertions to warnings (use only if the roster changed)")
    a = ap.parse_args()

    raw = json.load(open(a.json))
    if isinstance(raw, dict):                       # tolerate {"facilities":[...]}
        raw = next(v for v in raw.values() if isinstance(v, list))

    rows, errors, seen = [], 0, set()
    for i, f in enumerate(raw):
        name = (f.get("name") or "").strip()
        if not name:
            errors += fail(f"record {i}: missing name")
            continue
        fid = "ga_" + slug(name)
        if fid in seen:
            errors += fail(f"duplicate facility name: {name!r}")
            continue
        seen.add(fid)

        lat, lon = f.get("lat"), f.get("lon")
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            errors += fail(f"{name}: non-numeric coordinates ({lat!r}, {lon!r})")
            continue
        if not (GA_BBOX["lat"][0] <= lat <= GA_BBOX["lat"][1]):
            errors += fail(f"{name}: lat {lat} outside Georgia (swapped lat/lon?)")
        if not (GA_BBOX["lon"][0] <= lon <= GA_BBOX["lon"][1]):
            errors += fail(f"{name}: lon {lon} outside Georgia (swapped lat/lon?)")

        level = (f.get("maternal_level") or "").strip().upper()
        if level and level not in EXPECT_LEVELS:
            errors += fail(f"{name}: unknown maternal_level {level!r}")

        status = (f.get("status") or "").strip().lower()
        status = "active" if status == "active" else "closed"

        rows.append(dict(
            facility_id=fid, name=name, city=(f.get("city") or "").strip(),
            state_code=(f.get("state") or "GA").strip(),
            is_border_facility="false" if f.get("in_state", True) else "true",
            maternal_level=level, level_is_designated="true" if level else "false",
            status=status, lat=f"{lat:.6f}", lon=f"{lon:.6f}",
            source_citation="georgia_facilities.json (MaternalGrid workspace roster)"))

    # ---- roster assertions -------------------------------------------------
    active = sum(1 for r in rows if r["status"] == "active")
    closed = sum(1 for r in rows if r["status"] == "closed")
    levels = Counter(r["maternal_level"] for r in rows if r["maternal_level"])
    checks = [
        ("total facilities",  len(rows), EXPECT_TOTAL),
        ("active",            active,    EXPECT_ACTIVE),
        ("inactive/closed",   closed,    EXPECT_CLOSED),
    ] + [(f"Level {lv}", levels.get(lv, 0), n) for lv, n in EXPECT_LEVELS.items()]

    print(f"\n  {'check':<22} {'actual':>7} {'expected':>9}   result")
    hard = 0
    for label, got, want in checks:
        ok = got == want
        hard += 0 if ok else 1
        print(f"  {label:<22} {got:>7} {want:>9}   {'PASS' if ok else 'MISMATCH'}")

    got_closed = {r["name"] for r in rows if r["status"] == "closed"}
    if got_closed != EXPECT_CLOSED_NAMES:
        hard += 1
        print(f"  closed-facility names differ:")
        print(f"     only in file:   {sorted(got_closed - EXPECT_CLOSED_NAMES)}")
        print(f"     only in roster: {sorted(EXPECT_CLOSED_NAMES - got_closed)}")
    else:
        print(f"  {'closed names match':<22} {'4':>7} {'4':>9}   PASS")

    if errors:
        sys.exit(f"\n{errors} record-level error(s); refusing to write.")
    if hard and not a.allow_count_mismatch:
        sys.exit(f"\n{hard} roster assertion(s) failed; refusing to write. "
                 f"Re-run with --allow-count-mismatch if the roster genuinely changed.")

    # ---- optional border merge --------------------------------------------
    if a.merge_border:
        n = 0
        for r in csv.DictReader(open(a.merge_border)):
            if r.get("is_border_facility") != "true":
                continue
            rows.append({c: r.get(c, "") for c in COLS}); n += 1
        print(f"\n  merged {n} border facilities (no coordinates; excluded from travel matrix)")

    out = f"{a.out}/facilities.csv"
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    print(f"\n  wrote {out}  ({len(rows)} rows, "
          f"{sum(1 for r in rows if r['lat'])} with coordinates)")

if __name__ == "__main__":
    main()
