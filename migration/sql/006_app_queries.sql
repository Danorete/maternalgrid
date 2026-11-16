-- 006_app_queries.sql — views and functions the app server calls.
-- None of these need PostGIS: analytics.travel_matrix is precomputed, so
-- every scenario is a minimum over the remaining facility columns.

-- ── Baseline: nearest active facility per county ────────────────────────────
CREATE OR REPLACE VIEW analytics.county_baseline AS
SELECT DISTINCT ON (m.geoid)
       m.geoid,
       c.name                AS county,
       c.centroid_lat        AS lat,
       c.centroid_lon        AS lon,
       m.facility_id         AS nearest_facility_id,
       f.name                AS nearest_facility,
       m.modeled_minutes,
       (m.modeled_minutes <= 30.0) AS has_access,
       b.births,
       t.tier                AS mod_tier,
       t.is_desert
FROM   analytics.travel_matrix m
JOIN   geo.facilities f USING (facility_id)
JOIN   geo.counties   c ON c.geoid = m.geoid
LEFT   JOIN health.county_births b ON b.geoid = m.geoid AND b.year = 2024
LEFT   JOIN health.mod_access_tiers t ON t.geoid = m.geoid
WHERE  f.status = 'active'
ORDER  BY m.geoid, m.modeled_minutes ASC;

-- ── Statewide baseline KPIs ─────────────────────────────────────────────────
CREATE OR REPLACE VIEW analytics.statewide_baseline AS
SELECT count(*)                                            AS counties,
       count(*) FILTER (WHERE NOT has_access)              AS counties_no_access,
       round(100.0*count(*) FILTER (WHERE NOT has_access)/count(*),1) AS pct_no_access,
       sum(births) FILTER (WHERE NOT has_access)           AS births_no_access,
       sum(births)                                         AS births_total,
       round(sum(modeled_minutes*births)/sum(births),1)    AS avg_minutes_birth_weighted,
       count(*) FILTER (WHERE is_desert)                   AS mod_deserts
FROM   analytics.county_baseline;

-- ── Scenario: close facilities, re-index every county ───────────────────────
CREATE OR REPLACE FUNCTION sim.simulate_closure(p_closed TEXT[])
RETURNS TABLE (
    geoid CHAR(5), county TEXT, births INTEGER,
    baseline_minutes NUMERIC, scenario_minutes NUMERIC, delta_minutes NUMERIC,
    baseline_facility_id TEXT, baseline_facility TEXT,
    scenario_facility_id TEXT, scenario_facility TEXT,
    access_state TEXT
) LANGUAGE sql STABLE AS $fn$
    WITH scenario AS (
        SELECT DISTINCT ON (m.geoid)
               m.geoid, m.facility_id, m.modeled_minutes
        FROM   analytics.travel_matrix m
        JOIN   geo.facilities f USING (facility_id)
        WHERE  f.status = 'active'
          AND  NOT (m.facility_id = ANY(p_closed))
        ORDER  BY m.geoid, m.modeled_minutes ASC
    )
    SELECT b.geoid,
           b.county,
           b.births,
           b.modeled_minutes,
           s.modeled_minutes,
           round(s.modeled_minutes - b.modeled_minutes, 2),
           b.nearest_facility_id,
           b.nearest_facility,
           s.facility_id,
           sf.name,
           CASE WHEN b.has_access AND s.modeled_minutes > 30.0 THEN 'lost'
                WHEN NOT b.has_access AND s.modeled_minutes <= 30.0 THEN 'gained'
                WHEN s.facility_id <> b.nearest_facility_id THEN 'shifted'
                ELSE 'unchanged' END
    FROM   analytics.county_baseline b
    JOIN   scenario s USING (geoid)
    JOIN   geo.facilities sf ON sf.facility_id = s.facility_id
    ORDER  BY (s.modeled_minutes - b.modeled_minutes) DESC, b.births DESC;
$fn$;

-- ── Scenario KPIs (one row, ready for the impact banner) ────────────────────
CREATE OR REPLACE FUNCTION sim.scenario_kpis(p_closed TEXT[])
RETURNS TABLE (
    counties_lost_access INTEGER, counties_gained_access INTEGER,
    counties_shifted INTEGER, births_displaced BIGINT,
    worst_delta_minutes NUMERIC, avg_delta_minutes NUMERIC,
    baseline_avg_minutes NUMERIC, scenario_avg_minutes NUMERIC
) LANGUAGE sql STABLE AS $fn$
    WITH r AS (SELECT * FROM sim.simulate_closure(p_closed))
    SELECT count(*) FILTER (WHERE access_state='lost')::int,
           count(*) FILTER (WHERE access_state='gained')::int,
           count(*) FILTER (WHERE access_state='shifted')::int,
           COALESCE(sum(births) FILTER (WHERE access_state='lost'),0),
           COALESCE(max(delta_minutes),0),
           round(AVG(delta_minutes),2),
           round(sum(baseline_minutes*births)/NULLIF(sum(births),0),1),
           round(sum(scenario_minutes*births)/NULLIF(sum(births),0),1)
    FROM r;
$fn$;

-- ── Absorption: which facilities inherit displaced births ───────────────────
CREATE OR REPLACE FUNCTION sim.absorption(p_closed TEXT[])
RETURNS TABLE (
    facility_id TEXT, facility TEXT, city TEXT, maternal_level TEXT,
    counties_absorbed INTEGER, births_absorbed BIGINT,
    baseline_births BIGINT, pct_increase NUMERIC
) LANGUAGE sql STABLE AS $fn$
    WITH r AS (SELECT * FROM sim.simulate_closure(p_closed)),
    base AS (
        SELECT nearest_facility_id fid, COALESCE(sum(births),0) b
        FROM analytics.county_baseline GROUP BY 1
    ),
    moved AS (
        SELECT r.scenario_facility_id fid, count(*) n, COALESCE(sum(r.births),0) b
        FROM r WHERE r.scenario_facility_id <> r.baseline_facility_id GROUP BY 1
    )
    SELECT f.facility_id, f.name, f.city, f.maternal_level::text,
           m.n::int, m.b,
           COALESCE(base.b,0),
           round(100.0*m.b/NULLIF(base.b,0),1)
    FROM moved m
    JOIN geo.facilities f ON f.facility_id = m.fid
    LEFT JOIN base ON base.fid = f.facility_id
    ORDER BY m.b DESC;
$fn$;
