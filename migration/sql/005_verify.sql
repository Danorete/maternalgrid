-- 005_verify.sql — data quality gate. Run after every load.
-- Each row returns PASS or FAIL; a FAIL means do not build on this load.

\echo '=== MaternalGrid load verification ==='

WITH checks AS (
  SELECT 'counties = 159'                AS check_name,
         (SELECT count(*) FROM geo.counties)::text AS actual, '159' AS expected
  UNION ALL SELECT 'all counties are Georgia (13xxx)',
         (SELECT count(*) FROM geo.counties WHERE geoid LIKE '13%')::text, '159'
  UNION ALL SELECT 'birth rows = 159 x 10 years',
         (SELECT count(*) FROM health.county_births)::text, '1590'
  UNION ALL SELECT 'distinct birth years',
         (SELECT count(DISTINCT year) FROM health.county_births)::text, '10'
  UNION ALL SELECT 'statewide births 2024 (GDPH OASIS)',
         (SELECT sum(births)::text FROM health.county_births WHERE year = 2024), '126304'
  UNION ALL SELECT 'statewide births 2015',
         (SELECT sum(births)::text FROM health.county_births WHERE year = 2015), '131333'
  UNION ALL SELECT 'MoD tier rows = 159',
         (SELECT count(*) FROM health.mod_access_tiers)::text, '159'
  UNION ALL SELECT 'MoD maternity care deserts',
         (SELECT count(*) FROM health.mod_access_tiers WHERE is_desert)::text, '70'
  UNION ALL SELECT 'counties missing a MoD tier',
         (SELECT count(*) FROM geo.counties c
           LEFT JOIN health.mod_access_tiers m USING (geoid) WHERE m.geoid IS NULL)::text, '0'
  UNION ALL SELECT 'counties missing any birth year',
         (SELECT count(*) FROM (
            SELECT geoid FROM health.county_births
            GROUP BY geoid HAVING count(*) <> 10) x)::text, '0'
  UNION ALL SELECT 'negative or impossible birth counts',
         (SELECT count(*) FROM health.county_births WHERE births < 0)::text, '0'
  UNION ALL SELECT 'in-state facilities',
         (SELECT count(*) FROM geo.facilities WHERE NOT is_border_facility)::text, '66'
  UNION ALL SELECT 'in-state ACTIVE delivering hospitals',
         (SELECT count(*) FROM geo.facilities WHERE NOT is_border_facility AND status='active')::text, '62'
  UNION ALL SELECT 'in-state closed units',
         (SELECT count(*) FROM geo.facilities WHERE NOT is_border_facility AND status='closed')::text, '4'
  UNION ALL SELECT 'Level IV facilities',
         (SELECT count(*) FROM geo.facilities WHERE maternal_level='IV' AND NOT is_border_facility)::text, '7'
  UNION ALL SELECT 'total ACTIVE delivering facilities (62 in-state + 6 border)',
         (SELECT count(*) FROM geo.facilities WHERE status='active')::text, '68'
  UNION ALL SELECT 'counties WITH centroid coordinates',
         (SELECT count(*) FROM geo.counties WHERE centroid_lat IS NOT NULL)::text, '159'
  UNION ALL SELECT 'ACTIVE facilities missing coordinates',
         (SELECT count(*) FROM geo.facilities WHERE status='active' AND lat IS NULL)::text, '0'
)
SELECT check_name,
       expected,
       actual,
       CASE WHEN actual IS NOT DISTINCT FROM expected THEN 'PASS' ELSE 'FAIL' END AS result
FROM checks;

\echo ''
\echo '=== Known gaps (expected to be non-zero until the missing data arrives) ==='
SELECT 'counties WITHOUT centroid coordinates' AS gap,
       count(*) FILTER (WHERE centroid_lat IS NULL) AS n,
       count(*)                                     AS of_total
FROM geo.counties
UNION ALL
SELECT 'active facilities WITHOUT coordinates', count(*) FILTER (WHERE status='active' AND lat IS NULL),
       count(*) FILTER (WHERE status='active') FROM geo.facilities;

\echo ''
\echo '=== Baseline metrics (these are the numbers the demo should quote) ==='
SELECT
  (SELECT count(*) FROM health.mod_access_tiers WHERE is_desert)                       AS desert_counties,
  round(100.0 * (SELECT count(*) FROM health.mod_access_tiers WHERE is_desert)
        / (SELECT count(*) FROM health.mod_access_tiers), 1)                           AS pct_desert,
  (SELECT sum(b.births) FROM health.county_births b
     JOIN health.mod_access_tiers m USING (geoid)
    WHERE b.year = 2024 AND m.is_desert)                                               AS births_2024_in_deserts,
  (SELECT sum(births) FROM health.county_births WHERE year = 2024)                     AS births_2024_total;
