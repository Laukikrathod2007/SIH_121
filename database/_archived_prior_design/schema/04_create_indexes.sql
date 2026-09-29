-- ============================================================================
-- NWIS Database Indexes
-- Run after 03_create_tables_part2.sql
-- ============================================================================

-- ============================================================================
-- Indexes for wells table
-- ============================================================================

CREATE INDEX idx_wells_location ON wells USING GIST(location);
CREATE INDEX idx_wells_field_name ON wells(field_name);
CREATE INDEX idx_wells_status ON wells(well_status);
CREATE INDEX idx_wells_is_active ON wells(is_active_well) WHERE is_active_well = TRUE;
CREATE INDEX idx_wells_is_offset ON wells(is_offset_well) WHERE is_offset_well = TRUE;

-- ============================================================================
-- Indexes for drilling_telemetry table
-- ============================================================================

CREATE INDEX idx_drilling_telemetry_well_time 
    ON drilling_telemetry(well_id, timestamp DESC);
CREATE INDEX idx_drilling_telemetry_depth 
    ON drilling_telemetry(well_id, bit_depth_md);
CREATE INDEX idx_drilling_telemetry_rig_state 
    ON drilling_telemetry(rig_state) WHERE rig_state IS NOT NULL;
CREATE INDEX idx_drilling_telemetry_timestamp 
    ON drilling_telemetry(timestamp DESC);

-- ============================================================================
-- Indexes for formation_tops table
-- ============================================================================

CREATE INDEX idx_formation_tops_well_depth 
    ON formation_tops(well_id, top_depth_md);
CREATE INDEX idx_formation_tops_name 
    ON formation_tops(formation_name);
CREATE INDEX idx_formation_tops_lithology 
    ON formation_tops(formation_lithology);

-- ============================================================================
-- Indexes for documents table
-- ============================================================================

CREATE INDEX idx_documents_well_type ON documents(well_id, doc_type);
CREATE INDEX idx_documents_date ON documents(document_date);
CREATE INDEX idx_documents_extraction_status ON documents(extraction_status);
CREATE INDEX idx_documents_full_text ON documents USING GIN(full_text_search);
CREATE INDEX idx_documents_hash ON documents(file_hash_sha256);

-- ============================================================================
-- Indexes for daily_drilling_reports table
-- ============================================================================

CREATE INDEX idx_ddr_well_date ON daily_drilling_reports(well_id, report_date DESC);
CREATE INDEX idx_ddr_depth ON daily_drilling_reports(well_id, end_depth_md);
CREATE INDEX idx_ddr_document ON daily_drilling_reports(document_id);

-- ============================================================================
-- Indexes for well_completion_reports table
-- ============================================================================

CREATE INDEX idx_wcr_well ON well_completion_reports(well_id);
CREATE INDEX idx_wcr_completion_date ON well_completion_reports(completion_date);
CREATE INDEX idx_wcr_document ON well_completion_reports(document_id);

-- ============================================================================
-- Indexes for incidents table
-- ============================================================================

CREATE INDEX idx_incidents_well_time ON incidents(well_id, start_time DESC);
CREATE INDEX idx_incidents_type ON incidents(incident_type);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_depth ON incidents(well_id, depth_md);
CREATE INDEX idx_incidents_unresolved ON incidents(resolved) WHERE resolved = FALSE;
CREATE INDEX idx_incidents_document ON incidents(document_id);

-- ============================================================================
-- Indexes for offset_well_links table
-- ============================================================================

CREATE INDEX idx_offset_well_links_well_a ON offset_well_links(well_id_a, distance_km);
CREATE INDEX idx_offset_well_links_well_b ON offset_well_links(well_id_b, distance_km);
CREATE INDEX idx_offset_well_links_nearby ON offset_well_links(is_nearby) WHERE is_nearby = TRUE;
CREATE INDEX idx_offset_well_links_distance ON offset_well_links(distance_km);

-- ============================================================================
-- Indexes for alerts table
-- ============================================================================

CREATE INDEX idx_alerts_well_time ON alerts(well_id, triggered_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_unacknowledged ON alerts(acknowledged) WHERE acknowledged = FALSE;
CREATE INDEX idx_alerts_active ON alerts(resolved) WHERE resolved = FALSE;
CREATE INDEX idx_alerts_type ON alerts(alert_type);

-- ============================================================================
-- Indexes for predictions table
-- ============================================================================

CREATE INDEX idx_predictions_well_time ON predictions(well_id, prediction_time DESC);
CREATE INDEX idx_predictions_model ON predictions(model_name, model_version);
CREATE INDEX idx_predictions_event ON predictions(predicted_event, probability DESC);
CREATE INDEX idx_predictions_outcome ON predictions(outcome) WHERE outcome IS NOT NULL;
CREATE INDEX idx_predictions_high_prob ON predictions(well_id, probability DESC) 
    WHERE probability >= 0.7;

-- ============================================================================
-- Indexes for user_annotations table
-- ============================================================================

CREATE INDEX idx_annotations_well_time ON user_annotations(well_id, start_time);
CREATE INDEX idx_annotations_label ON user_annotations(label);
CREATE INDEX idx_annotations_annotator ON user_annotations(annotated_by);
CREATE INDEX idx_annotations_training ON user_annotations(used_in_training) 
    WHERE used_in_training = TRUE;

-- ============================================================================
-- Indexes for directional_surveys table
-- ============================================================================

CREATE INDEX idx_surveys_well_depth ON directional_surveys(well_id, measured_depth_md);
CREATE INDEX idx_surveys_position ON directional_surveys USING GIST(position_3d);

-- ============================================================================
-- Indexes for system_logs table
-- ============================================================================

CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX idx_system_logs_level ON system_logs(log_level);
CREATE INDEX idx_system_logs_module ON system_logs(module_name);
CREATE INDEX idx_system_logs_well ON system_logs(well_id) WHERE well_id IS NOT NULL;

-- ============================================================================
-- Composite Indexes for Common Query Patterns
-- ============================================================================

-- For real-time dashboard queries
CREATE INDEX idx_telemetry_dashboard 
    ON drilling_telemetry(well_id, timestamp DESC, bit_depth_md);

-- For formation correlation queries
CREATE INDEX idx_formation_correlation 
    ON formation_tops(formation_name, well_id, top_depth_md);

-- For NPT analysis queries
CREATE INDEX idx_incidents_npt_analysis 
    ON incidents(incident_type, start_time) 
    INCLUDE (npt_hours, cost_impact_usd);

-- ============================================================================
-- Analyze Tables for Query Optimization
-- ============================================================================

ANALYZE wells;
ANALYZE drilling_telemetry;
ANALYZE formation_tops;
ANALYZE documents;
ANALYZE daily_drilling_reports;
ANALYZE well_completion_reports;
ANALYZE incidents;
ANALYZE offset_well_links;
ANALYZE alerts;
ANALYZE predictions;
ANALYZE user_annotations;
ANALYZE directional_surveys;
ANALYZE system_logs;

-- ============================================================================
-- Summary
-- ============================================================================

SELECT 'All indexes created successfully!' AS status;

SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS index_size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
