# NWIS Project - Current Development Plan

## Project Overview
Building **Nearby Wells Intelligence System (NWIS)** - a production-grade AI-powered offset well knowledge platform for Oil India Limited. The system demonstrates a working framework using public Utah FORGE geothermal well data while being designed for OIL's Assam field deployment. Modular architecture enables historical data analysis, real-time drilling monitoring, predictive analytics, and live alerting.

### Key Innovation
- **Hybrid Data Strategy**: Engineering-grade content from Utah FORGE + Real Assam field geographic locations
- **Live eRTMAC Simulation**: Replay real drilling telemetry at 10-second intervals to demonstrate live data stream capabilities
- **Production-Ready Database**: WITSML-aligned schema designed from actual eRTMAC tender specifications
- **Honest Framework**: Public analogue data mapped to real field coordinates - demonstrating capabilities without false claims

---

## Data Strategy

### Utah FORGE Wells (Engineering Content Layer)
**Source**: 5 Utah FORGE geothermal wells - public, high-quality drilling data
- **Well 1**: 56-32 (Daily Drilling Reports + EOWR)
- **Well 2**: 78B-32 (Daily Drilling Reports + EOWR with appendices)
- **Well 3**: Data in well_3/
- **Well 4**: Data in well_4/
- **Well 5**: Data in well_5/
- **Active Well (Live Replay)**: 16A(78)-32 - 10-second interval telemetry CSV

**Why Utah FORGE**:
- Publicly available (no confidentiality issues for hackathon demo)
- High-quality drilling data with realistic physics correlations
- Comprehensive WCR/DDR reports for document extraction testing
- Real drilling incidents for NPT prediction training

### Assam Field Locations (Geographic Layer)
**Target Fields** (Real OIL India coordinates - for map visualization only):
- Nahorkatiya: ~27.29°N, 95.33°E
- Moran: ~27.28°N, 95.16°E
- Digboi: ~27.38°N, 95.62°E
- Baghjan: ~27.xx°N, 95.xx°E (to be mapped)
- Rudrasagar: ~27.xx°N, 95.xx°E (to be mapped)

**Mapping Strategy**:
```
Utah FORGE Well → Assam Field Location Mapping
----------------------------------------------
56-32         → Nahorkatiya Field (Well NH-001)
78B-32        → Moran Field (Well MR-002)
16A(78)-32    → Digboi Field (Well DG-003) [ACTIVE WELL]
Well_3        → Baghjan Field (Well BG-004)
Well_4        → Rudrasagar Field (Well RD-005)
```

**Disclosure Approach**: 
- Map UI shows wells at real Assam coordinates
- Well detail cards display: "Engineering data from Utah FORGE analogue well [original ID]"
- Clear attribution that framework uses public geothermal data to demonstrate capabilities

### Live eRTMAC Data Stream Simulation
**Active Well**: 16A(78)-32 (mapped to Digboi Field DG-003)
**Data Source**: `16A(78)-32_time_data_10s_intervals_standard.csv`
**Replay Engine**: Python/FastAPI WebSocket server

**Telemetry Parameters** (from CSV):
- Date/Time (timestamp)
- Bit Depth (MD & TVD)
- Bit RPM
- Weight on Bit (WOB)
- Rate of Penetration (ROP)
- Hookload
- Pump Pressure (SPP)
- Flow In Rate
- Differential Pressure
- Top Drive RPM & Torque
- Mud Temperature
- Downhole Torque
- Inclination & Azimuth
- Gamma (MWD)
- Mechanical Specific Energy (MSE)
- Rig State & Mode

**Replay Mechanism**:
1. Load CSV file on server startup
2. WebSocket endpoint: `/api/v1/live/well/{well_id}/telemetry`
3. Iterate through CSV rows, emit at 10-second intervals
4. Simulate real-time drilling: Feb 2021 timestamps → Current time offset
5. Loop or stop at end (configurable)

---

## Development Philosophy

### Modular Development Approach
- **Independent Module Development**: Each module built separately by team members
- **Integration-First Planning**: High-level implementation plans maintained for all modules during any single module's development
- **Data-Centric Architecture**: Database schema serves as the integration backbone
- **Production-Grade Standards**: Focus on correctness, impact, and uniqueness for Oil India Limited deployment

### Documentation Strategy
- Each module has its own `plan.md` file in its respective directory
- Cross-module dependencies documented in high-level plans
- Database schema evolution tracked across all modules
- eRTMAC tender document guides parameter selection

---

## Database Schema (eRTMAC-Aligned)

### Core Design Principles
- **WITSML Compliance**: Field names and structures align with eRTMAC tender specifications
- **Time-Series Optimization**: Efficient storage for 10-second interval telemetry
- **Extensibility**: Support for future sensors and calculated parameters
- **Relational Integrity**: Foreign keys maintain data consistency
- **Audit Trail**: Track data provenance and modifications

### Schema Overview (11 Tables)

#### 1. `wells` - Well Master Data
```sql
well_id (PK, UUID)
well_name (VARCHAR, e.g., "DG-003")
forge_source_id (VARCHAR, e.g., "16A(78)-32") -- Original Utah FORGE ID
field_name (VARCHAR, e.g., "Digboi")
latitude (DECIMAL)
longitude (DECIMAL)
spud_date (DATE)
total_depth_md (DECIMAL) -- Measured Depth in meters
total_depth_tvdss (DECIMAL) -- True Vertical Depth Sub-Sea
status (ENUM: 'planning', 'drilling', 'completed', 'suspended')
rig_name (VARCHAR)
operator (VARCHAR, default: 'Oil India Limited')
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
```

#### 2. `drilling_telemetry` - Real-Time Drilling Parameters (eRTMAC Stream)
```sql
telemetry_id (PK, BIGINT AUTO_INCREMENT)
well_id (FK → wells.well_id)
timestamp (DATETIME, INDEXED)
bit_depth_md (DECIMAL) -- meters
bit_depth_tvdss (DECIMAL) -- meters
wob_klbs (DECIMAL) -- Weight on Bit (kilolbs)
rop_m_hr (DECIMAL) -- Rate of Penetration (m/hr)
rpm (DECIMAL) -- Bit RPM (Top Drive + Motor)
top_drive_rpm (DECIMAL)
mud_motor_rpm (DECIMAL)
torque_kNm (DECIMAL) -- Surface Torque (kN·m)
downhole_torque_kNm (DECIMAL)
spp_kPa (DECIMAL) -- Standpipe Pressure (kPa)
differential_pressure_kPa (DECIMAL)
flow_rate_lpm (DECIMAL) -- Flow In (liters/min)
mud_temp_in_c (DECIMAL)
mud_temp_out_c (DECIMAL)
hookload_klbs (DECIMAL)
block_position_m (DECIMAL)
inclination_deg (DECIMAL)
azimuth_deg (DECIMAL)
gamma_api (DECIMAL) -- Gamma Ray MWD
mse_ksi (DECIMAL) -- Mechanical Specific Energy
stick_slip_index (DECIMAL)
rig_state (VARCHAR) -- 'drilling', 'tripping', 'circulating', etc.
on_bottom (BOOLEAN)
created_at (TIMESTAMP)
```
**Indexes**: `(well_id, timestamp)`, `(well_id, bit_depth_md)`

#### 3. `formation_tops` - Geological Markers
```sql
formation_top_id (PK, INT AUTO_INCREMENT)
well_id (FK → wells.well_id)
formation_name (VARCHAR, e.g., "Barail", "Tipam")
top_depth_md (DECIMAL)
top_depth_tvdss (DECIMAL)
identified_date (DATE)
identification_method (ENUM: 'MWD', 'LWD', 'Cuttings', 'Logs')
notes (TEXT)
```

#### 4. `daily_drilling_reports` - DDR Extracted Data
```sql
ddr_id (PK, INT AUTO_INCREMENT)
well_id (FK → wells.well_id)
document_id (FK → documents.document_id)
report_date (DATE, INDEXED)
start_depth_md (DECIMAL)
end_depth_md (DECIMAL)
depth_drilled_m (DECIMAL)
drilling_hours (DECIMAL)
npt_hours (DECIMAL) -- Non-Productive Time
operations_summary (TEXT)
bit_number (INT)
bit_size_mm (DECIMAL)
mud_weight_ppg (DECIMAL)
mud_viscosity_cp (DECIMAL)
major_events (TEXT)
extracted_at (TIMESTAMP)
```

#### 5. `well_completion_reports` - WCR Extracted Data
```sql
wcr_id (PK, INT AUTO_INCREMENT)
well_id (FK → wells.well_id)
document_id (FK → documents.document_id)
completion_date (DATE)
final_td_md (DECIMAL)
casing_design (JSON) -- Array of casing strings
cement_design (JSON)
wellhead_details (JSON)
geological_summary (TEXT)
npt_summary (TEXT)
cost_summary (JSON)
extracted_at (TIMESTAMP)
```

#### 6. `incidents` - NPT Events & Drilling Problems
```sql
incident_id (PK, INT AUTO_INCREMENT)
well_id (FK → wells.well_id)
document_id (FK → documents.document_id, NULLABLE)
telemetry_start_id (FK → drilling_telemetry.telemetry_id, NULLABLE)
telemetry_end_id (FK → drilling_telemetry.telemetry_id, NULLABLE)
incident_type (ENUM: 'stuck_pipe', 'lost_circulation', 'kick', 'twist_off', 'equipment_failure', 'other')
severity (ENUM: 'low', 'medium', 'high', 'critical')
start_time (DATETIME)
end_time (DATETIME)
depth_md (DECIMAL)
npt_hours (DECIMAL)
description (TEXT)
root_cause (TEXT)
corrective_action (TEXT)
cost_impact (DECIMAL, NULLABLE)
created_at (TIMESTAMP)
```

#### 7. `documents` - Document Registry
```sql
document_id (PK, INT AUTO_INCREMENT)
well_id (FK → wells.well_id)
doc_type (ENUM: 'DDR', 'WCR', 'EOWR', 'MorningReport', 'GeologyReport', 'Other')
file_name (VARCHAR)
file_path (VARCHAR)
file_size_bytes (BIGINT)
upload_timestamp (TIMESTAMP)
page_count (INT, NULLABLE)
extraction_status (ENUM: 'pending', 'processing', 'completed', 'failed')
extracted_json_path (VARCHAR, NULLABLE)
```

#### 8. `offset_well_links` - Well Proximity Relationships
```sql
link_id (PK, INT AUTO_INCREMENT)
well_id_a (FK → wells.well_id)
well_id_b (FK → wells.well_id)
distance_km (DECIMAL)
formation_overlap_count (INT) -- Number of shared formations
similarity_score (DECIMAL) -- ML-calculated similarity (0-1)
created_at (TIMESTAMP)
```
**Unique Constraint**: `(well_id_a, well_id_b)` where `well_id_a < well_id_b`

#### 9. `alerts` - Real-Time Alert Log
```sql
alert_id (PK, BIGINT AUTO_INCREMENT)
well_id (FK → wells.well_id)
telemetry_id (FK → drilling_telemetry.telemetry_id, NULLABLE)
alert_type (ENUM: 'stuck_pipe_risk', 'lost_circulation_risk', 'abnormal_pressure', 'equipment_anomaly', 'parameter_limit')
severity (ENUM: 'info', 'warning', 'critical')
message (TEXT)
triggered_at (TIMESTAMP)
acknowledged_at (TIMESTAMP, NULLABLE)
acknowledged_by (VARCHAR, NULLABLE)
resolved_at (TIMESTAMP, NULLABLE)
```

#### 10. `predictions` - ML Model Outputs
```sql
prediction_id (PK, BIGINT AUTO_INCREMENT)
well_id (FK → wells.well_id)
model_name (VARCHAR, e.g., "stuck_pipe_rf_v1.2")
model_version (VARCHAR)
prediction_time (DATETIME)
prediction_horizon_hours (DECIMAL) -- How far ahead
predicted_event (VARCHAR)
probability (DECIMAL) -- 0-1
confidence_interval_low (DECIMAL, NULLABLE)
confidence_interval_high (DECIMAL, NULLABLE)
feature_importance (JSON) -- Top contributing features
outcome (ENUM: 'true_positive', 'false_positive', 'true_negative', 'false_negative', 'pending')
created_at (TIMESTAMP)
```

#### 11. `user_annotations` - Human Labels for ML Training
```sql
annotation_id (PK, INT AUTO_INCREMENT)
well_id (FK → wells.well_id)
telemetry_start_id (FK → drilling_telemetry.telemetry_id)
telemetry_end_id (FK → drilling_telemetry.telemetry_id)
label (VARCHAR) -- e.g., "stuck_pipe_precursor", "normal_drilling"
annotated_by (VARCHAR)
annotation_date (DATE)
notes (TEXT)
```

---

## Module Architecture

### Module 1: Historical Data Extraction & Structuring (PDF → Database)
**Status**: NOT IN REPOSITORY - Developed by team member  
**Owner**: Friend/Team Member  
**Current State**: Extraction logic exists, but database population incomplete

#### Objectives
- Extract structured data from WCR/DDR PDF documents (Utah FORGE wells)
- Populate database tables: `wells`, `daily_drilling_reports`, `well_completion_reports`, `incidents`, `formation_tops`, `documents`
- Build training dataset for Module 4 predictive models

#### Current Blocker
**Database schema was not designed → Module 1 never populated the database**

✅ **NOW RESOLVED**: Database schema defined above (11 tables, eRTMAC-aligned)

#### What Needs to Happen
1. **Document Processing Pipeline**:
   ```
   Input: PDF files from well_1/, well_2/, well_3/, well_4/, well_5/
   ↓
   OCR/Text Extraction: pdfplumber or PyMuPDF
   ↓
   NLP Parsing: spaCy/Transformers to extract:
     - Well metadata (name, location, dates)
     - Daily drilling parameters (depth, ROP, mud properties)
     - Incident descriptions (stuck pipe, lost circulation)
     - Formation tops
   ↓
   Database Population: INSERT INTO wells, daily_drilling_reports, etc.
   ↓
   Output: Populated `documents` table with extraction_status = 'completed'
   ```

2. **Utah FORGE → Assam Mapping**:
   - Map extracted well IDs to Assam field coordinates
   - Store original FORGE ID in `wells.forge_source_id`
   - Assign new well names (DG-003, NH-001, etc.)

3. **Validation**:
   - Verify extracted depths are in correct units (feet → meters conversion)
   - Check date ranges are consistent
   - Validate incident classifications

#### Integration Points
- **Provides to Module 2**: Historical baseline data for anomaly detection
- **Provides to Module 3**: Time-series drilling data for visualization
- **Provides to Module 4**: Training labels (`incidents` table) for NPT prediction
- **Provides to Module 5**: Document registry for compliance tracking

#### Technology Stack (Recommended)
- **PDF Processing**: `pdfplumber` (table extraction), `PyMuPDF` (text)
- **NLP**: `spaCy` (entity extraction), `sentence-transformers` (semantic search)
- **Database**: PostgreSQL with PostGIS extension (for geospatial queries)
- **ORM**: SQLAlchemy (Python) or Prisma (if using Node.js)

#### Action Items for Module 1 Owner
1. ✅ Use the database schema defined in current_plan.md
2. ⏳ Build ETL pipeline: PDF → JSON → Database
3. ⏳ Start with well_1 (56-32) as proof-of-concept
4. ⏳ Validate extraction accuracy with sample manual review
5. ⏳ Scale to all 5 wells

---

### Module 4: Predictive Analytics & ML (OLD - SEE UPDATED VERSION BELOW)
**Status**: NOT STARTED - High-Level Planning Only  
**Owner**: TBD  
**Priority**: MEDIUM

#### High-Level Purpose
- NPT (Non-Productive Time) prediction
- Equipment failure forecasting
- Drilling parameter optimization

#### Data Dependencies (High-Level)
- **FROM Module 1**: Historical training data, labeled incidents
- **FROM Module 2**: Real-time feature data for predictions
- **REQUIRES**:
  - Feature engineering pipeline
  - Labeled dataset for supervised learning
  - Model versioning and storage

#### Database Considerations
```
Potential Required Tables:
- training_datasets (versioned training data)
- model_registry (model metadata, versions)
- predictions (model outputs with timestamps)
- feature_store (engineered features)
- ground_truth_labels (actual outcomes for retraining)
```

#### Integration Points
- Training: Batch access to historical data
- Inference: Real-time feature access from Module 2
- Feedback loop: Prediction validation from actual outcomes

---

### Module 5: System Integration & Orchestration
**Status**: NOT STARTED - High-Level Planning Only  
**Owner**: TBD (Likely team collaboration)  
**Priority**: LOW (Final integration phase)

#### High-Level Purpose
- Connect all modules into unified system
- API gateway and service mesh
- Authentication and authorization
- System monitoring and health checks

#### Integration Architecture
```
API Gateway
    ↓
┌────────────┬──────────────┬──────────────┬──────────────┐
│  Module 1  │   Module 2   │   Module 3   │   Module 4   │
│ Historical │  Real-Time   │  Analytics   │  Predictive  │
└────────────┴──────────────┴──────────────┴──────────────┘
                           ↓
                  Unified Database Layer
```

---

## Critical Path: Database Schema Development ✅ **COMPLETED**

### Status: Schema Design and Implementation Complete

✅ **Comprehensive Database Schema Designed** (13 tables)  
✅ **SQL Creation Scripts Generated**  
✅ **Indexes and Performance Optimization Defined**  
✅ **3D Visualization Technology Stack Recommended**  
✅ **Setup Guide and Documentation Created**

### Deliverables Created

1. **DATABASE_DESIGN.md** - Complete schema documentation with:
   - 13 core tables (wells, drilling_telemetry, formation_tops, etc.)
   - Entity Relationship Diagram
   - Sample queries for all modules
   - 3D visualization data queries
   - Performance optimization guidelines

2. **VISUALIZATION_TECH_STACK.md** - Technology recommendations:
   - **Primary:** Cesium.js + deck.gl + Leaflet.js for web-based 3D
   - **Alternative:** Blender + Python API for high-fidelity presentations
   - Database-to-visualization pipeline architecture

3. **SQL Schema Files** (database/schema/):
   - `01_create_database.sql` - Database and extensions setup
   - `02_create_tables.sql` - Core tables (Part 1)
   - `03_create_tables_part2.sql` - Core tables (Part 2)
   - `04_create_indexes.sql` - All indexes and optimization

4. **SETUP_GUIDE.md** - Complete setup instructions:
   - PostgreSQL installation (Windows)
   - PostGIS configuration
   - Database creation steps
   - Initial data population
   - Backup/restore procedures
   - Troubleshooting guide

### Key Features

- **PostgreSQL 15+ with PostGIS** for geospatial queries
- **Time-series optimized** (10-second interval telemetry)
- **WITSML-aligned** field names and structures
- **3D visualization ready** with directional surveys and formation layers
- **Extensible schema** for future enhancements

### Ready for Next Steps

✅ Database design approved  
⏳ Execute SQL scripts to create database  
⏳ Build ETL pipeline for CSV data (Module 2)  
⏳ Integrate OCR extraction with documents table  
⏳ Build FastAPI backend for Module 3

---

## Development Workflow

### For Each Module Development
1. **Pre-Planning**: Review current_plan.md for cross-module dependencies
2. **Module Planning**: Create detailed `module_X/plan.md`
3. **Design Phase**: Document interfaces, data contracts, APIs
4. **Implementation**: Build module independently
5. **Integration Planning**: Update other modules' high-level plans as needed
6. **Testing**: Unit tests, integration tests with mock data
7. **Documentation**: Update current_plan.md with learnings

### Integration Checkpoints
- After each module completion, validate integration assumptions
- Update database schema if needed (with migration strategy)
- Test cross-module data flow with sample data
- Document any breaking changes or API adjustments

---

## Current Focus: Module 2 Development

### Immediate Next Steps
1. ✅ Create this current_plan.md
2. ⏳ Create `module_2/plan.md` with detailed implementation plan
3. ⏳ Request/retrieve Module 1's data output samples
4. ⏳ Design database schema based on actual data structure
5. ⏳ Begin Module 2 development with schema in mind

### Questions to Answer During Module 2 Planning
- What real-time data sources will we integrate with?
- What is the expected data frequency/volume?
- How do we handle data conflicts between real-time and historical data?
- What validation rules are needed for incoming data?
- How do we ensure WITSML compliance in real-time data?

---

## Team Coordination

### Communication Points
- **Database Schema Changes**: Notify all team members, update all module plans
- **API Contract Changes**: Document and version changes
- **Data Format Changes**: Coordinate with dependent modules
- **Integration Issues**: Escalate early, don't wait until integration phase

### Repository Structure
```
NWIS/
├── current_plan.md (this file)
├── module_1/
│   ├── plan.md (to be created by Module 1 owner)
│   ├── src/
│   └── docs/
├── module_2/
│   ├── plan.md (to be created next)
│   ├── src/
│   └── docs/
├── module_3/
│   └── plan.md (high-level, to be detailed later)
├── module_4/
│   └── plan.md (high-level, to be detailed later)
├── module_5/
│   └── plan.md (high-level, to be detailed later)
├── database/
│   ├── schema/
│   ├── migrations/
│   └── docs/
└── data/
    ├── raw/
    └── processed/
```

---

## Success Metrics

### Module-Level
- ✅ Module passes all unit tests
- ✅ Module meets functional requirements
- ✅ Module documentation is complete
- ✅ Module adheres to agreed data contracts

### Integration-Level
- ✅ Modules communicate successfully via defined interfaces
- ✅ Data flows correctly between modules
- ✅ No data loss or corruption across module boundaries
- ✅ Performance meets production requirements

### Production-Ready Criteria
- ✅ All modules integrated and tested
- ✅ System handles realistic data volumes
- ✅ Monitoring and alerting in place
- ✅ Documentation complete for deployment and operations
- ✅ Security and access controls implemented

---

## Risk Management

### Known Risks
1. **Database Schema Mismatch**: If Module 1 schema changes after Module 2 development starts
   - Mitigation: Freeze schema early, use migration scripts for changes

2. **Data Quality Issues**: Real-time data may not match historical data format
   - Mitigation: Robust validation layer in Module 2

3. **Performance Bottlenecks**: High-frequency real-time data may overwhelm database
   - Mitigation: Design with scalability in mind, use caching/buffering

4. **Integration Complexity**: Multiple independent modules may have unforeseen conflicts
   - Mitigation: Regular integration checkpoints, early testing with sample data

---

## Version History
- **v1.0** - Initial plan created (Current)
- Future updates will be tracked here as modules evolve

---

## Notes
- This is a living document - update as planning evolves
- Keep high-level plans synchronized across all module planning documents
- Database schema is the foundation - get it right first
- **Provides to Module 4**: Training labels (`incidents` table) for NPT prediction
- **Provides to Module 5**: Document registry for compliance tracking

#### Technology Stack (Recommended)
- **PDF Processing**: `pdfplumber` (table extraction), `PyMuPDF` (text)
- **NLP**: `spaCy` (entity extraction), `sentence-transformers` (semantic search)
- **Database**: PostgreSQL with PostGIS extension (for geospatial queries)
- **ORM**: SQLAlchemy (Python) or Prisma (if using Node.js)

#### Action Items for Module 1 Owner
1. ✅ Use the database schema defined in current_plan.md
2. ⏳ Build ETL pipeline: PDF → JSON → Database
3. ⏳ Start with well_1 (56-32) as proof-of-concept
4. ⏳ Validate extraction accuracy with sample manual review
5. ⏳ Scale to all 5 wells

---

### Module 2: Real-Time Data Integration & Live Replay Engine
**Status**: IN PROGRESS - Planning Phase  
**Owner**: You (Current Developer)  
**Priority**: HIGH (Database schema complete, ready to implement)

#### Objectives
- **Live eRTMAC Simulation**: Replay 16A(78)-32 CSV at 10-second intervals via WebSocket
- **Real-Time Data Ingestion**: Stream data into `drilling_telemetry` table
- **Data Validation**: Quality checks, unit conversions, anomaly flagging
- **Alert Engine**: Trigger alerts based on parameter thresholds
- **WebSocket API**: Expose live data stream to Module 3 (frontend)

#### Dependencies
- ✅ Database schema defined (drilling_telemetry table)
- ✅ CSV file available: `16A(78)-32_time_data_10s_intervals_standard.csv`
- ✅ Well metadata ready (16A(78)-32 → DG-003 mapping)

#### High-Level Implementation Plan
```
Input: 16A(78)-32_time_data_10s_intervals_standard.csv
↓
Replay Engine (Python/FastAPI):
  - Load CSV file on startup
  - Parse and validate each row
  - Convert units (feet→meters, psi→kPa, etc.)
  - Map CSV columns → drilling_telemetry schema
  - Emit via WebSocket every 10 seconds
↓
Database Layer (PostgreSQL):
  - INSERT INTO drilling_telemetry (bulk inserts every 6 rows = 1 min)
  - Trigger checks for alert conditions
↓
Alert Engine:
  - Monitor WOB > threshold → "Stuck Pipe Risk"
  - Monitor ROP drop → "Lost Circulation Risk"
  - Monitor Torque spikes → "Equipment Anomaly"
  - INSERT INTO alerts table
↓
Output: 
  - WebSocket stream: ws://localhost:8000/api/v1/live/well/DG-003/telemetry
  - REST API: GET /api/v1/wells/DG-003/telemetry?since=2024-01-01T00:00:00
```

#### Key CSV Columns → Database Mapping
| CSV Column | Database Column | Unit Conversion |
|------------|-----------------|-----------------|
| Date | timestamp | Parse datetime |
| Bit Depth | bit_depth_md | feet → meters (÷3.28084) |
| Depth Hole Total Vertical Depth | bit_depth_tvdss | feet → meters |
| Weight on Bit | wob_klbs | kilolbs (no conversion) |
| Rate of Penetration | rop_m_hr | ft/hr → m/hr (÷3.28084) |
| Top Drive RPM | top_drive_rpm | direct |
| Top Drive Torque | torque_kNm | kft-lbs → kN·m (×1.35582) |
| Pump Pressure | spp_kPa | psi → kPa (×6.89476) |
| Flow In | flow_rate_lpm | GPM → L/min (×3.78541) |
| Mud Temperature | mud_temp_in_c | °F → °C: (F-32)×5/9 |
| Hookload | hookload_klbs | kilolbs (direct) |
| Inclination | inclination_deg | degrees |
| Azimuth | azimuth_deg | degrees |
| Gamma MWD | gamma_api | API units |

#### Technology Stack
- **Backend**: Python 3.11 + FastAPI + WebSockets
- **Database**: PostgreSQL 15 + psycopg3
- **CSV Processing**: pandas for bulk load, streaming with csv module
- **Async I/O**: asyncio for concurrent WebSocket connections
- **Alert Engine**: SQL triggers + Python rule engine (simple thresholds initially)

#### Planned Components
1. **Replay Service** (`src/replay_engine.py`):
   - `ReplayEngine` class: Load CSV, iterate rows, emit events
   - Configurable playback speed (1x, 5x, 10x real-time)
   - Loop or stop at end

2. **WebSocket Handler** (`src/api/live_data.py`):
   - FastAPI WebSocket endpoint
   - Broadcast to all connected clients
   - JSON message format:
     ```json
     {
       "well_id": "DG-003",
       "timestamp": "2024-01-15T14:32:10Z",
       "bit_depth_md": 2345.6,
       "wob_klbs": 25.3,
       "rop_m_hr": 12.5,
       ...
     }
     ```

3. **Database Ingestion** (`src/services/telemetry_ingestion.py`):
   - Batch INSERT every 1 minute (6 rows)
   - Handle duplicates (ON CONFLICT DO NOTHING)
   - Log ingestion stats

4. **Alert Engine** (`src/services/alert_engine.py`):
   - Rule-based thresholds:
     - WOB > 50 klbs → "High Weight on Bit"
     - ROP < 3 m/hr for 5+ min → "Low ROP Alert"
     - Torque > 30 kNm → "High Torque"
   - INSERT INTO alerts table
   - WebSocket broadcast to alert subscribers

5. **REST API** (`src/api/telemetry.py`):
   - `GET /api/v1/wells/{well_id}/telemetry/latest` → Last 100 rows
   - `GET /api/v1/wells/{well_id}/telemetry/range?start=&end=` → Time range query
   - `GET /api/v1/wells/{well_id}/alerts` → Recent alerts

#### Integration Points
- **Consumes from Module 1**: Well metadata (`wells` table) to validate well_id
- **Provides to Module 3**: Live WebSocket stream + REST API for charts
- **Provides to Module 4**: Real-time features for ML inference
- **Provides to Module 5**: Alert stream for notification system

#### Development Phases
1. **Phase 1 (Current Sprint)**: 
   - ✅ Database schema (DONE)
   - ⏳ Load CSV and validate data
   - ⏳ Build basic replay engine (emit to console)
   
2. **Phase 2 (Next Sprint)**:
   - ⏳ FastAPI WebSocket endpoint
   - ⏳ Database ingestion (INSERT telemetry)
   - ⏳ Unit conversion utilities

3. **Phase 3 (Final Sprint)**:
   - ⏳ Alert engine (rule-based thresholds)
   - ⏳ REST API endpoints
   - ⏳ Integration testing with Module 3

---

### Module 3: Analytics & Visualization Dashboard
**Status**: NOT STARTED - High-Level Planning Only  
**Owner**: TBD  
**Priority**: MEDIUM

#### High-Level Purpose
- Real-time drilling dashboard (WebSocket-powered live charts)
- Interactive map showing nearby offset wells (Leaflet.js with Assam field locations)
- Historical trend analysis and well comparison
- Alert notification UI

#### Data Dependencies (High-Level)
- **FROM Module 1**: Historical drilling data, well metadata, formation tops
- **FROM Module 2**: Live telemetry WebSocket stream, alerts REST API
- **REQUIRES**:
  - Time-series chart data (WOB, ROP, Torque over time)
  - Geospatial well coordinates for map rendering
  - Alert notifications in real-time

#### Technology Stack (Recommended)
- **Frontend**: React/Next.js + TypeScript
- **Charts**: Recharts or Apache ECharts for time-series
- **Map**: Leaflet.js + OpenStreetMap tiles
- **WebSocket Client**: native WebSocket API or Socket.io
- **State Management**: Zustand or Redux for real-time data

#### Key UI Components
1. **Live Drilling Dashboard**:
   - Real-time line charts: WOB, ROP, RPM, Torque, SPP
   - Current depth indicator
   - Alert banner at top (red/yellow/green status)
   - Well selector dropdown

2. **Nearby Wells Map**:
   - Leaflet map centered on Assam fields
   - Well markers color-coded by status (drilling/completed/suspended)
   - Click marker → Show well card with key stats
   - Display "Data from Utah FORGE analogue" disclaimer

3. **Historical Analysis**:
   - Date range picker for historical data
   - Compare multiple wells side-by-side
   - Formation tops overlay on depth charts

4. **Alert Management**:
   - Real-time alert feed (WebSocket)
   - Filter by severity (info/warning/critical)
   - Acknowledge button

#### Database Considerations
```
Potential Required Views (for performance):
- aggregated_telemetry_1min (rollup from 10s to 1min)
- well_summary (latest stats per well)
- active_alerts (unacknowledged alerts only)
```

#### Integration Points
- Read-only access to operational database via REST APIs
- WebSocket subscription to live telemetry and alerts
- No direct database writes from frontend

---

### Module 4: Predictive Analytics & ML
**Status**: NOT STARTED - High-Level Planning Only  
**Owner**: TBD  
**Priority**: MEDIUM-HIGH (Depends on Module 1 training data)

#### High-Level Purpose
- NPT (Non-Productive Time) prediction: Stuck pipe, lost circulation, equipment failure
- Real-time risk scoring based on live telemetry
- Offset well correlation: "Well A had incident X at depth Y → Alert if similar conditions in Well B"
- Model retraining pipeline with human feedback

#### Data Dependencies (High-Level)
- **FROM Module 1**: Labeled training data (`incidents` table, `user_annotations`)
- **FROM Module 2**: Real-time telemetry for inference
- **REQUIRES**:
  - Feature engineering pipeline (rolling averages, rate of change, etc.)
  - Model versioning and storage (`predictions` table)
  - Feedback loop (actual outcomes vs predictions)

#### Potential ML Models
1. **Stuck Pipe Prediction** (Binary Classification):
   - Features: WOB, ROP, Torque, Differential Pressure, depth rate of change
   - Algorithm: Random Forest or XGBoost
   - Output: Probability of stuck pipe in next 1-4 hours

2. **Lost Circulation Prediction**:
   - Features: SPP, Flow In vs Flow Out delta, ROP, formation tops proximity
   - Algorithm: Logistic Regression or Neural Network
   - Output: Risk score (0-1)

3. **Offset Well Correlation**:
   - Compare current well trajectory + parameters to historical wells
   - Cosine similarity on feature vectors
   - Alert if similar conditions preceded NPT in offset well

#### Technology Stack (Recommended)
- **ML Framework**: scikit-learn, XGBoost, or PyTorch
- **Feature Store**: PostgreSQL `user_annotations` + engineered features table
- **Model Serving**: FastAPI endpoint or MLflow
- **Monitoring**: Track prediction accuracy, drift detection

#### Database Considerations
```
Required Tables:
- predictions (model outputs with timestamps)
- model_registry (versioned models, hyperparameters)
- feature_store (pre-computed features for fast inference)
- ground_truth_labels (actual outcomes for retraining)
```

#### Integration Points
- Training: Batch access to historical data from Module 1
- Inference: Real-time feature access from Module 2 WebSocket stream
- Feedback loop: Human annotations via Module 3 UI → retrain models
- Alerting: Predictions trigger alerts in Module 2 alert engine

---

### Module 5: Offset Well Correlation Engine
**Status**: NOT STARTED - High-Level Planning Only  
**Owner**: TBD  
**Priority**: MEDIUM (Unique differentiator for OIL)

#### High-Level Purpose
- Calculate well-to-well proximity (geographic distance)
- Identify formation overlaps (shared geological layers)
- Similarity scoring based on drilling parameters
- Query engine: "Show me wells similar to current conditions"

#### Data Dependencies
- **FROM Module 1**: Well locations, formation tops, historical telemetry
- **FROM Module 2**: Current well telemetry
- **REQUIRES**:
  - Geospatial queries (PostGIS)
  - Formation matching algorithm
  - Parameter similarity metrics

#### Key Algorithms
1. **Geographic Proximity**:
   - PostGIS `ST_Distance` for well separation
   - Populate `offset_well_links.distance_km`

2. **Formation Overlap**:
   - Match formation names across wells
   - Count shared formations → `formation_overlap_count`

3. **Parameter Similarity**:
   - Compare WOB, ROP, Torque, mud weight profiles at similar depths
   - Cosine similarity or DTW (Dynamic Time Warping)
   - Score 0-1 → `similarity_score`

#### Integration Points
- Provides to Module 3: Offset well list for UI display
- Provides to Module 4: Similar well features for ML training

---

### Module 6: System Integration & Orchestration
**Status**: NOT STARTED - High-Level Planning Only  
**Owner**: TBD (Team collaboration)  
**Priority**: LOW (Final integration phase)

#### High-Level Purpose
- API Gateway (single entry point for all services)
- Authentication & Authorization (JWT-based)
- Service health checks and monitoring
- Docker Compose orchestration

#### Integration Architecture
```
API Gateway (Kong or nginx)
    ↓
┌────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│  Module 1  │   Module 2   │   Module 3   │   Module 4   │   Module 5   │
│ Historical │  Real-Time   │  Dashboard   │  Predictive  │  Correlation │
│  Ingestion │  Replay      │  (React)     │  ML Models   │   Engine     │
└────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
                           ↓
                  PostgreSQL Database
                  (11 tables, eRTMAC-aligned)
```

---

## Critical Path: Database Schema Implementation

### Current Status
✅ **Database schema DESIGNED** (11 tables, eRTMAC-aligned)

### Next Actions (Priority Order)
1. **IMMEDIATE** (This Sprint):
   - Create PostgreSQL database schema SQL script
   - Implement migration system (Alembic or Flyway)
   - Write sample INSERT statements for validation
   - Create `well` record for DG-003 (16A(78)-32 mapping)

2. **NEXT** (Module 1 Owner):
   - Build PDF extraction pipeline
   - Populate wells, documents, daily_drilling_reports, incidents
   - Validate with sample queries

3. **THEN** (Module 2 - You):
   - Implement CSV replay engine
   - Stream data into drilling_telemetry table
   - Build alert engine

### Schema Files Structure
```
database/
├── schema/
│   ├── 01_wells.sql
│   ├── 02_drilling_telemetry.sql
│   ├── 03_formation_tops.sql
│   ├── 04_daily_drilling_reports.sql
│   ├── 05_well_completion_reports.sql
│   ├── 06_incidents.sql
│   ├── 07_documents.sql
│   ├── 08_offset_well_links.sql
│   ├── 09_alerts.sql
│   ├── 10_predictions.sql
│   ├── 11_user_annotations.sql
│   └── indexes.sql
├── migrations/
│   └── V001__initial_schema.sql
├── seeds/
│   └── well_mapping.sql (DG-003, NH-001, etc.)
└── docs/
    └── schema_design.md
```

---

## Risk Management

### Known Risks
1. **Database Performance**: High-frequency telemetry inserts may overwhelm database
   - **Mitigation**: Batch inserts (6 rows/min), partitioning by date, indexes

2. **Unit Conversion Errors**: Feet↔Meters, PSI↔kPa conversions must be exact
   - **Mitigation**: Automated tests with known values, review by domain expert

3. **CSV Data Quality**: 16A(78)-32 CSV may have missing values or outliers
   - **Mitigation**: Data validation layer, null handling, outlier detection

4. **Module 1 Delay**: PDF extraction may take longer than expected
   - **Mitigation**: Module 2 can proceed with manual well seed data

5. **Live Demo Realism**: Replayed CSV data must look convincing
   - **Mitigation**: Use real timestamp offsets, add minor randomness to avoid "perfect" patterns

---

## Success Metrics

### Database-Level
- ✅ All 11 tables created without errors
- ✅ Foreign key constraints enforced
- ✅ Indexes improve query performance (measure with EXPLAIN ANALYZE)

### Module-Level
- ✅ Module 1: 5 wells populated with metadata + 100+ DDR records
- ✅ Module 2: Live replay streams 10,000+ telemetry rows without crashes
- ✅ Module 3: Dashboard renders real-time charts at 10s refresh rate
- ✅ Module 4: ML model achieves >70% precision on NPT prediction
- ✅ Module 5: Offset well queries return results in <500ms

### Production-Ready Criteria
- ✅ System handles 6 concurrent well streams (60 rows/min total)
- ✅ Database size projections for 1 year of data documented
- ✅ Security audit passed (no SQL injection, secure WebSocket auth)
- ✅ Deployment documentation complete (Docker Compose + README)

---

## Version History
- **v1.0** - Initial plan created
- **v2.0** - Added Utah FORGE data strategy, Assam field mapping, live replay architecture, full database schema (11 tables)

---

## Notes
- This is a living document - update as planning evolves
- **Database schema is the foundation** - all modules depend on it
- Honest disclosure: "Framework demonstration with public analogue data"
- Target demo date: [TBD - Add hackathon deadline]
