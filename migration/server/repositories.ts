// server/repositories.ts — every read the app needs, against geo / health / analytics.
// All scenario work runs over the precomputed analytics.travel_matrix, so no PostGIS
// call is on the request path.
import { pool } from './db';

export interface CountyRow {
  geoid: string; county: string; lat: number; lon: number;
  nearest_facility_id: string; nearest_facility: string;
  modeled_minutes: number; has_access: boolean;
  births: number | null; mod_tier: string | null; is_desert: boolean | null;
}

export interface FacilityRow {
  facility_id: string; name: string; city: string | null; state_code: string;
  is_border_facility: boolean; maternal_level: string | null;
  status: string; lat: number; lon: number;
}

export interface ScenarioCountyRow {
  geoid: string; county: string; births: number | null;
  baseline_minutes: number; scenario_minutes: number; delta_minutes: number;
  baseline_facility_id: string; baseline_facility: string;
  scenario_facility_id: string; scenario_facility: string;
  access_state: 'lost' | 'gained' | 'shifted' | 'unchanged';
}

export interface ScenarioKpis {
  counties_lost_access: number; counties_gained_access: number;
  counties_shifted: number; births_displaced: number;
  worst_delta_minutes: number; avg_delta_minutes: number;
  baseline_avg_minutes: number; scenario_avg_minutes: number;
}

export interface AbsorptionRow {
  facility_id: string; facility: string; city: string | null;
  maternal_level: string | null; counties_absorbed: number;
  births_absorbed: number; baseline_births: number;
  pct_increase: number | null;   // null when the facility had no baseline catchment
}

// Numerics arrive from pg as strings; coerce at the boundary so the API is typed.
const num = (v: unknown): number => (v === null || v === undefined ? 0 : Number(v));

export async function getCounties(): Promise<CountyRow[]> {
  const { rows } = await pool.query(`
    SELECT geoid, county, lat, lon, nearest_facility_id, nearest_facility,
           modeled_minutes, has_access, births, mod_tier, is_desert
    FROM analytics.county_baseline ORDER BY county`);
  return rows.map(r => ({ ...r,
    lat: num(r.lat), lon: num(r.lon),
    modeled_minutes: num(r.modeled_minutes),
    births: r.births === null ? null : num(r.births) }));
}

export async function getFacilities(activeOnly = true): Promise<FacilityRow[]> {
  const { rows } = await pool.query(`
    SELECT facility_id, name, city, state_code, is_border_facility,
           maternal_level::text AS maternal_level, status::text AS status, lat, lon
    FROM geo.facilities
    ${activeOnly ? "WHERE status = 'active'" : ''}
    ORDER BY is_border_facility, name`);
  return rows.map(r => ({ ...r, lat: num(r.lat), lon: num(r.lon) }));
}

export async function getStatewideBaseline() {
  const { rows } = await pool.query('SELECT * FROM analytics.statewide_baseline');
  const r = rows[0];
  return {
    counties: num(r.counties),
    counties_no_access: num(r.counties_no_access),
    pct_no_access: num(r.pct_no_access),
    births_no_access: num(r.births_no_access),
    births_total: num(r.births_total),
    avg_minutes_birth_weighted: num(r.avg_minutes_birth_weighted),
    mod_deserts: num(r.mod_deserts),
  };
}

export async function getCountyDetail(geoid: string) {
  const [base, series] = await Promise.all([
    pool.query('SELECT * FROM analytics.county_baseline WHERE geoid = $1', [geoid]),
    pool.query('SELECT year, births FROM health.county_births WHERE geoid = $1 ORDER BY year', [geoid]),
  ]);
  if (base.rowCount === 0) return null;
  const r = base.rows[0];
  return {
    ...r,
    lat: num(r.lat), lon: num(r.lon), modeled_minutes: num(r.modeled_minutes),
    births: r.births === null ? null : num(r.births),
    birth_series: series.rows.map(s => ({ year: num(s.year), births: num(s.births) })),
  };
}

export async function simulateClosure(closedIds: string[]): Promise<ScenarioCountyRow[]> {
  const { rows } = await pool.query('SELECT * FROM sim.simulate_closure($1::text[])', [closedIds]);
  return rows.map(r => ({ ...r,
    births: r.births === null ? null : num(r.births),
    baseline_minutes: num(r.baseline_minutes),
    scenario_minutes: num(r.scenario_minutes),
    delta_minutes: num(r.delta_minutes) }));
}

export async function scenarioKpis(closedIds: string[]): Promise<ScenarioKpis> {
  const { rows } = await pool.query('SELECT * FROM sim.scenario_kpis($1::text[])', [closedIds]);
  const r = rows[0];
  return {
    counties_lost_access: num(r.counties_lost_access),
    counties_gained_access: num(r.counties_gained_access),
    counties_shifted: num(r.counties_shifted),
    births_displaced: num(r.births_displaced),
    worst_delta_minutes: num(r.worst_delta_minutes),
    avg_delta_minutes: num(r.avg_delta_minutes),
    baseline_avg_minutes: num(r.baseline_avg_minutes),
    scenario_avg_minutes: num(r.scenario_avg_minutes),
  };
}

export async function absorption(closedIds: string[]): Promise<AbsorptionRow[]> {
  const { rows } = await pool.query('SELECT * FROM sim.absorption($1::text[])', [closedIds]);
  return rows.map(r => ({ ...r,
    counties_absorbed: num(r.counties_absorbed),
    births_absorbed: num(r.births_absorbed),
    baseline_births: num(r.baseline_births),
    pct_increase: r.pct_increase === null ? null : num(r.pct_increase) }));
}
