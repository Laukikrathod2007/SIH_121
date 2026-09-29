# NWIS Database Setup Guide

## Prerequisites

### 1. Install PostgreSQL 15+
**Windows:**
```powershell
# Download PostgreSQL installer from https://www.postgresql.org/download/windows/
# Or use Chocolatey:
choco install postgresql15

# Or use Scoop:
scoop install postgresql
```

**Verify Installation:**
```powershell
psql --version
# Should output: psql (PostgreSQL) 15.x
```

### 2. Install PostGIS Extension
**Windows:**
- PostGIS is typically included in PostgreSQL Windows installer
- During installation, select "PostGIS Bundle" option

**Verify PostGIS:**
```powershell
# Connect to postgres database
psql -U postgres

# Check if PostGIS is available
SELECT * FROM pg_available_extensions WHERE name = 'postgis';
```

### 3. Configure PostgreSQL

**Edit postgresql.conf** (location: C:\Program Files\PostgreSQL\15\data\postgresql.conf)
```ini
# Increase shared memory for better performance
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 64MB
maintenance_work_mem = 256MB

# Enable parallel query execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Set timezone
timezone = 'UTC'
```

**Restart PostgreSQL:**
```powershell
# As Administrator
Restart-Service postgresql-x64-15
```

---

## Database Setup

### Step 1: Create Database

```powershell
# Navigate to schema directory
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database\schema

# Run database creation script
psql -U postgres -f 01_create_database.sql
```

**Expected Output:**
```
CREATE DATABASE
\c
CREATE EXTENSION
CREATE EXTENSION
CREATE EXTENSION
CREATE EXTENSION
CREATE ROLE
GRANT
GRANT
GRANT
SET
 extension_name | version
----------------+----------
 postgis        | 3.3.2
 uuid-ossp      | 1.1
 pg_trgm        | 1.6
 btree_gist     | 1.7
(4 rows)

                        status
------------------------------------------------------
 Database nwis_production created successfully!
(1 row)
```

### Step 2: Create Tables

```powershell
# Connect to nwis_production database and create tables
psql -U postgres -d nwis_production -f 02_create_tables.sql
psql -U postgres -d nwis_production -f 03_create_tables_part2.sql
```

**Expected Output:**
```
CREATE TABLE
...
GRANT
GRANT
               status
---------------------------------------
 All tables created successfully!
(1 row)

 schemaname |        tablename         | size
------------+--------------------------+--------
 public     | alerts                   | 8192 bytes
 public     | daily_drilling_reports   | 8192 bytes
 ...
```

### Step 3: Create Indexes

```powershell
psql -U postgres -d nwis_production -f 04_create_indexes.sql
```

**Expected Output:**
```
CREATE INDEX
...
ANALYZE
                    status
---------------------------------------
 All indexes created successfully!
(1 row)
```

---

## Verify Installation

### Test Database Connection

```powershell
# Connect as nwis_app user
psql -U nwis_app -d nwis_production
```

### Test PostGIS Functionality

```sql
-- Create a test well location
SELECT ST_AsText(ST_SetSRID(ST_MakePoint(95.62, 27.38), 4326));

-- Should output: POINT(95.62 27.38)
```

### Check Table Statistics

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - 
                   pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Initial Data Population

### Insert Sample Wells

```sql
-- Connect to database
psql -U nwis_app -d nwis_production

-- Insert 5 offset wells
INSERT INTO wells (well_name, forge_source_id, location, latitude, longitude, 
                   field_name, well_status, is_offset_well, data_source) 
VALUES 
('NH-001', '56-32', ST_SetSRID(ST_MakePoint(95.33, 27.29), 4326), 
 27.29, 95.33, 'Nahorkatiya', 'completed', TRUE, 'utah_forge'),
('MR-002', '78B-32', ST_SetSRID(ST_MakePoint(95.16, 27.28), 4326), 
 27.28, 95.16, 'Moran', 'completed', TRUE, 'utah_forge'),
('DG-003', '16A(78)-32', ST_SetSRID(ST_MakePoint(95.62, 27.38), 4326), 
 27.38, 95.62, 'Digboi', 'drilling', TRUE, 'utah_forge'),
('BG-004', 'well_3', ST_SetSRID(ST_MakePoint(95.45, 27.30), 4326), 
 27.30, 95.45, 'Baghjan', 'completed', TRUE, 'utah_forge'),
('RD-005', 'well_4', ST_SetSRID(ST_MakePoint(95.28, 27.25), 4326), 
 27.25, 95.28, 'Rudrasagar', 'completed', TRUE, 'utah_forge');

-- Mark active well
UPDATE wells SET is_active_well = TRUE WHERE well_name = 'DG-003';

-- Verify insertion
SELECT well_name, field_name, well_status, 
       ST_AsText(location::geometry) AS location_wkt
FROM wells;
```

### Calculate Offset Well Links

```sql
-- Populate offset_well_links table with distances
INSERT INTO offset_well_links (well_id_a, well_id_b, distance_km)
SELECT 
    w1.well_id,
    w2.well_id,
    ST_Distance(w1.location, w2.location) / 1000 AS distance_km
FROM wells w1
CROSS JOIN wells w2
WHERE w1.well_id < w2.well_id;

-- Verify links
SELECT 
    w1.well_name AS well_a,
    w2.well_name AS well_b,
    ROUND(owl.distance_km::numeric, 2) AS distance_km,
    owl.is_nearby
FROM offset_well_links owl
JOIN wells w1 ON owl.well_id_a = w1.well_id
JOIN wells w2 ON owl.well_id_b = w2.well_id
ORDER BY owl.distance_km;
```

---

## Database Connection Strings

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nwis_production",
    user="nwis_app",
    password="your_password_here"
)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://nwis_app:your_password@localhost:5432/nwis_production'
)
```

### Node.js (pg)
```javascript
const { Pool } = require('pg');

const pool = new Pool({
    host: 'localhost',
    port: 5432,
    database: 'nwis_production',
    user: 'nwis_app',
    password: 'your_password_here'
});
```

### Environment Variables (.env file)
```env
DATABASE_URL=postgresql://nwis_app:your_password@localhost:5432/nwis_production
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nwis_production
DB_USER=nwis_app
DB_PASSWORD=your_password_here
```

---

## Backup and Restore

### Create Backup

```powershell
# Full database backup
pg_dump -U postgres -d nwis_production -F c -f nwis_backup_$(Get-Date -Format 'yyyyMMdd').backup

# Schema only backup
pg_dump -U postgres -d nwis_production --schema-only -f nwis_schema.sql

# Data only backup
pg_dump -U postgres -d nwis_production --data-only -f nwis_data.sql
```

### Restore from Backup

```powershell
# Restore full backup
pg_restore -U postgres -d nwis_production -c nwis_backup_20241215.backup

# Restore from SQL file
psql -U postgres -d nwis_production -f nwis_schema.sql
```

---

## Performance Tuning

### Enable Query Logging

**Edit postgresql.conf:**
```ini
log_statement = 'all'
log_duration = on
log_min_duration_statement = 1000  # Log queries slower than 1 second
```

### Monitor Slow Queries

```sql
-- Install pg_stat_statements extension
CREATE EXTENSION pg_stat_statements;

-- View slowest queries
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Vacuum and Analyze

```sql
-- Manual vacuum
VACUUM ANALYZE wells;
VACUUM ANALYZE drilling_telemetry;

-- Configure autovacuum in postgresql.conf
autovacuum = on
autovacuum_naptime = 1min
autovacuum_vacuum_scale_factor = 0.05
```

---

## Security Best Practices

### Change Default Password

```sql
-- Connect as postgres
psql -U postgres

-- Change nwis_app password
ALTER ROLE nwis_app WITH PASSWORD 'strong_random_password_here';
```

### Enable SSL Connection

**Edit postgresql.conf:**
```ini
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

### Restrict Network Access

**Edit pg_hba.conf:**
```
# Allow local connections only
host    nwis_production    nwis_app    127.0.0.1/32    md5
host    nwis_production    nwis_app    ::1/128         md5
```

---

## Troubleshooting

### Issue: Cannot connect to PostgreSQL

**Solution:**
```powershell
# Check if PostgreSQL service is running
Get-Service postgresql-x64-15

# Start service if stopped
Start-Service postgresql-x64-15

# Check port 5432 is listening
netstat -an | findstr "5432"
```

### Issue: PostGIS extension not found

**Solution:**
```powershell
# Reinstall PostgreSQL with PostGIS bundle
# Or install PostGIS separately from https://postgis.net/windows_downloads/
```

### Issue: Out of memory errors

**Solution: Increase PostgreSQL memory limits in postgresql.conf**
```ini
shared_buffers = 512MB
work_mem = 128MB
maintenance_work_mem = 512MB
```

---

## Next Steps

1. ✅ Database setup complete
2. ⏳ Build ETL pipeline for CSV data ingestion (Module 2)
3. ⏳ Integrate OCR extraction with documents table
4. ⏳ Build FastAPI backend with database queries
5. ⏳ Create visualization dashboard (Module 3)

---

## Useful Commands

```sql
-- List all tables
\dt

-- Describe table structure
\d wells

-- List all indexes
\di

-- Show table size
\dt+ wells

-- List all databases
\l

-- Switch database
\c nwis_production

-- Quit psql
\q
```

---

**Database setup is now complete!** 🎉

Ready to start populating with real data.
