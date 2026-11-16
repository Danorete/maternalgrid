# Wiring the app server to Tiger Data

## 1. Install

```bash
npm install pg
npm install -D @types/pg
```

## 2. Environment

```bash
# .env — never commit this
TIGER_URL="postgres://tsdbadmin:PASSWORD@HOST.tsdb.cloud.timescale.com:PORT/tsdb?sslmode=require"
```

Copy the string from the Tiger Cloud console. Keep `sslmode=require`.
`db.ts` skips TLS only when the URL says `sslmode=disable`, which is for a local
dev database — never for Tiger. It never sets `rejectUnauthorized:false`.

## 3. Run the query migration

```bash
psql "$TIGER_URL" -f sql/006_app_queries.sql
```

Creates `analytics.county_baseline`, `analytics.statewide_baseline`,
`sim.simulate_closure()`, `sim.scenario_kpis()`, `sim.absorption()`.
None of them touch PostGIS — `analytics.travel_matrix` is precomputed, so a
scenario is a minimum over the remaining facility columns.

## 4. Mount the routes

```ts
import express from 'express';
import { maternalGridRoutes } from './server/routes';

const app = express();
app.use(express.json());
app.use('/api', maternalGridRoutes);
app.listen(3001);
```

## 5. Replace the sample data in the client

| Old (bundled sample data) | New |
|---|---|
| county array import | `GET /api/counties` → 159 rows with nearest facility, minutes, births, MoD tier |
| facility array import | `GET /api/facilities` → 68 active (62 in-state + 6 border) |
| in-browser `runSimulation()` | `POST /api/simulate` `{ "closedFacilityIds": ["ga_..."] }` |
| hand-written summary strip | `GET /api/baseline` |
| county detail panel | `GET /api/counties/:geoid` (includes the 10-year birth series) |

`POST /api/simulate` returns `kpis`, a ready-to-render `impact` statement,
`changedCounties`, `absorbingFacilities`, and the full 159-row `counties` array
for recolouring the map.

## Verified against the live schema

| Endpoint | Result |
|---|---|
| `/api/health` | `{"ok":true}` |
| `/api/baseline` | 159 counties, 74 no-access (46.5%), 13,029 births, 11.1 min, 70 deserts |
| `/api/counties` | 159 rows |
| `/api/facilities` | 68 active |
| `/api/counties/13147` | Hart County + 10-year birth series |
| `/api/simulate` (Lavonia) | 1 lost, 2 shifted, 265 births displaced, worst delta 18.29 min |
| unknown facility id | HTTP 400 with the offending id |
| empty scenario | neutral severity, baseline headline |
| latency (warm) | **~48 ms** end-to-end, against a 400 ms target |

Typechecks clean under `tsc --strict`.

## Known edge case

A facility with no baseline catchment (a border hospital that was nobody's
nearest) returns `pct_increase: null` in `absorbingFacilities` — you cannot
compute a percentage increase from zero. Render that as "new catchment" rather
than a blank cell. In the Lavonia scenario, AnMed Health Medical Center hits this.
