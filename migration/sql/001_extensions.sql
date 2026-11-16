-- 001_extensions.sql — run once per Tiger Cloud service.
-- timescaledb is preinstalled on Tiger Cloud; postgis and vector need enabling.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

SELECT extname, extversion FROM pg_extension
WHERE extname IN ('timescaledb','postgis','vector') ORDER BY extname;
