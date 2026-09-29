-- NWIS Database Schema
-- Database for Real-Time Drilling Analytics and NPT Prediction

-- Drop existing tables if they exist (in reverse order of dependencies)
DROP TABLE IF EXISTS npt_events CASCADE;
DROP TABLE IF EXISTS kpi_metrics CASCADE;
DROP TABLE IF EXISTS equipment CASCADE;
DROP TABLE IF EXISTS daily_operations CASCADE;
DROP TABLE IF EXISTS telemetry_data CASCADE;
DROP TABLE IF EXISTS wells CASCADE;

-- Wells Master Table
CREATE TABLE wells (
    well_id SERIAL PRIMARY KEY,
    well_name VARCHAR(100) NOT NULL UNIQUE,
    well_type VARCHAR(50),
    spud_date DATE,
    completion_date DATE,
    planned_depth NUMERIC(10, 2),
    final_depth NUMERIC(10, 2),
    target_formation VARCHAR(100),
    location VARCHAR(200),
    operator VARCHAR(100),
    rig_name VARCHAR(100),
    well_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Telemetry Data Table (Time-series sensor data)
CREATE TABLE telemetry_data (
    telemetry_id BIGSERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(well_id),
    timestamp TIMESTAMP NOT NULL,
    
    -- Depth and Position
    bit_depth NUMERIC(10, 2),
    hole_depth NUMERIC(10, 2),
    block_position NUMERIC(10, 2),
    
    -- Drilling Parameters
    weight_on_bit NUMERIC(10, 2),
    rate_of_penetration NUMERIC(10, 2),
    rotary_rpm NUMERIC(10, 2),
    top_drive_torque NUMERIC(10, 2),
    
    -- Hydraulics
    pump_pressure NUMERIC(10, 2),
    flow_in NUMERIC(10, 2),
    return_flow NUMERIC(10, 2),
    spm NUMERIC(10, 2),
    
    -- Hookload and String
    hookload NUMERIC(10, 2),
    hookload_string NUMERIC(10, 2),
    
    -- Directional
    inclination NUMERIC(10, 4),
    azimuth NUMERIC(10, 4),
    
    -- Mud Motor
    differential_pressure NUMERIC(10, 2),
    downhole_torque NUMERIC(10, 2),
    motor_rpm NUMERIC(10, 2),
    
    -- Formation Evaluation
    gamma_ray NUMERIC(10, 2),
    
    -- Gas Detection
    gas_co2 NUMERIC(10, 2),
    gas_h2s NUMERIC(10, 2),
    
    -- Temperatures
    mud_temperature NUMERIC(10, 2),
    tool_temperature NUMERIC(10, 2),
    
    -- Performance Metrics
    mechanical_specific_energy NUMERIC(10, 2),
    mse_downhole NUMERIC(10, 2),
    mse_surface NUMERIC(10, 2),
    
    -- Operational State
    rig_state VARCHAR(50),
    rig_mode VARCHAR(50),
    on_bottom BOOLEAN,
    stick_slip NUMERIC(10, 4),
    
    -- Bit Information
    bit_diameter NUMERIC(10, 2),
    bit_revolutions NUMERIC(15, 2),
    
    -- Running Speeds
    running_speed_down NUMERIC(10, 2),
    running_speed_up NUMERIC(10, 2),
    
    -- Survey Data
    dogleg_severity NUMERIC(10, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_telemetry_well_timestamp ON telemetry_data(well_id, timestamp);
CREATE INDEX idx_telemetry_timestamp ON telemetry_data(timestamp);
CREATE INDEX idx_telemetry_bit_depth ON telemetry_data(bit_depth);

-- Daily Operations Table
CREATE TABLE daily_operations (
    daily_op_id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(well_id),
    report_date DATE NOT NULL,
    shift VARCHAR(20),
    
    -- Depth Progress
    start_depth NUMERIC(10, 2),
    end_depth NUMERIC(10, 2),
    depth_drilled NUMERIC(10, 2),
    
    -- Time Distribution (hours)
    drilling_time NUMERIC(10, 2),
    trip_time NUMERIC(10, 2),
    connection_time NUMERIC(10, 2),
    circulating_time NUMERIC(10, 2),
    reaming_time NUMERIC(10, 2),
    npt_time NUMERIC(10, 2),
    
    -- Operations Summary
    operations_summary TEXT,
    formations_drilled VARCHAR(200),
    
    -- BHA Information
    bha_number INTEGER,
    bit_number INTEGER,
    bit_type VARCHAR(100),
    bit_size NUMERIC(10, 2),
    
    -- Mud Properties
    mud_weight_in NUMERIC(10, 2),
    mud_weight_out NUMERIC(10, 2),
    mud_viscosity NUMERIC(10, 2),
    mud_ph NUMERIC(10, 2),
    
    -- Personnel
    company_man VARCHAR(100),
    toolpusher VARCHAR(100),
    
    -- Weather
    weather_conditions TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(well_id, report_date, shift)
);

-- Equipment Table
CREATE TABLE equipment (
    equipment_id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(well_id),
    equipment_type VARCHAR(50) NOT NULL, -- 'BHA', 'BIT', 'MOTOR', 'MWD', etc.
    equipment_name VARCHAR(100),
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    
    -- Installation/Removal
    run_number INTEGER,
    install_date TIMESTAMP,
    install_depth NUMERIC(10, 2),
    removal_date TIMESTAMP,
    removal_depth NUMERIC(10, 2),
    
    -- Performance
    hours_used NUMERIC(10, 2),
    footage_drilled NUMERIC(10, 2),
    performance_rating VARCHAR(20),
    
    -- Specifications (JSON for flexibility)
    specifications JSONB,
    
    -- Status
    equipment_status VARCHAR(50),
    failure_mode TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NPT Events Table
CREATE TABLE npt_events (
    npt_id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(well_id),
    event_start TIMESTAMP NOT NULL,
    event_end TIMESTAMP,
    duration_hours NUMERIC(10, 2),
    
    -- Event Classification
    npt_category VARCHAR(100), -- 'Stuck Pipe', 'Equipment Failure', 'Formation Issues', etc.
    npt_subcategory VARCHAR(100),
    severity VARCHAR(20), -- 'Minor', 'Moderate', 'Severe', 'Critical'
    
    -- Context
    depth_at_event NUMERIC(10, 2),
    operation_during_event VARCHAR(100),
    formation VARCHAR(100),
    
    -- Details
    event_description TEXT,
    root_cause TEXT,
    corrective_action TEXT,
    lessons_learned TEXT,
    
    -- Cost Impact
    estimated_cost NUMERIC(12, 2),
    
    -- Detection
    detected_by VARCHAR(50), -- 'Manual', 'System', 'AI'
    prediction_confidence NUMERIC(5, 2), -- For AI predictions
    
    -- Status
    event_status VARCHAR(50), -- 'Detected', 'In Progress', 'Resolved', 'Predicted'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- KPI Metrics Table
CREATE TABLE kpi_metrics (
    kpi_id SERIAL PRIMARY KEY,
    well_id INTEGER REFERENCES wells(well_id),
    calculation_date DATE NOT NULL,
    
    -- Time-based KPIs
    productive_time_percent NUMERIC(5, 2),
    npt_percent NUMERIC(5, 2),
    drilling_efficiency NUMERIC(5, 2),
    
    -- Performance KPIs
    avg_rop NUMERIC(10, 2),
    max_rop NUMERIC(10, 2),
    connection_time_avg NUMERIC(10, 2),
    trip_speed_avg NUMERIC(10, 2),
    
    -- Cost KPIs
    daily_cost NUMERIC(12, 2),
    cost_per_foot NUMERIC(10, 2),
    npt_cost NUMERIC(12, 2),
    
    -- Quality KPIs
    hole_quality_score NUMERIC(5, 2),
    bit_performance_score NUMERIC(5, 2),
    
    -- Predictive Indicators
    npt_risk_score NUMERIC(5, 2), -- 0-100 scale
    equipment_health_score NUMERIC(5, 2),
    
    -- Aggregated Metrics
    total_footage NUMERIC(10, 2),
    total_drilling_hours NUMERIC(10, 2),
    total_npt_hours NUMERIC(10, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(well_id, calculation_date)
);

-- Create indexes for performance
CREATE INDEX idx_daily_ops_well_date ON daily_operations(well_id, report_date);
CREATE INDEX idx_equipment_well_type ON equipment(well_id, equipment_type);
CREATE INDEX idx_npt_well_start ON npt_events(well_id, event_start);
CREATE INDEX idx_npt_category ON npt_events(npt_category);
CREATE INDEX idx_kpi_well_date ON kpi_metrics(well_id, calculation_date);

-- Create views for common queries

-- View: Latest telemetry per well
CREATE VIEW v_latest_telemetry AS
SELECT DISTINCT ON (well_id)
    well_id,
    timestamp,
    bit_depth,
    weight_on_bit,
    rate_of_penetration,
    pump_pressure,
    hookload,
    rig_state
FROM telemetry_data
ORDER BY well_id, timestamp DESC;

-- View: Daily NPT Summary
CREATE VIEW v_daily_npt_summary AS
SELECT 
    w.well_name,
    DATE(n.event_start) as event_date,
    COUNT(*) as event_count,
    SUM(n.duration_hours) as total_npt_hours,
    SUM(n.estimated_cost) as total_cost
FROM npt_events n
JOIN wells w ON n.well_id = w.well_id
WHERE n.event_status != 'Predicted'
GROUP BY w.well_name, DATE(n.event_start);

-- View: Well Performance Summary
CREATE VIEW v_well_performance AS
SELECT 
    w.well_id,
    w.well_name,
    w.final_depth,
    COUNT(DISTINCT d.report_date) as drilling_days,
    AVG(d.depth_drilled) as avg_daily_footage,
    SUM(d.npt_time) as total_npt_hours,
    AVG(k.npt_risk_score) as avg_npt_risk
FROM wells w
LEFT JOIN daily_operations d ON w.well_id = d.well_id
LEFT JOIN kpi_metrics k ON w.well_id = k.well_id
GROUP BY w.well_id, w.well_name, w.final_depth;

-- Comments
COMMENT ON TABLE wells IS 'Master table for well information';
COMMENT ON TABLE telemetry_data IS 'Time-series sensor data from drilling operations (10-second intervals)';
COMMENT ON TABLE daily_operations IS 'Daily drilling reports with operational summaries';
COMMENT ON TABLE equipment IS 'Equipment inventory and performance tracking';
COMMENT ON TABLE npt_events IS 'Non-Productive Time events - actual and predicted';
COMMENT ON TABLE kpi_metrics IS 'Calculated KPIs and performance metrics';

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO nwis_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nwis_app;
