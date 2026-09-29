-- ============================================================================
-- NWIS Core Tables Creation Script
-- Run after 01_create_database.sql
-- ============================================================================

-- Set search path
SET search_path TO public;

-- ============================================================================
-- Table 1: wells - Well Master Data
-- ============================================================================

CREATE TABLE wells (
    -- Primary Key
    well_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Well Identification
    well_name VARCHAR(100) NOT NULL UNIQUE,
    well_api_number VARCHAR(50),
    forge_source_id VARCHAR(100),
    
    -- Location Data (PostGIS)
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    surface_elevation_m DECIMAL(8, 2),
    
    -- Field Information
    field_name VARCHAR(100) NOT NULL,
    basin_name VARCHAR(100),
    block_name VARCHAR(100),
    
    -- Well Classification
    well_type VARCHAR(50),
    well_status VARCHAR(50) NOT NULL DEFAULT 'planning',
    well_purpose VARCHAR(100),
    
    -- Drilling Dates
    spud_date DATE,
    completion_date DATE,
    first_production_date DATE,
    
    -- Depth Information
    total_depth_md DECIMAL(10, 2),
    total_depth_tvd DECIMAL(10, 2),
    total_depth_tvdss DECIMAL(10, 2),
    kick_off_point_md DECIMAL(10, 2),
    
    -- Rig Information
    rig_name VARCHAR(100),
    rig_contractor VARCHAR(100),
    
    -- Operator
    operator VARCHAR(100) DEFAULT 'Oil India Limited',
    operator_contact VARCHAR(200),
    
    -- Data Source Metadata
    data_source VARCHAR(50),
    data_quality_score DECIMAL(3, 2),
    is_offset_well BOOLEAN DEFAULT FALSE,
    is_active_well BOOLEAN DEFAULT FALSE,
    
    -- Audit Fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    
    -- Constraints
    CHECK (data_quality_score IS NULL OR (data_quality_score >= 0 AND data_quality_score <= 1)),
    CHECK (well_status IN ('planning', 'drilling', 'completed', 'suspended', 'abandoned'))
);

COMMENT ON TABLE wells IS 'Central registry of all wells in the NWIS system';
COMMENT ON COLUMN wells.location IS 'PostGIS GEOGRAPHY type for geospatial queries';
COMMENT ON COLUMN wells.forge_source_id IS 'Original Utah FORGE well identifier for data provenance';

-- ============================================================================
-- Table 2: drilling_telemetry - Real-Time Drilling Parameters
-- ============================================================================

CREATE TABLE drilling_telemetry (
    -- Primary Key
    telemetry_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Timestamp
    timestamp TIMESTAMP NOT NULL,
    
    -- Depth Parameters
    bit_depth_md DECIMAL(10, 3),
    bit_depth_tvd DECIMAL(10, 3),
    bit_depth_tvdss DECIMAL(10, 3),
    hole_depth_md DECIMAL(10, 3),
    block_position_m DECIMAL(10, 3),
    
    -- Drilling Parameters
    wob_klbs DECIMAL(8, 3),
    rop_m_hr DECIMAL(8, 3),
    rpm_total DECIMAL(7, 2),
    top_drive_rpm DECIMAL(7, 2),
    mud_motor_rpm DECIMAL(7, 2),
    
    -- Torque
    torque_surface_knm DECIMAL(8, 3),
    torque_downhole_knm DECIMAL(8, 3),
    
    -- Hydraulics
    spp_kpa DECIMAL(8, 2),
    differential_pressure_kpa DECIMAL(8, 2),
    flow_rate_lpm DECIMAL(8, 2),
    return_flow_percent DECIMAL(5, 2),
    total_strokes_per_min DECIMAL(6, 2),
    
    -- Mud Properties
    mud_weight_in_ppg DECIMAL(5, 2),
    mud_weight_out_ppg DECIMAL(5, 2),
    mud_temp_in_c DECIMAL(5, 2),
    mud_temp_out_c DECIMAL(5, 2),
    mud_viscosity_cp DECIMAL(6, 2),
    
    -- Hookload
    hookload_klbs DECIMAL(8, 3),
    hookload_string_klbs DECIMAL(8, 3),
    overpull_klbs DECIMAL(7, 3),
    
    -- Directional Parameters
    inclination_deg DECIMAL(6, 3),
    azimuth_deg DECIMAL(6, 3),
    dogleg_severity_deg_100ft DECIMAL(6, 3),
    
    -- Logging While Drilling
    gamma_ray_api DECIMAL(7, 2),
    resistivity_ohmm DECIMAL(8, 3),
    tool_temperature_c DECIMAL(6, 2),
    
    -- Mechanical Specific Energy
    mse_surface_ksi DECIMAL(8, 3),
    mse_downhole_ksi DECIMAL(8, 3),
    mse_total_ksi DECIMAL(8, 3),
    
    -- Gas Detection
    gas_total_percent DECIMAL(5, 3),
    gas_c1_percent DECIMAL(5, 3),
    gas_c2_percent DECIMAL(5, 3),
    gas_co2_ppm DECIMAL(7, 2),
    h2s_ppm DECIMAL(7, 2),
    
    -- Operational States
    rig_state VARCHAR(50),
    rig_mode VARCHAR(50),
    on_bottom BOOLEAN,
    autodriller_enabled BOOLEAN,
    
    -- Performance Indicators
    stick_slip_index DECIMAL(5, 3),
    running_speed_down_fpm DECIMAL(7, 2),
    running_speed_up_fpm DECIMAL(7, 2),
    
    -- Bit Information
    bit_number INTEGER,
    bit_diameter_inches DECIMAL(5, 3),
    bit_total_revolutions INTEGER,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_source VARCHAR(50) DEFAULT 'ertmac',
    
    -- Constraints
    UNIQUE (well_id, timestamp)
);

COMMENT ON TABLE drilling_telemetry IS 'High-frequency telemetry data (10-second intervals) from eRTMAC system';

-- Convert to TimescaleDB hypertable (if TimescaleDB is installed)
-- SELECT create_hypertable('drilling_telemetry', 'timestamp', 
--                          chunk_time_interval => INTERVAL '1 day',
--                          if_not_exists => TRUE);

-- ============================================================================
-- Table 3: formation_tops - Geological Formation Markers
-- ============================================================================

CREATE TABLE formation_tops (
    -- Primary Key
    formation_top_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Formation Identification
    formation_name VARCHAR(200) NOT NULL,
    formation_code VARCHAR(50),
    formation_age VARCHAR(100),
    formation_lithology VARCHAR(200),
    
    -- Depth Data
    top_depth_md DECIMAL(10, 3) NOT NULL,
    top_depth_tvd DECIMAL(10, 3),
    top_depth_tvdss DECIMAL(10, 3),
    bottom_depth_md DECIMAL(10, 3),
    bottom_depth_tvd DECIMAL(10, 3),
    thickness_md DECIMAL(10, 3),
    thickness_tvd DECIMAL(10, 3),
    
    -- Identification Method
    identified_date TIMESTAMP,
    identification_method VARCHAR(50),
    identified_by VARCHAR(100),
    
    -- Formation Properties
    porosity_percent DECIMAL(5, 2),
    permeability_md DECIMAL(8, 3),
    water_saturation_percent DECIMAL(5, 2),
    hydrocarbon_shows BOOLEAN,
    
    -- Notes
    notes TEXT,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (bottom_depth_md IS NULL OR top_depth_md < bottom_depth_md)
);

COMMENT ON TABLE formation_tops IS 'Geological formation boundaries for correlation and 3D visualization';

-- ============================================================================
-- Table 4: documents - Document Registry
-- ============================================================================

CREATE TABLE documents (
    -- Primary Key
    document_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Document Classification
    doc_type VARCHAR(50) NOT NULL,
    doc_subtype VARCHAR(100),
    
    -- File Information
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size_bytes BIGINT,
    file_hash_sha256 VARCHAR(64),
    mime_type VARCHAR(100),
    
    -- Document Dates
    document_date DATE,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- PDF Metadata
    page_count INTEGER,
    pdf_version VARCHAR(20),
    
    -- Extraction Status
    extraction_status VARCHAR(50) DEFAULT 'pending',
    extraction_started_at TIMESTAMP,
    extraction_completed_at TIMESTAMP,
    extraction_error TEXT,
    extracted_json_path VARCHAR(1000),
    
    -- OCR Status
    ocr_status VARCHAR(50),
    ocr_confidence_avg DECIMAL(5, 4),
    ocr_text_path VARCHAR(1000),
    
    -- Search
    full_text_search TSVECTOR,
    
    -- Tags
    tags TEXT[],
    
    -- Audit
    uploaded_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (file_hash_sha256),
    CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed'))
);

COMMENT ON TABLE documents IS 'Registry of all uploaded documents (PDFs, reports, logs)';

-- ============================================================================
-- Table 5: daily_drilling_reports - Extracted DDR Data
-- ============================================================================

CREATE TABLE daily_drilling_reports (
    -- Primary Key
    ddr_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(document_id),
    
    -- Report Identification
    report_date DATE NOT NULL,
    report_number VARCHAR(50),
    shift VARCHAR(20),
    
    -- Depth Progress
    start_depth_md DECIMAL(10, 3),
    end_depth_md DECIMAL(10, 3),
    depth_drilled_m DECIMAL(8, 3),
    
    -- Time Breakdown
    drilling_hours DECIMAL(5, 2),
    tripping_hours DECIMAL(5, 2),
    circulating_hours DECIMAL(5, 2),
    connection_time_hours DECIMAL(5, 2),
    npt_hours DECIMAL(5, 2),
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
    operations_summary TEXT,
    major_events TEXT,
    formation_description TEXT,
    
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
    extraction_method VARCHAR(50),
    extraction_confidence DECIMAL(3, 2),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id, report_date, shift),
    CHECK (extraction_confidence IS NULL OR (extraction_confidence >= 0 AND extraction_confidence <= 1))
);

COMMENT ON TABLE daily_drilling_reports IS 'Structured data extracted from Daily Drilling Reports';

-- ============================================================================
-- Table 6: well_completion_reports - Extracted WCR Data
-- ============================================================================

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
    
    -- Casing Design (JSON)
    casing_design JSONB,
    
    -- Cement Design
    cement_design JSONB,
    
    -- Wellhead Details
    wellhead_details JSONB,
    
    -- Formation Summary
    geological_summary TEXT,
    formation_tops JSONB,
    
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
    
    -- Extraction Metadata
    extracted_at TIMESTAMP,
    extraction_method VARCHAR(50),
    extraction_confidence DECIMAL(3, 2),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id, report_date),
    CHECK (extraction_confidence IS NULL OR (extraction_confidence >= 0 AND extraction_confidence <= 1))
);

COMMENT ON TABLE well_completion_reports IS 'Structured data from Well Completion Reports';

-- ============================================================================
-- Table 7: incidents - NPT Events and Drilling Problems
-- ============================================================================

CREATE TABLE incidents (
    -- Primary Key
    incident_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(document_id),
    telemetry_start_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    telemetry_end_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    
    -- Incident Classification
    incident_type VARCHAR(100) NOT NULL,
    incident_category VARCHAR(50),
    severity VARCHAR(20) NOT NULL,
    
    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_hours DECIMAL(8, 2),
    
    -- Location
    depth_md DECIMAL(10, 3),
    depth_tvd DECIMAL(10, 3),
    formation_name VARCHAR(200),
    
    -- NPT Impact
    npt_hours DECIMAL(8, 2),
    cost_impact_usd DECIMAL(12, 2),
    
    -- Description
    description TEXT NOT NULL,
    root_cause TEXT,
    corrective_action TEXT,
    preventive_measures TEXT,
    
    -- Operational Context
    wob_klbs DECIMAL(8, 3),
    rop_m_hr DECIMAL(8, 3),
    rpm DECIMAL(7, 2),
    torque_knm DECIMAL(8, 3),
    spp_kpa DECIMAL(8, 2),
    mud_weight_ppg DECIMAL(5, 2),
    
    -- Detection
    detected_by VARCHAR(100),
    detection_method VARCHAR(100),
    
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

COMMENT ON TABLE incidents IS 'NPT events, stuck pipe, lost circulation, and other drilling problems';

-- ============================================================================
-- Table 8: offset_well_links - Well Proximity Relationships
-- ============================================================================

CREATE TABLE offset_well_links (
    -- Primary Key
    link_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id_a UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    well_id_b UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Spatial Relationship
    distance_km DECIMAL(10, 3) NOT NULL,
    bearing_deg DECIMAL(6, 3),
    
    -- Geological Similarity
    formation_overlap_count INTEGER DEFAULT 0,
    formation_similarity_score DECIMAL(3, 2),
    
    -- Operational Similarity
    similarity_score DECIMAL(3, 2),
    similarity_features JSONB,
    
    -- Correlation Flags
    is_nearby BOOLEAN GENERATED ALWAYS AS (distance_km <= 10.0) STORED,
    is_analog BOOLEAN DEFAULT FALSE,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id_a, well_id_b),
    CHECK (well_id_a < well_id_b),
    CHECK (similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1)),
    CHECK (formation_similarity_score IS NULL OR (formation_similarity_score >= 0 AND formation_similarity_score <= 1))
);

COMMENT ON TABLE offset_well_links IS 'Pre-calculated relationships between wells for fast nearby well queries';

-- Continue in next file (03_create_tables_part2.sql)
