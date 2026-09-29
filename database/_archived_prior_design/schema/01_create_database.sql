-- ============================================================================
-- NWIS Database Creation Script
-- Database: nwis_production
-- Version: 1.0
-- PostgreSQL 15+ with PostGIS Extension
-- ============================================================================

-- Create database (run as postgres superuser)
CREATE DATABASE nwis_production
    WITH 
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- Connect to the new database
\c nwis_production

-- Create extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS btree_gist; -- For multi-column GIST indexes

-- Optional but recommended for time-series optimization
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create application user
CREATE USER nwis_app WITH PASSWORD 'change_this_password_in_production';

-- Grant privileges
GRANT CONNECT ON DATABASE nwis_production TO nwis_app;
GRANT USAGE ON SCHEMA public TO nwis_app;
GRANT CREATE ON SCHEMA public TO nwis_app;

-- Enable row-level security (optional, for multi-tenant scenarios)
-- ALTER DATABASE nwis_production SET row_security = on;

-- Set timezone
SET timezone = 'UTC';

-- Confirm extensions
SELECT 
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname IN ('postgis', 'uuid-ossp', 'pg_trgm', 'btree_gist', 'timescaledb');

-- Database ready for schema creation
SELECT 'Database nwis_production created successfully!' AS status;
