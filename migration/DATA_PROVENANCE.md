# Data provenance — READ BEFORE QUOTING ANY NUMBER

`georgia_facilities.json` and `georgia_counties.json` arrived from AI Studio. Both had
JSON syntax errors (1 and 48 respectively) which were repaired. After repair, each field
was validated against the authoritative source. **The two files are not equally reliable.**

## georgia_facilities.json — TRUSTED, used in full

| Check | Result |
|---|---|
| 66 total / 62 active / 4 inactive | PASS |
| Level IV/III/II/I = 7/14/24/21 | PASS |
| Closed facility names | match exactly |
| Coordinates inside Georgia | 66/66 |

## georgia_counties.json — COORDINATES ONLY

The centroids are real. **Three other fields in this file are synthetic and are NOT loaded.**

| Field | Verdict | Evidence |
|---|---|---|
| `lat` / `lon` | **USED** | 159/159 in bounds; reproduces the app's own travel model exactly (see below) |
| `births` | **REJECTED** | **0 of 159** match GDPH OASIS. File total 126,007 vs OASIS 126,304 — close in aggregate, wrong in every single county. That is the signature of a distribution generated to hit a target total. |
| `women_15_44` | **REJECTED** | `births / women_15_44` is effectively constant across all 159 counties (stdev 0.00009; multiplier 17.37–17.53). It was derived from births by multiplication, not sourced from Census. |
| `ob_providers` | **REJECTED** | Derived from the same synthetic series; no independent source. |
| `mod_access_level` | **REJECTED** | Only **86/159** agree with the real March of Dimes file. The desert *count* is 70 in both, but only **57 overlap** — so 13 counties are wrongly marked desert and 13 real deserts are missing. |

Births and MoD tiers are loaded from the authoritative files instead
(`births.csv` / OASIS and `mod_benchmark.csv` / March of Dimes).
`women_15_44` and `ob_providers` are **not loaded at all** — there is no real source for
them yet. Do not quote the "295,666 women beyond 30 minutes" figure; it has no basis.

## Coordinate validation

Recomputing nearest-facility and modeled travel time from the centroids, using
Haversine x 1.30 / 45 mph over the 68 active facilities, reproduces the app's own output:

- nearest facility name: **159/159 match**
- modeled minutes: **159/159 within 0.15 min** (median deviation 0.02, max 0.05)

So the spatial layer is sound and the documented travel model is exactly what the app runs.

## Verified baselines (real data, recomputed)

| Metric | Value |
|---|---|
| Counties beyond 30 modeled minutes | **74 / 159 (46.5%)** |
| OASIS births in those counties | **13,029** |
| Births-weighted average travel time | **11.1 min** |
| Active delivering facilities | **68** (62 in-state + 6 border) |
| Travel matrix size | **159 x 68 = 10,812** |
