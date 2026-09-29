# NWIS Database Quick Start Guide

## 🎯 Simple 3-Step Process

This guide will take you from **nothing** to a **fully working database with data** in 30 minutes.

---

## Step 1: Install PostgreSQL (15 minutes)

### Download and Install

1. **Go to:** https://www.postgresql.org/download/windows/
2. **Download:** PostgreSQL 15.x Windows installer (latest version)
3. **Run installer** and follow these settings:

```
Installation Directory: C:\Program Files\PostgreSQL\15  ✅
Components to Install:
  ✅ PostgreSQL Server
  ✅ pgAdmin 4 (graphical tool)
  ✅ Command Line Tools
  ✅ Stack Builder (select PostGIS during this)
  
Port: 5432  ✅
Password for 'postgres' user: [CHOOSE A STRONG PASSWORD] 🔐
  ⚠️ REMEMBER THIS PASSWORD!
```

4. **After main installation:** Stack Builder will open
   - Select your PostgreSQL installation
   - Under "Spatial Extensions" → Select **PostGIS**
   - Click Next and install

5. **Verify installation:**
```powershell
# Open PowerShell
psql --version
# Should show: psql (PostgreSQL) 15.x
```

---

## Step 2: Create Database (5 minutes)

### Option A: Automatic (Run SQL Scripts)

```powershell
# 1. Open PowerShell
# 2. Navigate to schema folder
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database\schema

# 3. Run scripts in order (enter postgres password when asked)
psql -U postgres -f 01_create_database.sql
psql -U postgres -d nwis_production -f 02_create_tables.sql
psql -U postgres -d nwis_production -f 03_create_tables_part2.sql
psql -U postgres -d nwis_production -f 04_create_indexes.sql
```

**Expected output:** "All tables created successfully!"

### Option B: Using pgAdmin (Graphical)

1. **Open pgAdmin 4** (installed with PostgreSQL)
2. **Connect to server:**
   - Servers → PostgreSQL 15 → Enter postgres password
3. **Right-click "Databases"** → Create → Database
   - Database: `nwis_production`
   - Owner: postgres
   - Save
4. **Open Query Tool:**
   - Right-click `nwis_production` → Query Tool
5. **Copy-paste each SQL file content** (01, 02, 03, 04) and execute

---

## Step 3: Add Data (10 minutes)

### Part A: Add 5 Sample Wells (Manual - 2 minutes)

```powershell
# Navigate to scripts folder
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database\scripts

# Run sample data script
# Password is now 'your_password_here' - you should change it!
psql -U nwis_app -d nwis_production -f populate_sample_wells.sql
```

**What this does:**
- Inserts 5 wells (NH-001, MR-002, DG-003, BG-004, RD-005)
- Calculates distances between wells
- Adds sample formation layers
- DG-003 is marked as "active well" for live monitoring

### Part B: Load CSV Telemetry Data (Automatic - 5-8 minutes)

**Before running, update the password:**

1. **Edit `load_csv_telemetry.py`:**
```python
# Line 13-14: Change password
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'nwis_production',
    'user': 'nwis_app',
    'password': 'your_actual_password_here'  # ← CHANGE THIS!
}
```

2. **Install Python dependencies:**
```powershell
pip install pandas psycopg2-binary
```

3. **Run the loader:**
```powershell
python load_csv_telemetry.py
```

**What this does:**
- Reads `16A(78)-32_time_data_10s_intervals_standard.csv`
- Converts units (feet→meters, psi→kPa, °F→°C)
- Inserts telemetry data into `drilling_telemetry` table
- Shows progress every 1,000 rows

**Expected output:**
```
🚀 NWIS CSV Telemetry Loader
✅ Loaded 123,456 rows
✅ Connected to nwis_production
✅ Found active well: DG-003
📊 Processing rows...
  ✓ Inserted 1,000 rows...
  ✓ Inserted 2,000 rows...
  ...
✅ Successfully inserted 123,456 telemetry rows!
```

---

## ✅ Verification: Test Your Database

### Test 1: Check Wells

```powershell
# Connect to database
psql -U nwis_app -d nwis_production

# Run test query
SELECT well_name, field_name, well_status 
FROM wells 
ORDER BY well_name;
```

**Expected output:**
```
 well_name | field_name  | well_status
-----------+-------------+-------------
 BG-004    | Baghjan     | completed
 DG-003    | Digboi      | drilling
 MR-002    | Moran       | completed
 NH-001    | Nahorkatiya | completed
 RD-005    | Rudrasagar  | completed
```

### Test 2: Check Telemetry Data

```sql
SELECT COUNT(*) FROM drilling_telemetry;
-- Should show: count = 123,456 (or similar)

SELECT 
    timestamp, 
    bit_depth_md, 
    wob_klbs, 
    rop_m_hr 
FROM drilling_telemetry 
ORDER BY timestamp DESC 
LIMIT 5;
```

### Test 3: Check Nearby Wells

```sql
SELECT 
    w1.well_name AS from_well,
    w2.well_name AS to_well,
    owl.distance_km,
    owl.is_nearby
FROM offset_well_links owl
JOIN wells w1 ON owl.well_id_a = w1.well_id
JOIN wells w2 ON owl.well_id_b = w2.well_id
WHERE w1.well_name = 'DG-003'
ORDER BY owl.distance_km;
```

### Test 4: Check Formation Layers

```sql
SELECT 
    w.well_name,
    ft.formation_name,
    ft.top_depth_md,
    ft.bottom_depth_md
FROM formation_tops ft
JOIN wells w ON ft.well_id = w.well_id
ORDER BY w.well_name, ft.top_depth_md;
```

---

## 🎨 Visualize Your Data (Optional - Using pgAdmin)

1. **Open pgAdmin**
2. **Navigate to:** Servers → PostgreSQL 15 → Databases → nwis_production → Schemas → public → Tables
3. **Right-click any table** (e.g., `wells`) → View/Edit Data → All Rows
4. **For map view:**
   - Right-click `wells` table → View/Edit Data → First 100 Rows
   - You'll see all well locations with coordinates

---

## 📊 What Each Table Contains Now

| Table | Status | Row Count | Description |
|-------|--------|-----------|-------------|
| `wells` | ✅ Has data | 5 | Well master records |
| `drilling_telemetry` | ✅ Has data | ~123,456 | Real-time drilling data |
| `formation_tops` | ✅ Has data | 8 | Geological layers (2 wells) |
| `offset_well_links` | ✅ Has data | 10 | Well proximity relationships |
| `documents` | ⏳ Empty | 0 | Will be filled by OCR system |
| `daily_drilling_reports` | ⏳ Empty | 0 | Will be filled by OCR extraction |
| `well_completion_reports` | ⏳ Empty | 0 | Will be filled by OCR extraction |
| `incidents` | ⏳ Empty | 0 | Will be filled manually or OCR |
| `alerts` | ⏳ Empty | 0 | Will be generated by Module 2 |
| `predictions` | ⏳ Empty | 0 | Will be filled by Module 4 (ML) |
| `directional_surveys` | ⏳ Empty | 0 | Will be calculated from telemetry |
| `user_annotations` | ⏳ Empty | 0 | For ML training (manual labels) |
| `system_logs` | ⏳ Empty | 0 | Will be filled by application |

---

## 🔧 Troubleshooting

### Issue: "psql: command not found"

**Solution:** Add PostgreSQL to PATH
```powershell
# Add to environment variables:
C:\Program Files\PostgreSQL\15\bin
```
Or use full path:
```powershell
"C:\Program Files\PostgreSQL\15\bin\psql" -U postgres
```

### Issue: "password authentication failed"

**Solution:** 
1. Check password is correct
2. Edit `pg_hba.conf` file:
   - Location: `C:\Program Files\PostgreSQL\15\data\pg_hba.conf`
   - Change `md5` to `trust` for local connections (for testing only!)
   - Restart PostgreSQL service

### Issue: "PostGIS extension not found"

**Solution:** Install PostGIS via Stack Builder
1. Run Stack Builder (Start Menu → PostgreSQL 15 → Stack Builder)
2. Select PostgreSQL 15
3. Under "Spatial Extensions" → Install PostGIS
4. Restart PostgreSQL

### Issue: Python script fails

**Solution:** Install dependencies
```powershell
pip install pandas psycopg2-binary
```

If `psycopg2` fails, try:
```powershell
pip install psycopg2-binary --no-binary :all:
```

---

## 🔐 Security: Change Default Password

```sql
-- Connect as postgres
psql -U postgres

-- Change nwis_app password
ALTER ROLE nwis_app WITH PASSWORD 'new_strong_password_here';
```

Then update `load_csv_telemetry.py` with new password.

---

## 📚 Next Steps

### You Now Have:
✅ PostgreSQL database installed  
✅ NWIS database created with 13 tables  
✅ 5 sample wells with locations  
✅ ~123,000 telemetry records (10-second intervals)  
✅ Formation tops for 2 wells  
✅ Offset well relationships calculated  

### What's Next:
⏳ **Module 2:** Build FastAPI backend to query this data  
⏳ **Module 3:** Build Cesium.js dashboard to visualize  
⏳ **Module 4:** Train ML models using telemetry data  
⏳ **OCR Integration:** Extract DDR/WCR documents  

---

## 🔌 Connect from Your Application

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="nwis_production",
    user="nwis_app",
    password="your_password"
)

cursor = conn.cursor()
cursor.execute("SELECT * FROM wells")
wells = cursor.fetchall()
print(wells)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://nwis_app:your_password@localhost:5432/nwis_production'
)

import pandas as pd
df = pd.read_sql("SELECT * FROM drilling_telemetry LIMIT 1000", engine)
print(df.head())
```

### JavaScript/Node.js
```javascript
const { Pool } = require('pg');

const pool = new Pool({
    host: 'localhost',
    port: 5432,
    database: 'nwis_production',
    user: 'nwis_app',
    password: 'your_password'
});

pool.query('SELECT * FROM wells', (err, res) => {
    console.log(res.rows);
});
```

---

## 💡 Useful Commands

```sql
-- List all tables
\dt

-- Describe table structure
\d wells

-- Count rows in all tables
SELECT 
    schemaname,
    tablename,
    n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Check database size
SELECT pg_size_pretty(pg_database_size('nwis_production'));

-- Exit psql
\q
```

---

## ✅ Checklist

- [ ] PostgreSQL 15 installed
- [ ] PostGIS extension installed
- [ ] Database `nwis_production` created
- [ ] All 13 tables created
- [ ] 5 sample wells inserted
- [ ] CSV telemetry data loaded
- [ ] Test queries work
- [ ] Password changed from default
- [ ] Connection from Python/Node.js tested

---

**Congratulations! Your NWIS database is now ready! 🎉**

If you have any issues, check:
1. `SETUP_GUIDE.md` for detailed troubleshooting
2. `DATABASE_DESIGN.md` for table reference
3. PostgreSQL logs: `C:\Program Files\PostgreSQL\15\data\log\`
