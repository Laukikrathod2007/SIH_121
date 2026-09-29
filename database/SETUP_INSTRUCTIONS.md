# NWIS Database Setup Instructions

## Prerequisites
- PostgreSQL 14+ installed and running
- Python 3.9+ installed
- CSV and PDF data files in `/data/raw/` directory

## Step-by-Step Setup

### 1. Install Python Dependencies
```bash
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database
pip install -r requirements.txt
```

### 2. Configure Database Connection

**Create .env file with your credentials:**

```bash
# Copy the example file
copy .env.example .env
```

**Edit the .env file and set your PostgreSQL password:**

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nwis_db
DB_USER=postgres
DB_PASSWORD=your_actual_password_here  ← Update this!
```

**Important:** 
- The .env file is in .gitignore and won't be committed
- Never hardcode passwords in source code
- Each environment (dev, staging, prod) can have its own .env

### 3. Create Database (First Time Only)

Open PostgreSQL command line or pgAdmin and run:

```sql
CREATE DATABASE nwis_db;
```

Or use Python:
```python
from config.db_config import DatabaseConnection, DatabaseConfig

config = DatabaseConfig(
    host="localhost",
    database="postgres",  # Connect to default database first
    user="postgres",
    password="YOUR_PASSWORD"
)

db = DatabaseConnection(config)
db.create_database("nwis_db")
```

### 4. Run Complete Setup (Recommended)

Run the master loading script that handles everything:

```bash
cd scripts
python master_load.py
```

This will:
1. Create all database tables
2. Create sample well records
3. Load CSV telemetry data
4. Extract and load PDF reports
5. Calculate initial KPIs
6. Generate summary report

### 5. Manual Setup (Alternative)

If you prefer manual control:

#### 5.1 Create Tables
```bash
python -c "from config.db_config import get_db; db = get_db(); db.execute_script_file('../schema/create_tables.sql')"
```

#### 5.2 Load Telemetry Data
```bash
python load_csv_telemetry.py
```

#### 5.3 Load PDF Reports
```bash
python load_pdf_reports.py
```

## Verification

### Check Table Counts
```python
from config.db_config import get_db

db = get_db()
print(f"Wells: {db.get_table_count('wells')}")
print(f"Telemetry: {db.get_table_count('telemetry_data')}")
print(f"Daily Operations: {db.get_table_count('daily_operations')}")
print(f"KPIs: {db.get_table_count('kpi_metrics')}")
```

### Query Sample Data
```sql
-- Connect to database
psql -U postgres -d nwis_db

-- Check wells
SELECT * FROM wells;

-- Check recent telemetry
SELECT 
    timestamp, 
    bit_depth, 
    rate_of_penetration, 
    weight_on_bit 
FROM telemetry_data 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check daily operations
SELECT * FROM daily_operations ORDER BY report_date DESC;

-- Check KPIs
SELECT * FROM kpi_metrics ORDER BY calculation_date DESC;

-- Check views
SELECT * FROM v_well_performance;
SELECT * FROM v_latest_telemetry;
```

## Database Schema Overview

### Core Tables
1. **wells** - Master well information
2. **telemetry_data** - Time-series sensor data (10-second intervals)
3. **daily_operations** - Daily drilling reports
4. **equipment** - Equipment inventory and performance
5. **npt_events** - Non-Productive Time events
6. **kpi_metrics** - Calculated performance metrics

### Views
- **v_latest_telemetry** - Latest telemetry per well
- **v_daily_npt_summary** - Daily NPT summary
- **v_well_performance** - Overall well performance

## Troubleshooting

### Connection Issues
```
Error: could not connect to server
```
**Solution:** Ensure PostgreSQL is running
```bash
# Windows
net start postgresql-x64-14

# Check status
pg_isready
```

### Permission Errors
```
Error: permission denied for table
```
**Solution:** Grant proper permissions
```sql
GRANT ALL PRIVILEGES ON DATABASE nwis_db TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
```

### CSV Loading Issues
```
Error: CSV file not found
```
**Solution:** Check file path in `load_csv_telemetry.py` line 217

### Memory Issues
```
Error: MemoryError or system runs out of memory
```
**Solution:** Reduce chunk_size in loaders
- In `load_csv_telemetry.py`: Change `chunk_size=5000` to `chunk_size=1000`
- In `master_load.py`: Same adjustment

## Data Files Required

```
data/
├── raw/
│   ├── 16A(78)-32_time_data_10s_intervals_standard.csv  ✓ Required
│   └── well_1/
│       └── 56-32 Daily Drilling Reports/
│           ├── DailyReportDetailRpt_210205202148.pdf
│           ├── DailyReportDetailRpt_210206193435.pdf
│           └── ... (30+ PDF files)
```

## Next Steps

After successful database setup:

1. **Verify Data Quality**
   ```bash
   python scripts/verify_data.py
   ```

2. **Start Backend API**
   ```bash
   cd ../backend
   python app.py
   ```

3. **Test API Endpoints**
   - http://localhost:5000/api/wells
   - http://localhost:5000/api/telemetry/latest
   - http://localhost:5000/api/kpis

4. **Launch Frontend Dashboard**
   ```bash
   cd ../frontend
   npm start
   ```

## Support

For issues or questions:
- Check logs in console output
- Review database logs: `pg_log` directory
- Verify Python dependencies: `pip list`
