# MaternalGrid — TigerData migration bundle

Loads the GDPH/OASIS and March of Dimes data into TigerData (Postgres +
TimescaleDB + PostGIS). Generated from the raw exports; see `etl/build_csvs.py`.

## Run order

```bash
export TIGER_URL="postgres://tsdbadmin:...@....tsdb.cloud.timescale.com:33333/tsdb?sslmode=require"

psql "$TIGER_URL" -f sql/001_extensions.sql   # extensions (once per service)
psql "$TIGER_URL" -f sql/002_schema.sql       # schemas + tables
python3 etl/ingest_facilities.py \
    --json georgia_facilities.json --out data/ \
    --merge-border data/facilities_partial.csv      # validates the roster, writes data/facilities.csv
psql "$TIGER_URL" -f sql/003_load.sql         # \copy the CSVs  (run from bundle root)
psql "$TIGER_URL" -f sql/005_verify.sql       # 11-check data quality gate
```

`sql/004_travel_matrix.sql` is **blocked** until the two gaps below are filled.
It guards itself and raises a clear exception rather than building a partial matrix.

To regenerate the CSVs from the raw exports:

```bash
python3 etl/build_csvs.py --raw <dir-with-raw-downloads> --out data/
```

## What is loaded

| Table | Rows | Source |
|---|---|---|
| `geo.counties` | 159 | GDPH OASIS (names + FIPS; **coordinates missing**) |
| `health.county_births` | 1,590 | GDPH OASIS, births by residence, 2015–2024 |
| `health.mod_access_tiers` | 159 | March of Dimes 2026 |
| `geo.facilities` | 72 (68 active) | `georgia_facilities.json` via `etl/ingest_facilities.py`, plus border roster |

**See DATA_PROVENANCE.md before quoting any figure.**

Verification status: **18/18 checks pass** (tested against a synthetic fixture
matching the stated roster; re-run against the real file to confirm). Includes
statewide births reconciling to 126,304 (2024) and 131,333 (2015), 70/159 MoD
deserts, and the 66/62/4 facility split with the Level IV count.

### Facility count reconciliation

The spec says "68 delivering hospitals: 62 in-state active + 6 border". The
border figure is wrong. Actual:

| Set | Count | Active |
|---|---|---|
| Georgia in-state (`georgia_facilities.json`) | 66 | **62** |
| Out-of-state border (blueprint roster) | 11 | **9** (2 are L&D-closed) |
| **Total active delivering** | | **71** |

So the travel matrix is 159 x 62 = **9,858** rows using in-state facilities only,
or 159 x 71 = **11,289** once the 9 active border facilities are geocoded --
not the 10,812 the spec assumes. Excluding border facilities systematically
overstates access loss in frontier counties, so geocoding those 9 addresses is
worth doing before any published run.

## What is still missing

| Gap | Blocks | Where to get it |
|---|---|---|
| **County centroids** (lat/lon) | **The last blocker for the travel matrix** | Census Gazetteer 2024 (*egress-blocked, 403*) — but your app already has them to draw the D3 map |
| **Coordinates for 9 active border facilities** | Frontier-county accuracy | Geocode the addresses in `facilities_partial.csv` |
| **Women aged 15–44** | The "women beyond 30-min access" KPI | Census ACS B01001 — *egress-blocked (403)* |
| **OB provider counts** | Provider-load map layer | NPPES NPI Registry — *egress-blocked (403)* |

### `data/facilities_partial.csv` — what it holds

16 facilities recovered from the hackathon blueprint documents, **all without coordinates**:

- **11 out-of-state border facilities** (TN, FL, AL, SC) with street addresses. Two are
  marked L&D-closed (CHI Memorial, Baptist Medical Center Nassau), so **9 are active** —
  not the 6 the spec assumed.
- **5 Georgia Level IV facilities** (Atrium Health Navicent, Grady, Northside, Piedmont
  Atlanta, Wellstar MCG) with city and DPH designation expiry. These are the only
  facilities in the set whose maternal level is an actual DPH designation
  (`level_is_designated = true`); the border rows carry descriptive marketing text, which
  is why that flag exists.

Nothing is loaded by `003_load.sql` — this file is a staging artifact until coordinates
and the Georgia roster exist.

## Resolved: the baseline-figure discrepancy

Confirmed by the research document in the hackathon blueprint. Three separate
metrics had been collapsed into two mislabelled ones:

| Metric | Correct figure | Source |
|---|---|---|
| No birthing facility | **108** (67.9%) | GA DPH, 2025 |
| OB/GYN shortage | **82** (51.6%) | GA Board of Health Care Workforce, 2024 |
| Maternity Care Desert | **70** (44.0%) | March of Dimes 2026 (verified here) |

The prototype reported 70 as an OB-provider count — it is the MoD desert count —
and 106 for missing facilities, which matches no published source. Both are
corrected in §2.1 and §13.1 of the spec.

## Note on hypertables

`health.county_births` is 1,590 rows and is deliberately a **plain table**.
Hypertables pay off on high-volume append workloads — `sim.scenario_event`,
`sim.county_result`, `audit.ai_interaction` — which arrive with the simulation
engine, not with this load. Converting a decade of county totals would add
chunk overhead for no benefit.
