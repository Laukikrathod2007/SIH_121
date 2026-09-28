# NWIS Database Documentation

## Overview

This directory contains the complete database design, schema, and setup scripts for the **Nearby Wells Intelligence System (NWIS)**.

## Directory Structure

```
database/
├── README.md                          # This file
├── DATABASE_DESIGN.md                 # Complete schema documentation (START HERE!)
├── VISUALIZATION_TECH_STACK.md        # 3D visualization technology recommendations
├── SETUP_GUIDE.md                     # Step-by-step setup instructions
├── schema/
│   ├── 01_create_database.sql         # Database and extensions creation
│   ├── 02_create_tables.sql           # Core tables (Part 1)
│   ├── 03_create_tables_part2.sql     # Core tables (Part 2)
│   └── 04_create_indexes.sql          # Indexes and optimization
└── migrations/                        # Future migration scripts
```

## Quick Start

### 1. Review the Design

📖 **Start here:** [DATABASE_DESIGN.md](./DATABASE_DESIGN.md)

This document contains:
- Complete schema description (13 tables)
- Entity Relationship Diagram
- Sample queries for all modules
- Performance optimization guidelines

### 2. Setup Database

📋 **Follow:** [SETUP_GUIDE.md](./SETUP_GUIDE.md)

Execute setup scripts in order:
```powershell
cd schema

# Step 1: Create database
psql -U postgres -f 01_create_database.sql

# Step 2: Create tables (Part 1)
psql -U postgres -d nwis_production -f 02_create_tables.sql

# Step 3: Create tables (Part 2)
psql -U postgres -d nwis_production -f 03_create_tables_part2.sql

# Step 4: Create indexes
psql -U postgres -d nwis_production -f 04_create_indexes.sql
```

### 3. Visualization Technology

🎨 **Read:** [VISUALIZATION_TECH_STACK.md](./VISUALIZATION_TECH_STACK.md)

Recommended stack for Module 2:
- **Cesium.js** - 3D geospatial visualization
- **deck.gl** - Data-driven overlays
- **Leaflet.js** - 2D map view
- **ECharts** - Real-time telemetry charts

## Database Schema Summary

### Core Tables (13 total)

| Table | Purpose | Key Features |
|-------|---------|--------------|
| `wells` | Well master data | PostGIS location, status tracking |
| `drilling_telemetry` | Real-time telemetry (10s intervals) | 48 parameters, time-series optimized |
| `formation_tops` | Geological markers | 3D visualization support |
| `documents` | Document registry | OCR status, full-text search |
| `daily_drilling_reports` | Extracted DDR data | NPT tracking, operations summary |
| `well_completion_reports` | Extracted WCR data | Casing design (JSON), cost analysis |
| `incidents` | NPT events | Root cause, corrective actions |
| `offset_well_links` | Well proximity | Pre-calculated distances |
| `alerts` | Real-time alerts | Severity levels, acknowledgment |
| `predictions` | ML model outputs | Feature importance, outcome tracking |
| `user_annotations` | ML training labels | Expert annotations |
| `directional_surveys` | Well trajectory | 3D coordinates for visualization |
| `system_logs` | Audit trail | Error tracking, debugging |

## Key Features

### 1. Geospatial Capabilities (PostGIS)
- Store well locations as GEOGRAPHY points
- Calculate distances between wells
- Find nearby wells within radius
- Support for 3D well trajectories

### 2. Time-Series Optimization
- 10-second interval telemetry storage
- Efficient indexing for real-time queries
- Optional TimescaleDB for compression
- Continuous aggregates for dashboards

### 3. Document Management
- OCR status tracking
- Full-text search capability
- Hash-based duplicate detection
- Extraction confidence scoring

### 4. Machine Learning Support
- Prediction storage with feature importance
- Human annotation tracking
- Outcome validation for model evaluation
- SHAP values for explainability

### 5. 3D Visualization Ready
- Directional survey data (trajectory)
- Formation tops (layered geology)
- Real-time bit position
- GeoJSON export for web rendering

## Data Flow

```
┌─────────────────┐
│  Raw Documents  │ (DDR, WCR, EOWR PDFs)
│   (data/raw/)   │
└────────┬────────┘
         │
         ▼ OCR Extraction
┌─────────────────┐
│   documents     │ (File registry)
└────────┬────────┘
         │
         ├────────────────────┐
         │                    │
         ▼                    ▼
┌──────────────────┐  ┌────────────────┐
│ daily_drilling_  │  │ well_completion│
│    _reports      │  │   _reports     │
└──────────────────┘  └────────┬───────┘
         │                     │
         ├─────────────────────┤
         │                     │
         ▼                     ▼
┌─────────────────┐   ┌────────────────┐
│   incidents     │   │ formation_tops │
└─────────────────┘   └────────────────┘


┌─────────────────┐
│  CSV Telemetry  │ (16A(78)-32 10s intervals)
│   (data/raw/)   │
└────────┬────────┘
         │
         ▼ ETL Pipeline (Module 2)
┌─────────────────┐
│ drilling_telem  │ (Real-time data)
└────────┬────────┘
         │
         ├────────────────────┐
         │                    │
         ▼                    ▼
┌──────────────────┐  ┌────────────────┐
│     alerts       │  │  predictions   │
└──────────────────┘  └────────────────┘


All Data → Module 3 (Dashboard) → Cesium.js/deck.gl Visualization
```

## Sample Queries

### 1. Find Nearby Wells

```sql
SELECT 
    w2.well_name,
    ST_Distance(w1.location, w2.location) / 1000 AS distance_km,
    w2.field_name,
    w2.well_status
FROM wells w1
CROSS JOIN wells w2
WHERE w1.well_name = 'DG-003'
  AND w1.well_id != w2.well_id
  AND ST_DWithin(w1.location, w2.location, 10000)  -- 10km
ORDER BY distance_km;
```

### 2. Latest Telemetry

```sql
SELECT 
    timestamp,
    bit_depth_md,
    wob_klbs,
    rop_m_hr,
    rig_state
FROM drilling_telemetry
WHERE well_id = (SELECT well_id FROM wells WHERE well_name = 'DG-003')
ORDER BY timestamp DESC
LIMIT 100;
```

### 3. Formation Correlation

```sql
SELECT 
    ft.formation_name,
    w.well_name,
    ft.top_depth_md,
    ST_Distance(w.location, active.location) / 1000 AS distance_km
FROM formation_tops ft
JOIN wells w ON ft.well_id = w.well_id
CROSS JOIN (SELECT location FROM wells WHERE well_name = 'DG-003') active
WHERE ft.formation_name = 'Barail Formation'
  AND ST_DWithin(w.location, active.location, 15000)
ORDER BY distance_km;
```

## Connection Examples

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="nwis_production",
    user="nwis_app",
    password="your_password"
)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://nwis_app:password@localhost:5432/nwis_production'
)
```

### FastAPI Example
```python
from databases import Database

database = Database("postgresql://nwis_app:password@localhost:5432/nwis_production")

@app.on_event("startup")
async def startup():
    await database.connect()

@app.get("/wells")
async def get_wells():
    query = "SELECT * FROM wells WHERE well_status = 'drilling'"
    return await database.fetch_all(query)
```

## Performance Considerations

### Indexes
- All foreign keys are indexed
- Geospatial indexes (GIST) on location columns
- Time-series indexes on timestamp columns
- Full-text search indexes (GIN) on documents

### Query Optimization
- Use `EXPLAIN ANALYZE` to check query plans
- Batch INSERT operations for telemetry data
- Use prepared statements for repeated queries
- Leverage PostGIS spatial indexes

### Monitoring
```sql
-- Check slow queries
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Backup Strategy

### Daily Backup
```powershell
# Automated backup script
pg_dump -U postgres -d nwis_production -F c -f "backup_$(Get-Date -Format 'yyyyMMdd').backup"
```

### Point-in-Time Recovery
Enable WAL archiving in postgresql.conf:
```ini
wal_level = replica
archive_mode = on
archive_command = 'copy "%p" "C:\\backup\\wal\\%f"'
```

## Security Checklist

- [x] Strong password for nwis_app user
- [ ] SSL/TLS encryption enabled
- [ ] Network access restricted (pg_hba.conf)
- [ ] Regular security updates
- [ ] Audit logging enabled
- [ ] Backup encryption

## Troubleshooting

### Common Issues

**Connection Refused:**
```powershell
# Check PostgreSQL service
Get-Service postgresql-x64-15
Start-Service postgresql-x64-15
```

**PostGIS Not Found:**
```sql
-- Check available extensions
SELECT * FROM pg_available_extensions WHERE name = 'postgis';

-- Install if needed
CREATE EXTENSION postgis;
```

**Slow Queries:**
```sql
-- Run ANALYZE
ANALYZE wells;
ANALYZE drilling_telemetry;

-- Check missing indexes
SELECT * FROM pg_stat_user_tables WHERE idx_scan = 0;
```

## Next Steps

1. ✅ Database design complete
2. ⏳ Execute SQL scripts to create database
3. ⏳ Insert sample well data
4. ⏳ Build ETL pipeline for CSV ingestion (Module 2)
5. ⏳ Integrate OCR extraction with documents table
6. ⏳ Build FastAPI backend with database queries
7. ⏳ Create 3D visualization dashboard (Module 3)

## Support & Contact

For questions or issues:
- Review [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) for detailed schema info
- Check [SETUP_GUIDE.md](./SETUP_GUIDE.md) for installation help
- Review [VISUALIZATION_TECH_STACK.md](./VISUALIZATION_TECH_STACK.md) for UI guidance

---

**Database Version:** 1.0  
**Last Updated:** December 2024  
**Status:** ✅ Ready for Implementation
