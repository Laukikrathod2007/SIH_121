# NWIS Database Design Document
**Version:** 1.0  
**Date:** December 2024  
**Database Technology:** PostgreSQL 15+ with PostGIS Extension

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Database Technology Stack](#database-technology-stack)
3. [Data Sources Analysis](#data-sources-analysis)
4. [Database Schema Design](#database-schema-design)
5. [Entity Relationship Diagram](#entity-relationship-diagram)
6. [Indexes and Performance](#indexes-and-performance)
7. [Visualization Support](#visualization-support)
8. [Sample Queries](#sample-queries)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

The NWIS (Nearby Wells Intelligence System) database is designed as a **production-grade, analytics-ready PostgreSQL database** that serves as the central data repository for:

- **Real-time drilling telemetry** (eRTMAC simulation via CSV replay)
- **Historical offset well data** (5 wells from Utah FORGE dataset)
- **Extracted document metadata** (DDR, WCR, EOWR reports)
- **Geospatial well locations** (Assam field coordinates)
- **Predictive analytics outputs** (NPT events, risk scores)

### Key Design Principles

✅ **Time-Series Optimized** - Efficient storage for 10-second interval telemetry  
✅ **Geospatially Indexed** - PostGIS for nearby well queries and map visualization  
✅ **WITSML-Aligned** - Parameter names match eRTMAC tender specifications  
✅ **3D Visualization Ready** - Depth, formation, and trajectory data structured for 3D rendering  
✅ **Extensible Schema** - Easy to add new parameters without breaking changes  
✅ **Audit Trail** - Complete data provenance tracking

---

## Database Technology Stack

### Primary Database
**PostgreSQL 15.3+**
- Mature, ACID-compliant relational database
- Excellent JSON support for flexible fields
- Strong analytics performance
- Native array types for multi-value fields

### Extensions

#### 1. PostGIS 3.3+
**Purpose:** Geospatial queries and mapping
```sql
CREATE EXTENSION postgis;
```
**Features:**
- GEOGRAPHY type for lat/long coordinates
- Distance calculations (nearby wells within radius)
- Spatial indexes (GIST) for fast queries
- Coordinate system transformations

#### 2. TimescaleDB (Optional but Recommended)
**Purpose:** Time-series data optimization
```sql
CREATE EXTENSION timescaledb;
```
**Benefits:**
- Automatic partitioning of telemetry data
- 10x faster queries on time-series
- Data compression (reduce storage by 95%)
- Continuous aggregates for dashboards

---

## Data Sources Analysis

### Source 1: eRTMAC Tender Document
**Analyzed File:** `data/raw/eRTMAC tender document.pdf`

**Key Parameters Identified:**
- Real-time drilling telemetry requirements
- WITSML standard field names
- Data frequency: 10-second intervals
- Communication protocols

**Parameters Extracted (48 total):**
- Depth: MD, TVD, TVDSS
- Drilling: WOB, ROP, RPM, Torque
- Hydraulics: SPP, Flow Rate, Mud Weight
- Directional: Inclination, Azimuth
- Formation: Gamma Ray, Resistivity
- Operations: Rig State, On Bottom flag

### Source 2: Live Drilling CSV
**File:** `data/raw/16A(78)-32_time_data_10s_intervals_standard.csv`

**Columns (50 fields):**
```
Date, AutoDriller System Enabled, Azimuth, Bit Depth, Bit Diameter, 
Bit RPM, Block Position, Differential Pressure, Dog-Leg Severity, 
Downhole Torque, Flow In, Gamma MWD, Gas CO2, H2S, Hookload, 
Inclination, Mechanical Specific Energy, Mud Motor RPM, Mud Temperature,
On Bottom, Over Pull, Pump Pressure, Rate of Penetration, 
Return Flow, Rig Mode, Rig State, Running Speed, Stick Slip,
Tool Temperature, Top Drive RPM, Top Drive Torque, Total Strokes,
Weight on Bit, ... (and more)
```

**Data Characteristics:**
- Frequency: 10-second intervals
- Duration: Multiple months of continuous drilling
- Units: Mixed (feet, psi, GPM, °F) - requires conversion
- Missing values: Frequent nulls in certain parameters

### Source 3: Well Completion Reports (WCR)
**Sample File:** `well_1/56-32 EOWR - Final 22 July 2021.pdf`

**Data to Extract:**
- Well identification and location
- Spud date and completion date
- Total depth (MD and TVD)
- Casing program (sizes, depths, cement)
- Formation tops (name, depth)
- Directional survey data
- NPT summary and incidents
- Cost data
- Lessons learned

### Source 4: Daily Drilling Reports (DDR)
**Sample Files:** `well_1/56-32 Daily Drilling Reports/*.pdf`

**Data to Extract:**
- Report date and shift
- Start depth and end depth
- Depth drilled (daily progress)
- Bit information (size, type, hours)
- Mud properties (weight, viscosity, pH)
- Operations summary (text)
- Major events and incidents
- NPT hours and reasons
- Personnel on site

### Source 5: Offset Well Database
**Wells Available:**
- Well 1: 56-32 (Mapped to Nahorkatiya Field)
- Well 2: 78B-32 (Mapped to Moran Field)
- Well 3: Data available (Mapped to Baghjan Field)
- Well 4: Data available (Mapped to Rudrasagar Field)
- Well 5: Active well simulation (Mapped to Digboi Field)

---

## Database Schema Design

### Overview: 13 Core Tables

```
┌─────────────────────────────────────────────────────────────┐
│                    NWIS Database Schema                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐     ┌─────────────────┐     ┌──────────┐    │
│  │  wells   │────▶│ drilling_telem  │────▶│ alerts   │    │
│  └──────────┘     └─────────────────┘     └──────────┘    │
│       │                    │                                │
│       │                    │                                │
│       ▼                    ▼                                │
│  ┌──────────┐     ┌─────────────────┐                      │
│  │formation │     │   predictions   │                      │
│  │  _tops   │     └─────────────────┘                      │
│  └──────────┘                                               │
│       │                                                     │
│       ▼                                                     │
│  ┌──────────┐     ┌─────────────────┐     ┌──────────┐    │
│  │ daily_   │────▶│   incidents     │────▶│documents │    │
│  │drilling_ │     └─────────────────┘     └──────────┘    │
│  │ reports  │                                               │
│  └──────────┘                                               │
│       │                                                     │
│       ▼                                                     │
│  ┌──────────┐     ┌─────────────────┐                      │
│  │  well_   │     │ offset_well_    │                      │
│  │completion│     │    links        │                      │
│  │ _reports │     └─────────────────┘                      │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

---

### Table 1: `wells` - Well Master Data

**Purpose:** Central registry of all wells in the system

```sql
CREATE TABLE wells (
    -- Primary Key
    well_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Well Identification
    well_name VARCHAR(100) NOT NULL UNIQUE,  -- e.g., "DG-003", "NH-001"
    well_api_number VARCHAR(50),              -- API well number if available
    forge_source_id VARCHAR(100),             -- Original Utah FORGE ID (e.g., "16A(78)-32")
    
    -- Location Data (PostGIS)
    location GEOGRAPHY(POINT, 4326) NOT NULL, -- Lat/Long in WGS84
    latitude DECIMAL(10, 7) NOT NULL,         -- Extracted for easy access
    longitude DECIMAL(10, 7) NOT NULL,
    surface_elevation_m DECIMAL(8, 2),        -- Ground level elevation
    
    -- Field Information
    field_name VARCHAR(100) NOT NULL,         -- e.g., "Digboi", "Nahorkatiya"
    basin_name VARCHAR(100),                  -- e.g., "Upper Assam Basin"
    block_name VARCHAR(100),                  -- Licensing block
    
    -- Well Classification
    well_type VARCHAR(50),                    -- 'exploration', 'development', 'appraisal'
    well_status VARCHAR(50) NOT NULL,         -- 'planning', 'drilling', 'completed', 'suspended', 'abandoned'
    well_purpose VARCHAR(100),                -- 'oil', 'gas', 'geothermal', 'injection'
    
    -- Drilling Dates
    spud_date DATE,                           -- Start of drilling
    completion_date DATE,                     -- End of drilling
    first_production_date DATE,
    
    -- Depth Information
    total_depth_md DECIMAL(10, 2),            -- Measured Depth in meters
    total_depth_tvd DECIMAL(10, 2),           -- True Vertical Depth
    total_depth_tvdss DECIMAL(10, 2),         -- TVD Sub-Sea (below sea level)
    kick_off_point_md DECIMAL(10, 2),         -- Where directional drilling starts
    
    -- Rig Information
    rig_name VARCHAR(100),                    -- e.g., "Rig-7"
    rig_contractor VARCHAR(100),
    
    -- Operator
    operator VARCHAR(100) DEFAULT 'Oil India Limited',
    operator_contact VARCHAR(200),
    
    -- Data Source Metadata
    data_source VARCHAR(50),                  -- 'utah_forge', 'oil_india', 'manual'
    data_quality_score DECIMAL(3, 2),         -- 0.00 to 1.00
    is_offset_well BOOLEAN DEFAULT FALSE,     -- TRUE for historical wells
    is_active_well BOOLEAN DEFAULT FALSE,     -- TRUE for live monitoring
    
    -- Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Constraints
    CHECK (data_quality_score >= 0 AND data_quality_score <= 1),
    CHECK (well_status IN ('planning', 'drilling', 'completed', 'suspended', 'abandoned'))
);

-- Indexes
CREATE INDEX idx_wells_location ON wells USING GIST(location);
CREATE INDEX idx_wells_field_name ON wells(field_name);
CREATE INDEX idx_wells_status ON wells(well_status);
CREATE INDEX idx_wells_is_active ON wells(is_active_well) WHERE is_active_well = TRUE;
```

**Sample Data:**
```sql
INSERT INTO wells (well_name, forge_source_id, location, latitude, longitude, 
                   field_name, well_status, is_active_well) 
VALUES 
('DG-003', '16A(78)-32', ST_SetSRID(ST_MakePoint(95.62, 27.38), 4326), 
 27.38, 95.62, 'Digboi', 'drilling', TRUE),
('NH-001', '56-32', ST_SetSRID(ST_MakePoint(95.33, 27.29), 4326), 
 27.29, 95.33, 'Nahorkatiya', 'completed', FALSE);
```

---

### Table 2: `drilling_telemetry` - Real-Time Drilling Parameters

**Purpose:** Store high-frequency telemetry data (10-second intervals)

```sql
CREATE TABLE drilling_telemetry (
    -- Primary Key
    telemetry_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Timestamp
    timestamp TIMESTAMP NOT NULL,             -- UTC timestamp
    
    -- Depth Parameters
    bit_depth_md DECIMAL(10, 3),             -- Measured Depth (meters)
    bit_depth_tvd DECIMAL(10, 3),            -- True Vertical Depth (meters)
    bit_depth_tvdss DECIMAL(10, 3),          -- TVD Sub-Sea (meters)
    hole_depth_md DECIMAL(10, 3),            -- Total Hole Depth
    block_position_m DECIMAL(10, 3),         -- Travelling Block Position
    
    -- Drilling Parameters
    wob_klbs DECIMAL(8, 3),                  -- Weight on Bit (kilolbs)
    rop_m_hr DECIMAL(8, 3),                  -- Rate of Penetration (meters/hour)
    rpm_total DECIMAL(7, 2),                 -- Total RPM (Top Drive + Motor)
    top_drive_rpm DECIMAL(7, 2),             -- Top Drive RPM
    mud_motor_rpm DECIMAL(7, 2),             -- Mud Motor RPM
    
    -- Torque
    torque_surface_knm DECIMAL(8, 3),        -- Surface Torque (kN·m)
    torque_downhole_knm DECIMAL(8, 3),       -- Downhole Torque (kN·m)
    
    -- Hydraulics
    spp_kpa DECIMAL(8, 2),                   -- Standpipe Pressure (kPa)
    differential_pressure_kpa DECIMAL(8, 2), -- Differential Pressure across bit
    flow_rate_lpm DECIMAL(8, 2),             -- Flow In Rate (liters/minute)
    return_flow_percent DECIMAL(5, 2),       -- Return Flow as % of flow in
    total_strokes_per_min DECIMAL(6, 2),     -- Pump Strokes Per Minute
    
    -- Mud Properties
    mud_weight_in_ppg DECIMAL(5, 2),         -- Mud Weight In (pounds per gallon)
    mud_weight_out_ppg DECIMAL(5, 2),        -- Mud Weight Out
    mud_temp_in_c DECIMAL(5, 2),             -- Mud Temperature In (°C)
    mud_temp_out_c DECIMAL(5, 2),            -- Mud Temperature Out (°C)
    mud_viscosity_cp DECIMAL(6, 2),          -- Mud Viscosity (centipoise)
    
    -- Hookload
    hookload_klbs DECIMAL(8, 3),             -- Hookload (kilolbs)
    hookload_string_klbs DECIMAL(8, 3),      -- String Weight
    overpull_klbs DECIMAL(7, 3),             -- Overpull
    
    -- Directional Parameters
    inclination_deg DECIMAL(6, 3),           -- Inclination (degrees)
    azimuth_deg DECIMAL(6, 3),               -- Azimuth (degrees from North)
    dogleg_severity_deg_100ft DECIMAL(6, 3), -- Dogleg Severity (deg/100ft)
    
    -- Logging While Drilling (LWD/MWD)
    gamma_ray_api DECIMAL(7, 2),             -- Gamma Ray (API units)
    resistivity_ohmm DECIMAL(8, 3),          -- Resistivity (ohm·m)
    tool_temperature_c DECIMAL(6, 2),        -- MWD Tool Temperature (°C)
    
    -- Mechanical Specific Energy
    mse_surface_ksi DECIMAL(8, 3),           -- MSE Surface (ksi)
    mse_downhole_ksi DECIMAL(8, 3),          -- MSE Downhole (ksi)
    mse_total_ksi DECIMAL(8, 3),             -- MSE Total (ksi)
    
    -- Gas Detection
    gas_total_percent DECIMAL(5, 3),         -- Total Gas (%)
    gas_c1_percent DECIMAL(5, 3),            -- Methane (C1)
    gas_c2_percent DECIMAL(5, 3),            -- Ethane (C2)
    gas_co2_ppm DECIMAL(7, 2),               -- Carbon Dioxide (ppm)
    h2s_ppm DECIMAL(7, 2),                   -- Hydrogen Sulfide (ppm)
    
    -- Operational States
    rig_state VARCHAR(50),                   -- 'drilling', 'tripping_in', 'tripping_out', 
                                             -- 'circulating', 'connection', 'reaming'
    rig_mode VARCHAR(50),                    -- 'rotary', 'sliding', 'back_reaming'
    on_bottom BOOLEAN,                       -- Is bit on bottom?
    autodriller_enabled BOOLEAN,             -- Autodriller active?
    
    -- Performance Indicators
    stick_slip_index DECIMAL(5, 3),          -- Stick-Slip severity (0-1)
    running_speed_down_fpm DECIMAL(7, 2),    -- Running speed down (feet/min)
    running_speed_up_fpm DECIMAL(7, 2),      -- Running speed up (feet/min)
    
    -- Bit Information (snapshot at this time)
    bit_number INTEGER,                      -- Current bit number in use
    bit_diameter_inches DECIMAL(5, 3),       -- Bit diameter
    bit_total_revolutions INTEGER,           -- Total revolutions on this bit
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(50) DEFAULT 'ertmac', -- 'ertmac', 'csv_replay', 'manual'
    
    -- Constraints
    UNIQUE (well_id, timestamp)              -- Prevent duplicate timestamps
);

-- Primary Index (Hypertable if using TimescaleDB)
SELECT create_hypertable('drilling_telemetry', 'timestamp', 
                         chunk_time_interval => INTERVAL '1 day');

-- Additional Indexes
CREATE INDEX idx_drilling_telemetry_well_time 
    ON drilling_telemetry(well_id, timestamp DESC);
CREATE INDEX idx_drilling_telemetry_depth 
    ON drilling_telemetry(well_id, bit_depth_md);
CREATE INDEX idx_drilling_telemetry_rig_state 
    ON drilling_telemetry(rig_state) WHERE rig_state IS NOT NULL;
```

---

### Table 3: `formation_tops` - Geological Formation Markers

**Purpose:** Store formation boundaries for correlation and 3D visualization

```sql
CREATE TABLE formation_tops (
    -- Primary Key
    formation_top_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Formation Identification
    formation_name VARCHAR(200) NOT NULL,    -- e.g., "Barail Formation", "Tipam Sandstone"
    formation_code VARCHAR(50),              -- Standardized code
    formation_age VARCHAR(100),              -- e.g., "Miocene", "Oligocene"
    formation_lithology VARCHAR(200),        -- e.g., "Sandstone", "Shale", "Limestone"
    
    -- Depth Data
    top_depth_md DECIMAL(10, 3) NOT NULL,    -- Top of formation (MD)
    top_depth_tvd DECIMAL(10, 3),            -- Top of formation (TVD)
    top_depth_tvdss DECIMAL(10, 3),          -- Top of formation (TVDSS)
    bottom_depth_md DECIMAL(10, 3),          -- Bottom of formation (MD)
    bottom_depth_tvd DECIMAL(10, 3),         -- Bottom of formation (TVD)
    thickness_md DECIMAL(10, 3),             -- Formation thickness (MD)
    thickness_tvd DECIMAL(10, 3),            -- Formation thickness (TVD)
    
    -- Identification Method
    identified_date TIMESTAMP,
    identification_method VARCHAR(50),        -- 'MWD', 'LWD', 'Cuttings', 'Wireline_Logs', 'Cores'
    identified_by VARCHAR(100),               -- Geologist name
    
    -- Formation Properties
    porosity_percent DECIMAL(5, 2),          -- Porosity (%)
    permeability_md DECIMAL(8, 3),           -- Permeability (millidarcies)
    water_saturation_percent DECIMAL(5, 2),  -- Water Saturation (%)
    hydrocarbon_shows BOOLEAN,               -- Presence of hydrocarbons
    
    -- Notes
    notes TEXT,                               -- Free-text observations
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (top_depth_md < bottom_depth_md OR bottom_depth_md IS NULL)
);

-- Indexes
CREATE INDEX idx_formation_tops_well_depth 
    ON formation_tops(well_id, top_depth_md);
CREATE INDEX idx_formation_tops_name 
    ON formation_tops(formation_name);
```

---

### Table 4: `daily_drilling_reports` - Extracted DDR Data

**Purpose:** Store structured data extracted from Daily Drilling Reports

```sql
CREATE TABLE daily_drilling_reports (
    -- Primary Key
    ddr_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(document_id),
    
    -- Report Identification
    report_date DATE NOT NULL,
    report_number VARCHAR(50),
    shift VARCHAR(20),                        -- 'day', 'night', 'both'
    
    -- Depth Progress
    start_depth_md DECIMAL(10, 3),
    end_depth_md DECIMAL(10, 3),
    depth_drilled_m DECIMAL(8, 3),            -- Progress made this period
    
    -- Time Breakdown
    drilling_hours DECIMAL(5, 2),
    tripping_hours DECIMAL(5, 2),
    circulating_hours DECIMAL(5, 2),
    connection_time_hours DECIMAL(5, 2),
    npt_hours DECIMAL(5, 2),                  -- Non-Productive Time
    total_hours DECIMAL(5, 2) DEFAULT 24.0,
    
    -- Bit Information
    bit_number INTEGER,
    bit_size_mm DECIMAL(6, 2),
    bit_type VARCHAR(100),
    bit_manufacturer VARCHAR(100),
    bit_serial_number VARCHAR(100),
    bit_hours_this_run DECIMAL(6, 2),
    bit_depth_in_m DECIMAL(10, 3),
    bit_depth_out_m DECIMAL(10, 3),
    
    -- Mud Properties
    mud_weight_ppg DECIMAL(5, 2),
    mud_viscosity_cp DECIMAL(6, 2),
    mud_ph DECIMAL(4, 2),
    fluid_loss_ml_30min DECIMAL(6, 2),
    sand_content_percent DECIMAL(5, 3),
    mud_volume_m3 DECIMAL(8, 2),
    
    -- Operations Summary
    operations_summary TEXT,                  -- Free-text description
    major_events TEXT,                        -- Important events
    formation_description TEXT,               -- Geological observations
    
    -- Performance Metrics
    avg_rop_m_hr DECIMAL(7, 3),
    max_wob_klbs DECIMAL(7, 3),
    avg_rpm DECIMAL(6, 2),
    max_torque_knm DECIMAL(7, 3),
    
    -- Personnel
    company_man VARCHAR(100),
    toolpusher VARCHAR(100),
    driller VARCHAR(100),
    
    -- Extraction Metadata
    extracted_at TIMESTAMP,
    extraction_method VARCHAR(50),            -- 'ocr', 'manual', 'api'
    extraction_confidence DECIMAL(3, 2),      -- 0.00 to 1.00
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id, report_date, shift),
    CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1)
);

-- Indexes
CREATE INDEX idx_ddr_well_date ON daily_drilling_reports(well_id, report_date DESC);
CREATE INDEX idx_ddr_depth ON daily_drilling_reports(well_id, end_depth_md);
```

---

### Table 5: `well_completion_reports` - Extracted WCR Data

**Purpose:** Store structured data from Well Completion Reports

```sql
CREATE TABLE well_completion_reports (
    -- Primary Key
    wcr_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(document_id),
    
    -- Report Information
    report_date DATE NOT NULL,
    report_version VARCHAR(20),
    report_author VARCHAR(100),
    
    -- Well Summary
    completion_date DATE,
    final_td_md DECIMAL(10, 3),
    final_td_tvd DECIMAL(10, 3),
    total_drilling_days INTEGER,
    total_cost_usd DECIMAL(15, 2),
    
    -- Casing Design (JSON for flexibility)
    casing_design JSONB,
    /* Example structure:
    [
        {
            "casing_string": "Conductor",
            "size_inches": 30,
            "depth_md": 50,
            "grade": "API 5CT K55",
            "weight_lb_ft": 133,
            "cement_top_md": 0,
            "cement_bottom_md": 50
        },
        { ... }
    ]
    */
    
    -- Cement Design
    cement_design JSONB,
    /* Example:
    {
        "primary_cement": {
            "type": "Class G",
            "density_ppg": 16.5,
            "volume_bbl": 150
        },
        "squeeze_jobs": [ ... ]
    }
    */
    
    -- Wellhead Details
    wellhead_details JSONB,
    
    -- Formation Summary
    geological_summary TEXT,
    formation_tops JSONB,                     -- Duplicate of formation_tops table for archival
    
    -- NPT Summary
    total_npt_hours DECIMAL(8, 2),
    npt_summary TEXT,
    major_incidents TEXT,
    
    -- Performance Summary
    avg_rop_m_hr DECIMAL(7, 3),
    max_inclination_deg DECIMAL(6, 3),
    hydrocarbon_shows TEXT,
    
    -- Lessons Learned
    lessons_learned TEXT,
    recommendations TEXT,
    
    -- Cost Breakdown
    cost_summary JSONB,
    /* Example:
    {
        "rig_cost": 1500000,
        "services": 800000,
        "materials": 400000,
        "fuel": 100000
    }
    */
    
    -- Extraction Metadata
    extracted_at TIMESTAMP,
    extraction_method VARCHAR(50),
    extraction_confidence DECIMAL(3, 2),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id, report_date),
    CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1)
);

-- Indexes
CREATE INDEX idx_wcr_well ON well_completion_reports(well_id);
CREATE INDEX idx_wcr_completion_date ON well_completion_reports(completion_date);
```

---

### Table 6: `incidents` - NPT Events and Drilling Problems

**Purpose:** Track all incidents, stuck pipe events, lost circulation, etc.

```sql
CREATE TABLE incidents (
    -- Primary Key
    incident_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(document_id),
    telemetry_start_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    telemetry_end_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    
    -- Incident Classification
    incident_type VARCHAR(100) NOT NULL,      -- 'stuck_pipe', 'lost_circulation', 'kick',
                                              -- 'twist_off', 'equipment_failure', 'wellbore_instability'
    incident_category VARCHAR(50),            -- 'operational', 'geological', 'equipment'
    severity VARCHAR(20) NOT NULL,            -- 'low', 'medium', 'high', 'critical'
    
    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_hours DECIMAL(8, 2),
    
    -- Location
    depth_md DECIMAL(10, 3),
    depth_tvd DECIMAL(10, 3),
    formation_name VARCHAR(200),
    
    -- NPT Impact
    npt_hours DECIMAL(8, 2),                  -- Non-Productive Time
    cost_impact_usd DECIMAL(12, 2),
    
    -- Description
    description TEXT NOT NULL,                -- What happened
    root_cause TEXT,                          -- Why it happened
    corrective_action TEXT,                   -- What was done to fix it
    preventive_measures TEXT,                 -- How to prevent in future
    
    -- Operational Context (snapshot at time of incident)
    wob_klbs DECIMAL(8, 3),
    rop_m_hr DECIMAL(8, 3),
    rpm DECIMAL(7, 2),
    torque_knm DECIMAL(8, 3),
    spp_kpa DECIMAL(8, 2),
    mud_weight_ppg DECIMAL(5, 2),
    
    -- Detection
    detected_by VARCHAR(100),                 -- Person or system that detected
    detection_method VARCHAR(100),            -- 'realtime_alert', 'visual', 'log_analysis'
    
    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Constraints
    CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CHECK (end_time IS NULL OR end_time >= start_time)
);

-- Indexes
CREATE INDEX idx_incidents_well_time ON incidents(well_id, start_time DESC);
CREATE INDEX idx_incidents_type ON incidents(incident_type);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_depth ON incidents(well_id, depth_md);
CREATE INDEX idx_incidents_unresolved ON incidents(resolved) WHERE resolved = FALSE;
```

---

### Table 7: `documents` - Document Registry

**Purpose:** Track all uploaded documents (PDFs, images, etc.)

```sql
CREATE TABLE documents (
    -- Primary Key
    document_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Document Classification
    doc_type VARCHAR(50) NOT NULL,            -- 'DDR', 'WCR', 'EOWR', 'MorningReport', 
                                              -- 'GeologyReport', 'MudLog', 'Survey', 'Other'
    doc_subtype VARCHAR(100),
    
    -- File Information
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,         -- Relative path from data root
    file_size_bytes BIGINT,
    file_hash_sha256 VARCHAR(64),             -- For duplicate detection
    mime_type VARCHAR(100),                   -- 'application/pdf', 'image/jpeg'
    
    -- Document Dates
    document_date DATE,                       -- Date the document represents
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- PDF Metadata
    page_count INTEGER,
    pdf_version VARCHAR(20),
    
    -- Extraction Status
    extraction_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'failed'
    extraction_started_at TIMESTAMP,
    extraction_completed_at TIMESTAMP,
    extraction_error TEXT,
    extracted_json_path VARCHAR(1000),        -- Path to JSON output file
    
    -- OCR Status (if applicable)
    ocr_status VARCHAR(50),                   -- 'not_required', 'pending', 'completed', 'failed'
    ocr_confidence_avg DECIMAL(5, 4),         -- Average OCR confidence (0.0000 to 1.0000)
    ocr_text_path VARCHAR(1000),              -- Path to extracted text file
    
    -- Search
    full_text_search TSVECTOR,                -- PostgreSQL full-text search
    
    -- Tags
    tags TEXT[],                              -- Array of tags for categorization
    
    -- Audit
    uploaded_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (file_hash_sha256),                -- Prevent duplicate uploads
    CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes
CREATE INDEX idx_documents_well_type ON documents(well_id, doc_type);
CREATE INDEX idx_documents_date ON documents(document_date);
CREATE INDEX idx_documents_extraction_status ON documents(extraction_status);
CREATE INDEX idx_documents_full_text ON documents USING GIN(full_text_search);
```

---

### Table 8: `offset_well_links` - Well Proximity Relationships

**Purpose:** Pre-calculated relationships between wells for fast nearby well queries

```sql
CREATE TABLE offset_well_links (
    -- Primary Key
    link_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys (both directions)
    well_id_a UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    well_id_b UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Spatial Relationship
    distance_km DECIMAL(10, 3) NOT NULL,      -- Distance between wells
    bearing_deg DECIMAL(6, 3),                -- Bearing from A to B
    
    -- Geological Similarity
    formation_overlap_count INTEGER DEFAULT 0, -- Number of shared formations
    formation_similarity_score DECIMAL(3, 2),  -- 0.00 to 1.00
    
    -- Operational Similarity (ML-calculated)
    similarity_score DECIMAL(3, 2),           -- Overall similarity (0.00 to 1.00)
    similarity_features JSONB,                 -- What makes them similar
    
    -- Correlation Flags
    is_nearby BOOLEAN GENERATED ALWAYS AS (distance_km <= 10.0) STORED,  -- Within 10km
    is_analog BOOLEAN DEFAULT FALSE,          -- Manually flagged as analog well
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id_a, well_id_b),
    CHECK (well_id_a < well_id_b),            -- Ensure ordered pairs
    CHECK (similarity_score >= 0 AND similarity_score <= 1),
    CHECK (formation_similarity_score >= 0 AND formation_similarity_score <= 1)
);

-- Indexes
CREATE INDEX idx_offset_well_links_well_a ON offset_well_links(well_id_a, distance_km);
CREATE INDEX idx_offset_well_links_well_b ON offset_well_links(well_id_b, distance_km);
CREATE INDEX idx_offset_well_links_nearby ON offset_well_links(is_nearby) WHERE is_nearby = TRUE;
```

---

### Table 9: `alerts` - Real-Time Alert Log

**Purpose:** Log all generated alerts for tracking and analytics

```sql
CREATE TABLE alerts (
    -- Primary Key
    alert_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    telemetry_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    related_incident_id INTEGER REFERENCES incidents(incident_id),
    
    -- Alert Classification
    alert_type VARCHAR(100) NOT NULL,         -- 'stuck_pipe_risk', 'lost_circulation_risk',
                                              -- 'abnormal_pressure', 'equipment_anomaly',
                                              -- 'parameter_limit_exceeded'
    alert_category VARCHAR(50),               -- 'drilling', 'hydraulics', 'directional', 'safety'
    severity VARCHAR(20) NOT NULL,            -- 'info', 'warning', 'critical'
    
    -- Alert Content
    message TEXT NOT NULL,                    -- Human-readable message
    detailed_message TEXT,                    -- Additional details
    recommendations TEXT,                     -- Suggested actions
    
    -- Timing
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                     -- Auto-clear alerts after this time
    
    -- User Interaction
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    dismissed BOOLEAN DEFAULT FALSE,
    dismissed_at TIMESTAMP,
    dismissed_by VARCHAR(100),
    
    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    
    -- Alert Context (snapshot of parameters)
    context_data JSONB,
    /* Example:
    {
        "wob": 35.2,
        "rop": 2.1,
        "torque": 28.5,
        "threshold_exceeded": "wob",
        "threshold_value": 30.0
    }
    */
    
    -- Alert Source
    alert_source VARCHAR(50),                 -- 'rule_engine', 'ml_model', 'manual'
    rule_id VARCHAR(100),                     -- Which rule triggered this
    model_name VARCHAR(100),                  -- Which ML model
    confidence_score DECIMAL(5, 4),           -- Model confidence (0.0000 to 1.0000)
    
    -- Notification Status
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at TIMESTAMP,
    notification_channels TEXT[],             -- ['email', 'sms', 'dashboard']
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (severity IN ('info', 'warning', 'critical'))
);

-- Indexes
CREATE INDEX idx_alerts_well_time ON alerts(well_id, triggered_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_unacknowledged ON alerts(acknowledged) WHERE acknowledged = FALSE;
CREATE INDEX idx_alerts_active ON alerts(resolved) WHERE resolved = FALSE;
```

---

### Table 10: `predictions` - ML Model Outputs

**Purpose:** Store predictions from machine learning models

```sql
CREATE TABLE predictions (
    -- Primary Key
    prediction_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    telemetry_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    
    -- Model Information
    model_name VARCHAR(100) NOT NULL,         -- e.g., "stuck_pipe_rf_v1.2"
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50),                   -- 'classification', 'regression', 'anomaly_detection'
    
    -- Prediction Timing
    prediction_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prediction_horizon_hours DECIMAL(6, 2),   -- How far ahead (NULL for current state)
    
    -- Prediction Output
    predicted_event VARCHAR(200) NOT NULL,    -- e.g., "stuck_pipe", "lost_circulation", "normal"
    prediction_class INTEGER,                 -- Class ID for classification
    prediction_value DECIMAL(12, 6),          -- Continuous value for regression
    probability DECIMAL(7, 6) NOT NULL,       -- Probability score (0.000000 to 1.000000)
    
    -- Confidence Intervals (for regression)
    confidence_interval_low DECIMAL(12, 6),
    confidence_interval_high DECIMAL(12, 6),
    confidence_level_percent DECIMAL(5, 2),   -- e.g., 95.0 for 95% CI
    
    -- Feature Importance
    feature_importance JSONB,
    /* Example:
    {
        "wob": 0.32,
        "rop": 0.28,
        "torque": 0.22,
        "spp": 0.18
    }
    */
    
    -- SHAP Values (explainability)
    shap_values JSONB,
    
    -- Input Features (snapshot)
    input_features JSONB,
    
    -- Outcome Tracking (for model evaluation)
    outcome VARCHAR(50),                      -- 'true_positive', 'false_positive', 
                                              -- 'true_negative', 'false_negative', 'pending'
    outcome_time TIMESTAMP,
    outcome_notes TEXT,
    
    -- Alert Generated
    alert_generated BOOLEAN DEFAULT FALSE,
    alert_id BIGINT REFERENCES alerts(alert_id),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (probability >= 0 AND probability <= 1),
    CHECK (outcome IN ('true_positive', 'false_positive', 'true_negative', 'false_negative', 'pending') OR outcome IS NULL)
);

-- Indexes
CREATE INDEX idx_predictions_well_time ON predictions(well_id, prediction_time DESC);
CREATE INDEX idx_predictions_model ON predictions(model_name, model_version);
CREATE INDEX idx_predictions_event ON predictions(predicted_event, probability DESC);
CREATE INDEX idx_predictions_outcome ON predictions(outcome) WHERE outcome IS NOT NULL;
```

---

### Table 11: `user_annotations` - Human Labels for ML Training

**Purpose:** Store expert labels for training and validating ML models

```sql
CREATE TABLE user_annotations (
    -- Primary Key
    annotation_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    telemetry_start_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    telemetry_end_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    related_incident_id INTEGER REFERENCES incidents(incident_id),
    
    -- Time Range
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    
    -- Depth Range
    start_depth_md DECIMAL(10, 3),
    end_depth_md DECIMAL(10, 3),
    
    -- Annotation Label
    label VARCHAR(200) NOT NULL,              -- e.g., "stuck_pipe_precursor", "normal_drilling",
                                              -- "lost_circulation_event", "unstable_wellbore"
    label_category VARCHAR(100),              -- 'positive_example', 'negative_example', 'neutral'
    
    -- Confidence
    annotator_confidence VARCHAR(20),         -- 'low', 'medium', 'high'
    
    -- Description
    notes TEXT,
    contextual_information TEXT,              -- Why this label was chosen
    
    -- Annotator
    annotated_by VARCHAR(100) NOT NULL,
    annotator_role VARCHAR(100),              -- 'drilling_engineer', 'geologist', 'data_scientist'
    annotation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    validated_by VARCHAR(100),
    validated_at TIMESTAMP,
    validation_notes TEXT,
    
    -- Usage in Training
    used_in_training BOOLEAN DEFAULT FALSE,
    training_dataset_id VARCHAR(100),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (end_time >= start_time),
    CHECK (annotator_confidence IN ('low', 'medium', 'high') OR annotator_confidence IS NULL)
);

-- Indexes
CREATE INDEX idx_annotations_well_time ON user_annotations(well_id, start_time);
CREATE INDEX idx_annotations_label ON user_annotations(label);
CREATE INDEX idx_annotations_annotator ON user_annotations(annotated_by);
CREATE INDEX idx_annotations_training ON user_annotations(used_in_training) 
    WHERE used_in_training = TRUE;
```

---

### Table 12: `directional_surveys` - Wellbore Trajectory Data

**Purpose:** Store directional survey points for 3D well path visualization

```sql
CREATE TABLE directional_surveys (
    -- Primary Key
    survey_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Survey Station
    measured_depth_md DECIMAL(10, 3) NOT NULL,
    
    -- Survey Measurements
    inclination_deg DECIMAL(6, 3) NOT NULL,   -- Inclination from vertical
    azimuth_deg DECIMAL(6, 3) NOT NULL,       -- Azimuth from North
    
    -- Calculated Coordinates
    tvd DECIMAL(10, 3),                       -- True Vertical Depth
    northing_m DECIMAL(12, 3),                -- North displacement from surface
    easting_m DECIMAL(12, 3),                 -- East displacement from surface
    vertical_section_m DECIMAL(12, 3),        -- Distance along planned direction
    
    -- 3D Coordinates (for visualization)
    position_3d GEOMETRY(POINTZ, 4326),       -- PostGIS 3D point
    
    -- Survey Quality
    survey_type VARCHAR(50),                  -- 'MWD', 'gyro', 'magnetic', 'multi_station'
    tool_type VARCHAR(100),
    survey_quality VARCHAR(20),               -- 'excellent', 'good', 'fair', 'poor'
    
    -- Dogleg
    dogleg_severity_deg_100ft DECIMAL(6, 3),  -- Dogleg severity at this station
    
    -- Survey Timing
    survey_date TIMESTAMP,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id, measured_depth_md),
    CHECK (inclination_deg >= 0 AND inclination_deg <= 180),
    CHECK (azimuth_deg >= 0 AND azimuth_deg < 360)
);

-- Indexes
CREATE INDEX idx_surveys_well_depth ON directional_surveys(well_id, measured_depth_md);
CREATE INDEX idx_surveys_position ON directional_surveys USING GIST(position_3d);
```

---

### Table 13: `system_logs` - Audit Trail

**Purpose:** System-level audit logging

```sql
CREATE TABLE system_logs (
    -- Primary Key
    log_id BIGSERIAL PRIMARY KEY,
    
    -- Timestamp
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Log Level
    log_level VARCHAR(20) NOT NULL,           -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    
    -- Source
    module_name VARCHAR(100),                 -- 'ocr_extraction', 'alert_engine', 'api_server'
    function_name VARCHAR(200),
    
    -- User Context
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    
    -- Log Message
    message TEXT NOT NULL,
    stack_trace TEXT,
    
    -- Related Entities
    well_id UUID REFERENCES wells(well_id),
    document_id INTEGER REFERENCES documents(document_id),
    
    -- Additional Context
    metadata JSONB,
    
    -- Constraints
    CHECK (log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

-- Indexes
CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX idx_system_logs_level ON system_logs(log_level);
CREATE INDEX idx_system_logs_module ON system_logs(module_name);
```

---

## Entity Relationship Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         NWIS Database Schema ERD                              │
└──────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────┐
                                    │    wells    │ (Master Table)
                                    │─────────────│
                                    │ well_id PK  │
                                    │ well_name   │
                                    │ location    │ (PostGIS GEOGRAPHY)
                                    │ field_name  │
                                    │ well_status │
                                    └──────┬──────┘
                                           │
                   ┌───────────────────────┼───────────────────────┐
                   │                       │                       │
                   ▼                       ▼                       ▼
        ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
        │ drilling_telem   │   │ formation_tops   │   │   documents      │
        │──────────────────│   │──────────────────│   │──────────────────│
        │ telemetry_id PK  │   │ formation_top_id │   │ document_id PK   │
        │ well_id FK       │   │ well_id FK       │   │ well_id FK       │
        │ timestamp        │   │ formation_name   │   │ doc_type         │
        │ bit_depth_md     │   │ top_depth_md     │   │ file_path        │
        │ wob_klbs         │   │ formation_age    │   │ extraction_status│
        │ rop_m_hr         │   └──────────────────┘   └───────┬──────────┘
        │ ... (48 fields)  │                                  │
        └────────┬─────────┘                                  │
                 │                                             │
                 │                      ┌──────────────────────┘
                 │                      │
                 ▼                      ▼
        ┌──────────────────┐   ┌──────────────────┐
        │     alerts       │   │ daily_drilling   │
        │──────────────────│   │     _reports     │
        │ alert_id PK      │   │──────────────────│
        │ well_id FK       │   │ ddr_id PK        │
        │ telemetry_id FK  │   │ well_id FK       │
        │ alert_type       │   │ document_id FK   │
        │ severity         │   │ report_date      │
        │ message          │   │ start_depth_md   │
        │ acknowledged     │   │ end_depth_md     │
        └──────────────────┘   │ depth_drilled_m  │
                               │ npt_hours        │
                               └────────┬─────────┘
                                        │
                 ┌──────────────────────┼───────────────────┐
                 │                      │                   │
                 ▼                      ▼                   ▼
        ┌──────────────────┐   ┌──────────────────┐  ┌──────────────────┐
        │   incidents      │   │  well_completion │  │ directional_     │
        │──────────────────│   │     _reports     │  │    surveys       │
        │ incident_id PK   │   │──────────────────│  │──────────────────│
        │ well_id FK       │   │ wcr_id PK        │  │ survey_id PK     │
        │ document_id FK   │   │ well_id FK       │  │ well_id FK       │
        │ incident_type    │   │ document_id FK   │  │ measured_depth_md│
        │ severity         │   │ casing_design    │  │ inclination_deg  │
        │ npt_hours        │   │ cement_design    │  │ azimuth_deg      │
        │ root_cause       │   │ cost_summary     │  │ position_3d      │
        └──────────────────┘   └──────────────────┘  │ (PostGIS 3D)     │
                 │                                    └──────────────────┘
                 │
                 ▼
        ┌──────────────────┐
        │  predictions     │
        │──────────────────│
        │ prediction_id PK │
        │ well_id FK       │
        │ model_name       │
        │ predicted_event  │
        │ probability      │
        │ outcome          │
        └──────────────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ user_annotations │
        │──────────────────│
        │ annotation_id PK │
        │ well_id FK       │
        │ label            │
        │ annotated_by     │
        └──────────────────┘


        ┌──────────────────┐
        │ offset_well_     │
        │     links        │
        │──────────────────│
        │ link_id PK       │
        │ well_id_a FK     │───┐
        │ well_id_b FK     │───┼─▶ References wells.well_id
        │ distance_km      │   │
        │ similarity_score │───┘
        └──────────────────┘
```

---

## Indexes and Performance

### Primary Indexes

1. **Time-Series Queries** (drilling_telemetry)
   - `(well_id, timestamp DESC)` - For latest data
   - `(well_id, bit_depth_md)` - For depth-based queries
   - TimescaleDB hypertable with 1-day chunks

2. **Geospatial Queries** (wells)
   - `GIST(location)` - For nearby well searches
   - `GIST(position_3d)` on directional_surveys

3. **Full-Text Search** (documents)
   - `GIN(full_text_search)` - For document content search
   - `GIN(tags)` - For tag-based filtering

### Query Performance Targets

| Query Type | Target Response Time | Index Used |
|------------|---------------------|------------|
| Latest telemetry (last 100 rows) | < 50ms | well_id + timestamp DESC |
| Nearby wells (< 10km) | < 100ms | GIST(location) |
| Formation tops at depth | < 30ms | well_id + top_depth_md |
| Incident history (6 months) | < 200ms | well_id + start_time |
| Document search | < 300ms | GIN(full_text_search) |
| Offset well correlation | < 150ms | offset_well_links |

---

## Visualization Support

### For 2D Map Visualization (Leaflet.js, Mapbox)

**Query: Get all wells with status for map markers**
```sql
SELECT 
    well_id,
    well_name,
    ST_Y(location::geometry) AS latitude,
    ST_X(location::geometry) AS longitude,
    field_name,
    well_status,
    is_active_well,
    total_depth_md
FROM wells
WHERE well_status != 'abandoned';
```

**Query: Find nearby wells within radius**
```sql
SELECT 
    w2.well_id,
    w2.well_name,
    ST_Distance(w1.location, w2.location) / 1000 AS distance_km,
    w2.field_name,
    w2.well_status
FROM wells w1
CROSS JOIN wells w2
WHERE w1.well_id = 'active_well_uuid'
  AND w1.well_id != w2.well_id
  AND ST_DWithin(w1.location, w2.location, 10000)  -- 10km in meters
ORDER BY distance_km;
```

### For 3D Well Visualization (Three.js, Blender API, Cesium)

**Query: Get well trajectory for 3D path**
```sql
SELECT 
    measured_depth_md,
    tvd,
    northing_m,
    easting_m,
    inclination_deg,
    azimuth_deg,
    ST_Z(position_3d::geometry) AS z_coordinate
FROM directional_surveys
WHERE well_id = 'well_uuid'
ORDER BY measured_depth_md;
```

**Query: Formation layers for cross-section**
```sql
SELECT 
    formation_name,
    formation_lithology,
    top_depth_md,
    bottom_depth_md,
    thickness_tvd,
    formation_age
FROM formation_tops
WHERE well_id = 'well_uuid'
ORDER BY top_depth_md;
```

### For Real-Time Dashboard Charts (Recharts, ECharts)

**Query: Latest telemetry (last 10 minutes)**
```sql
SELECT 
    timestamp,
    bit_depth_md,
    wob_klbs,
    rop_m_hr,
    torque_surface_knm,
    spp_kpa,
    rig_state
FROM drilling_telemetry
WHERE well_id = 'active_well_uuid'
  AND timestamp >= NOW() - INTERVAL '10 minutes'
ORDER BY timestamp DESC;
```

**Query: Depth vs. Parameter chart**
```sql
SELECT 
    bit_depth_md,
    AVG(wob_klbs) AS avg_wob,
    AVG(rop_m_hr) AS avg_rop,
    AVG(torque_surface_knm) AS avg_torque,
    COUNT(*) AS data_points
FROM drilling_telemetry
WHERE well_id = 'well_uuid'
  AND bit_depth_md BETWEEN 1000 AND 3000
GROUP BY FLOOR(bit_depth_md / 10) * 10  -- 10m bins
ORDER BY bit_depth_md;
```

---

## Sample Queries

### 1. Real-Time Monitoring

**Get latest telemetry with alert status**
```sql
SELECT 
    dt.timestamp,
    dt.bit_depth_md,
    dt.wob_klbs,
    dt.rop_m_hr,
    dt.rig_state,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM alerts a 
            WHERE a.well_id = dt.well_id 
            AND a.telemetry_id = dt.telemetry_id 
            AND a.severity = 'critical'
            AND a.resolved = FALSE
        ) THEN 'CRITICAL'
        WHEN EXISTS (
            SELECT 1 FROM alerts a 
            WHERE a.well_id = dt.well_id 
            AND a.telemetry_id = dt.telemetry_id 
            AND a.severity = 'warning'
            AND a.resolved = FALSE
        ) THEN 'WARNING'
        ELSE 'NORMAL'
    END AS alert_status
FROM drilling_telemetry dt
WHERE dt.well_id = 'active_well_uuid'
ORDER BY dt.timestamp DESC
LIMIT 1;
```

### 2. Offset Well Correlation

**Find similar incidents in nearby wells**
```sql
WITH nearby_wells AS (
    SELECT well_id_b AS nearby_well_id, distance_km
    FROM offset_well_links
    WHERE well_id_a = 'active_well_uuid'
      AND distance_km <= 10.0
)
SELECT 
    i.incident_type,
    i.depth_md,
    i.npt_hours,
    i.description,
    i.corrective_action,
    w.well_name,
    nw.distance_km
FROM incidents i
JOIN nearby_wells nw ON i.well_id = nw.nearby_well_id
JOIN wells w ON i.well_id = w.well_id
WHERE i.incident_type IN ('stuck_pipe', 'lost_circulation')
  AND i.depth_md BETWEEN 2000 AND 2500
ORDER BY nw.distance_km, i.npt_hours DESC;
```

### 3. Formation Correlation

**Compare formation tops across offset wells**
```sql
SELECT 
    ft.formation_name,
    w.well_name,
    ft.top_depth_md,
    ft.formation_lithology,
    ST_Distance(w.location, active_well.location) / 1000 AS distance_km
FROM formation_tops ft
JOIN wells w ON ft.well_id = w.well_id
CROSS JOIN (
    SELECT location FROM wells WHERE well_id = 'active_well_uuid'
) active_well
WHERE ft.formation_name IN ('Barail Formation', 'Tipam Sandstone')
  AND ST_DWithin(w.location, active_well.location, 15000)  -- 15km
ORDER BY ft.formation_name, distance_km;
```

### 4. Predictive Analytics

**Get high-risk predictions with context**
```sql
SELECT 
    p.prediction_time,
    p.predicted_event,
    p.probability,
    p.model_name,
    dt.bit_depth_md,
    dt.wob_klbs,
    dt.rop_m_hr,
    dt.torque_surface_knm,
    p.feature_importance->>'wob' AS wob_importance,
    p.feature_importance->>'rop' AS rop_importance
FROM predictions p
JOIN drilling_telemetry dt ON p.telemetry_id = dt.telemetry_id
WHERE p.well_id = 'active_well_uuid'
  AND p.probability >= 0.7
  AND p.predicted_event != 'normal'
  AND p.prediction_time >= NOW() - INTERVAL '24 hours'
ORDER BY p.probability DESC;
```

### 5. NPT Analysis

**Calculate NPT by incident type**
```sql
SELECT 
    incident_type,
    COUNT(*) AS incident_count,
    SUM(npt_hours) AS total_npt_hours,
    AVG(npt_hours) AS avg_npt_hours,
    SUM(cost_impact_usd) AS total_cost_usd
FROM incidents
WHERE well_id IN (SELECT well_id FROM wells WHERE field_name = 'Digboi')
  AND start_time >= '2024-01-01'
GROUP BY incident_type
ORDER BY total_npt_hours DESC;
```

---

## Implementation Roadmap

### Phase 1: Database Setup (Week 1)
✅ Install PostgreSQL 15+  
✅ Install PostGIS extension  
✅ Create database and user  
✅ Execute schema creation scripts  
✅ Set up backups  

### Phase 2: Data Migration (Week 2-3)
- **Wells Master Data**
  - Manual entry for 5 offset wells
  - Coordinate mapping (Utah FORGE → Assam fields)
  
- **CSV Telemetry Import**
  - Build ETL pipeline for 16A(78)-32 CSV
  - Unit conversion (feet→meters, psi→kPa)
  - Batch insert with validation

- **Document Registration**
  - Scan data/raw/ folders
  - Register PDFs in documents table
  - Generate file hashes

### Phase 3: OCR Integration (Week 4-5)
- Connect existing OCR system
- Extract DDR data → daily_drilling_reports table
- Extract WCR data → well_completion_reports table
- Populate formation_tops and incidents tables

### Phase 4: Real-Time Integration (Week 6)
- Build live telemetry ingestion API
- WebSocket server for live data streaming
- Alert rule engine
- Dashboard API endpoints

### Phase 5: Analytics & ML (Week 7-8)
- Populate predictions table with ML outputs
- Build annotation UI for user_annotations
- Offset well link calculation
- Performance optimization

---

## Next Steps

1. **Review and Approve Schema** ✅ (You're reading this!)
2. **Execute Database Creation Scripts** (I'll generate these)
3. **Populate Sample Data** (Start with 1-2 wells)
4. **Test Queries** (Verify performance)
5. **Build ETL Pipelines** (CSV → Database)
6. **Integrate with Modules** (Module 2, 3, 4 consumption)

---

**End of Database Design Document**
