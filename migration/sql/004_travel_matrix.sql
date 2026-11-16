-- 004_travel_matrix.sql — BLOCKED until two things are loaded:
--   1. geo.counties.centroid_lat / centroid_lon   (Census TIGER, or your prototype)
--   2. geo.facilities                             (68 delivering hospitals + coords)
--
-- Requires PostGIS. The guard below stops the migration with a clear message
-- rather than silently building an empty or partial matrix.

DO $$
DECLARE
    missing_centroids INT;
    facility_count    INT;
    missing_coords    INT;
BEGIN
    SELECT count(*) INTO missing_centroids FROM geo.counties WHERE centroid_lat IS NULL;
    SELECT count(*) INTO facility_count    FROM geo.facilities WHERE status = 'active';

    IF missing_centroids > 0 THEN
        RAISE EXCEPTION
          'Cannot build travel matrix: % of % counties have no centroid coordinates.',
          missing_centroids, (SELECT count(*) FROM geo.counties);
    END IF;

    IF facility_count = 0 THEN
        RAISE EXCEPTION
          'Cannot build travel matrix: geo.facilities is empty. Load the delivering-hospital roster first.';
    END IF;

    SELECT count(*) INTO missing_coords
      FROM geo.facilities WHERE status = 'active' AND lat IS NULL;
    IF missing_coords > 0 THEN
        RAISE EXCEPTION
          'Cannot build travel matrix: % active facilities have no coordinates. Geocode them or mark them inactive.',
          missing_coords;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS analytics.travel_matrix (
    geoid           CHAR(5) NOT NULL REFERENCES geo.counties(geoid),
    facility_id     TEXT    NOT NULL REFERENCES geo.facilities(facility_id),
    distance_miles  NUMERIC(8,3) NOT NULL,
    modeled_minutes NUMERIC(6,2) NOT NULL,
    computed_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (geoid, facility_id)
);
CREATE INDEX IF NOT EXISTS idx_matrix_county_time
    ON analytics.travel_matrix (geoid, modeled_minutes);

-- Model parameters (spec §6.2): road curvature 1.30, rural transit 45 mph.
-- ST_Distance on geography returns metres on the spheroid.
TRUNCATE analytics.travel_matrix;
INSERT INTO analytics.travel_matrix (geoid, facility_id, distance_miles, modeled_minutes)
SELECT c.geoid,
       f.facility_id,
       (ST_Distance(c.centroid, f.location) / 1609.344)::numeric(8,3),
       (((ST_Distance(c.centroid, f.location) / 1609.344) * 1.30 / 45.0) * 60)::numeric(6,2)
FROM geo.counties c
CROSS JOIN geo.facilities f
WHERE f.status = 'active' AND f.location IS NOT NULL;

-- Expect 159 x (active facilities). With 68 active that is 10,812 rows.
SELECT count(*) AS matrix_rows,
       count(DISTINCT geoid) AS counties,
       count(DISTINCT facility_id) AS facilities
FROM analytics.travel_matrix;
