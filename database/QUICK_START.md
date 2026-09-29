# NWIS Database - Quick Start Guide

## ⚡ Fast Setup (5 minutes)

### Step 1: Configure Database Password

**Create .env file with your PostgreSQL password:**

```bash
# Copy the example file
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database
copy .env.example .env

# Edit .env and update DB_PASSWORD
notepad .env
```

Your `.env` file should look like:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nwis_db
DB_USER=postgres
DB_PASSWORD=your_actual_password_here  ← Change this!
```

**✅ Advantages of .env:**
- ✓ Keeps passwords out of code
- ✓ Never committed to git (.gitignore)
- ✓ Easy to change per environment
- ✓ Standard industry practice

**Or use the helper script (recommended for first-time setup):**

```bash
python setup_env.py
```

This interactive script will:
- Prompt for your PostgreSQL credentials
- Hide password input for security
- Create the .env file automatically
- Validate your configuration

### Step 2: Run Setup Script

```bash
cd c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\database\scripts
python master_load.py
```

This single command will:
- ✓ Create the database
- ✓ Initialize all tables
- ✓ Load CSV telemetry data (~30,000+ records)
- ✓ Extract PDF daily reports
- ✓ Calculate KPIs
- ✓ Verify data quality

### Step 3: Verify Installation

```bash
python verify_data.py
```

## 📊 What Gets Loaded

| Data Source | Records | Description |
|-------------|---------|-------------|
| CSV Telemetry | 30,000+ | Time-series drilling data (10s intervals) |
| Daily Reports | 30+ | Daily drilling operation summaries |
| Well Records | 5 | Master well information |
| KPI Metrics | 100+ | Calculated performance indicators |

## 🔍 Quick Verification Queries

Connect to database:
```bash
psql -U postgres -d nwis_db
```

Check data:
```sql
-- View all wells
SELECT * FROM wells;

-- Latest telemetry
SELECT * FROM v_latest_telemetry;

-- Daily NPT summary
SELECT * FROM v_daily_npt_summary;

-- Well performance overview
SELECT * FROM v_well_performance;
```

## ❗ Troubleshooting

### Issue: Connection Failed
```
Error: password authentication failed
```
**Fix:** Update password in `config/db_config.py`

### Issue: Database Doesn't Exist
```
Error: database "nwis_db" does not exist
```
**Fix:** The script creates it automatically. If it fails:
```sql
CREATE DATABASE nwis_db;
```

### Issue: CSV File Not Found
```
FileNotFoundError: CSV file not found
```
**Fix:** Ensure this file exists:
```
c:\Users\harsh_cuhj7z7\OneDrive\Documents\HACKATHON\NWIS\data\raw\16A(78)-32_time_data_10s_intervals_standard.csv
```

## ✅ Success Indicators

After running `master_load.py`, you should see:

```
==================================================================
  ✓ Database setup and data loading complete!
==================================================================

Total Records in Database: 30,000+

🚀 Next Steps:
  1. Verify data: python verify_data.py
  2. Start backend API server
  3. Start frontend dashboard
```

## 📁 Database Schema

### Core Tables
- **wells** - Master well registry
- **telemetry_data** - Time-series sensor data
- **daily_operations** - Daily drilling reports  
- **equipment** - Equipment tracking
- **npt_events** - Non-productive time events
- **kpi_metrics** - Performance metrics

### Views
- **v_latest_telemetry** - Latest readings per well
- **v_daily_npt_summary** - NPT aggregation
- **v_well_performance** - Well performance KPIs

## 🚀 Next Module: Backend API

Once database is loaded, proceed to backend:

```bash
cd ../backend
# Backend setup instructions
```

## 📞 Need Help?

Check the detailed setup guide:
```
database/SETUP_INSTRUCTIONS.md
```
