-- ============================================================================
-- NWIS Core Tables Creation Script - Part 2
-- Run after 02_create_tables.sql
-- ============================================================================

-- ============================================================================
-- Table 9: alerts - Real-Time Alert Log
-- ============================================================================

CREATE TABLE alerts (
    -- Primary Key
    alert_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    telemetry_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    related_incident_id INTEGER REFERENCES incidents(incident_id),
    
    -- Alert Classification
    alert_type VARCHAR(100) NOT NULL,
    alert_category VARCHAR(50),
    severity VARCHAR(20) NOT NULL,
    
    -- Alert Content
    message TEXT NOT NULL,
    detailed_message TEXT,
    recommendations TEXT,
    
    -- Timing
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    
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
    
    -- Alert Context
    context_data JSONB,
    
    -- Alert Source
    alert_source VARCHAR(50),
    rule_id VARCHAR(100),
    model_name VARCHAR(100),
    confidence_score DECIMAL(5, 4),
    
    -- Notification Status
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at TIMESTAMP,
    notification_channels TEXT[],
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (severity IN ('info', 'warning', 'critical'))
);

COMMENT ON TABLE alerts IS 'Real-time alert log for monitoring and analytics';

-- ============================================================================
-- Table 10: predictions - ML Model Outputs
-- ============================================================================

CREATE TABLE predictions (
    -- Primary Key
    prediction_id BIGSERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    telemetry_id BIGINT REFERENCES drilling_telemetry(telemetry_id),
    
    -- Model Information
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50),
    
    -- Prediction Timing
    prediction_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prediction_horizon_hours DECIMAL(6, 2),
    
    -- Prediction Output
    predicted_event VARCHAR(200) NOT NULL,
    prediction_class INTEGER,
    prediction_value DECIMAL(12, 6),
    probability DECIMAL(7, 6) NOT NULL,
    
    -- Confidence Intervals
    confidence_interval_low DECIMAL(12, 6),
    confidence_interval_high DECIMAL(12, 6),
    confidence_level_percent DECIMAL(5, 2),
    
    -- Feature Importance
    feature_importance JSONB,
    
    -- SHAP Values
    shap_values JSONB,
    
    -- Input Features
    input_features JSONB,
    
    -- Outcome Tracking
    outcome VARCHAR(50),
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

COMMENT ON TABLE predictions IS 'ML model predictions for NPT events and drilling optimization';

-- ============================================================================
-- Table 11: user_annotations - Human Labels for ML Training
-- ============================================================================

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
    label VARCHAR(200) NOT NULL,
    label_category VARCHAR(100),
    
    -- Confidence
    annotator_confidence VARCHAR(20),
    
    -- Description
    notes TEXT,
    contextual_information TEXT,
    
    -- Annotator
    annotated_by VARCHAR(100) NOT NULL,
    annotator_role VARCHAR(100),
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

COMMENT ON TABLE user_annotations IS 'Expert labels for training and validating ML models';

-- ============================================================================
-- Table 12: directional_surveys - Wellbore Trajectory Data
-- ============================================================================

CREATE TABLE directional_surveys (
    -- Primary Key
    survey_id SERIAL PRIMARY KEY,
    
    -- Foreign Keys
    well_id UUID NOT NULL REFERENCES wells(well_id) ON DELETE CASCADE,
    
    -- Survey Station
    measured_depth_md DECIMAL(10, 3) NOT NULL,
    
    -- Survey Measurements
    inclination_deg DECIMAL(6, 3) NOT NULL,
    azimuth_deg DECIMAL(6, 3) NOT NULL,
    
    -- Calculated Coordinates
    tvd DECIMAL(10, 3),
    northing_m DECIMAL(12, 3),
    easting_m DECIMAL(12, 3),
    vertical_section_m DECIMAL(12, 3),
    
    -- 3D Coordinates
    position_3d GEOMETRY(POINTZ, 4326),
    
    -- Survey Quality
    survey_type VARCHAR(50),
    tool_type VARCHAR(100),
    survey_quality VARCHAR(20),
    
    -- Dogleg
    dogleg_severity_deg_100ft DECIMAL(6, 3),
    
    -- Survey Timing
    survey_date TIMESTAMP,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE (well_id, measured_depth_md),
    CHECK (inclination_deg >= 0 AND inclination_deg <= 180),
    CHECK (azimuth_deg >= 0 AND azimuth_deg < 360)
);

COMMENT ON TABLE directional_surveys IS 'Wellbore trajectory data for 3D visualization';

-- ============================================================================
-- Table 13: system_logs - Audit Trail
-- ============================================================================

CREATE TABLE system_logs (
    -- Primary Key
    log_id BIGSERIAL PRIMARY KEY,
    
    -- Timestamp
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Log Level
    log_level VARCHAR(20) NOT NULL,
    
    -- Source
    module_name VARCHAR(100),
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

COMMENT ON TABLE system_logs IS 'System-level audit logging and error tracking';

-- ============================================================================
-- Grant Permissions
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nwis_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nwis_app;

-- ============================================================================
-- Summary
-- ============================================================================

SELECT 'All tables created successfully!' AS status;

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
