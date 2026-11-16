-- 002_schema.sql — core tables for the data we actually hold today.
--
-- NOTE ON HYPERTABLES: county_births is 159 counties x 10 years = 1,590 rows.
-- That is a plain table. Hypertables earn their keep on high-volume append
-- workloads (scenario runs, audit logs), not on a decade of county totals.
-- Converting this would add chunk overhead for no gain. The hypertables in the
-- spec (sim.scenario_event, sim.county_result, audit.ai_interaction) still
-- apply -- they arrive with the simulation engine, not with this load.

-- Schemas live here, not in 001: they are schema, not extensions, and this
-- file must be runnable on a plain Postgres for testing without PostGIS.
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS health;
CREATE SCHEMA IF NOT EXISTS sim;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ── Counties ────────────────────────────────────────────────────────────────
-- centroid_* are NULLABLE on purpose: we do not have coordinates yet. They are
-- required before any travel-time work (see 004_travel_matrix.sql).
CREATE TABLE IF NOT EXISTS geo.counties (
    geoid          CHAR(5)      PRIMARY KEY,
    name           TEXT         NOT NULL,
    centroid_lat   NUMERIC(9,6),
    centroid_lon   NUMERIC(9,6),
    centroid       geography(Point, 4326)
                   GENERATED ALWAYS AS (
                       CASE WHEN centroid_lat IS NOT NULL AND centroid_lon IS NOT NULL
                            THEN ST_SetSRID(ST_MakePoint(centroid_lon::float8,
                                                         centroid_lat::float8), 4326)::geography
                       END
                   ) STORED,
    is_rural       BOOLEAN,
    source_citation TEXT NOT NULL DEFAULT
        'GDPH OASIS, Number of Births by Residence, retrieved 2026-09-18',
    CONSTRAINT counties_geoid_is_ga CHECK (geoid LIKE '13%')
);
CREATE INDEX IF NOT EXISTS idx_counties_centroid ON geo.counties USING GIST (centroid);

-- ── Births, 2015-2024 (GDPH OASIS) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS health.county_births (
    geoid   CHAR(5)  NOT NULL REFERENCES geo.counties(geoid),
    year    SMALLINT NOT NULL CHECK (year BETWEEN 1990 AND 2100),
    births  INTEGER  CHECK (births >= 0),   -- NULL = suppressed small cell
    PRIMARY KEY (geoid, year)
);
CREATE INDEX IF NOT EXISTS idx_births_year ON health.county_births (year);

-- ── March of Dimes access tiers (2026) ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS health.mod_access_tiers (
    geoid       CHAR(5) PRIMARY KEY REFERENCES geo.counties(geoid),
    tier        TEXT    NOT NULL CHECK (tier IN ('full','moderate','low','desert')),
    tier_label  TEXT    NOT NULL,            -- verbatim MoD wording, for display
    is_desert   BOOLEAN NOT NULL,
    vintage     DATE    NOT NULL DEFAULT DATE '2026-01-01',
    source_citation TEXT NOT NULL DEFAULT 'March of Dimes, Maternity Care Desert report, 2026'
);

-- ── Facilities — SCHEMA ONLY, NO DATA YET ───────────────────────────────────
-- This is the blocking gap. Without facility coordinates there is no travel
-- matrix, no closure simulation, and no absorption analysis.
DO $$ BEGIN
    CREATE TYPE geo.maternal_level AS ENUM ('I','II','III','IV');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TYPE geo.facility_status AS ENUM ('active','closed','planned','suspended');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS geo.facilities (
    facility_id        TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    city               TEXT,
    state_code         CHAR(2) NOT NULL,
    is_border_facility BOOLEAN NOT NULL DEFAULT FALSE,
    -- NULLABLE: border rows recovered from the blueprint have no coordinates
    -- yet. The travel-matrix guard in 004 refuses to run while any ACTIVE
    -- facility lacks them, so a partial roster cannot silently skew the model.
    lat                NUMERIC(9,6),
    lon                NUMERIC(9,6),
    location           geography(Point, 4326)
                       GENERATED ALWAYS AS (
                           CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
                                THEN ST_SetSRID(ST_MakePoint(lon::float8, lat::float8), 4326)::geography
                           END
                       ) STORED,
    maternal_level     geo.maternal_level,
    level_is_designated BOOLEAN NOT NULL DEFAULT FALSE,
    status             geo.facility_status NOT NULL DEFAULT 'active',
    status_asserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_citation    TEXT NOT NULL,
    CONSTRAINT facilities_coords_paired CHECK ((lat IS NULL) = (lon IS NULL)),
    CONSTRAINT facilities_lat_range CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
    CONSTRAINT facilities_lon_range CHECK (lon IS NULL OR lon BETWEEN -180 AND 180)
);
CREATE INDEX IF NOT EXISTS idx_facilities_location ON geo.facilities USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_facilities_active   ON geo.facilities (status) WHERE status = 'active';
