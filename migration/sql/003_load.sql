-- 003_load.sql — run with psql from the bundle root:
--     psql "$TIGER_URL" -f sql/003_load.sql
-- \copy is client-side, so paths resolve relative to your shell, not the server.

\copy geo.counties (geoid, name, centroid_lat, centroid_lon) FROM 'data/counties.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy health.county_births (geoid, year, births) FROM 'data/county_births.csv' WITH (FORMAT csv, HEADER true, NULL '')
\copy health.mod_access_tiers (geoid, tier, tier_label, is_desert) FROM 'data/mod_access_tiers.csv' WITH (FORMAT csv, HEADER true, NULL '')

-- facilities.csv is produced by etl/ingest_facilities.py from georgia_facilities.json
\copy geo.facilities (facility_id, name, city, state_code, is_border_facility, maternal_level, level_is_designated, status, lat, lon, source_citation) FROM 'data/facilities.csv' WITH (FORMAT csv, HEADER true, NULL '')

ANALYZE geo.counties;
ANALYZE geo.facilities;
ANALYZE health.county_births;
ANALYZE health.mod_access_tiers;
