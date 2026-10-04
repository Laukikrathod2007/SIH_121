// ============================================================================
// NWIS Frontend Types — reconciled against OUR real backends
// (modules/01_document_intelligence and modules/02_nwis_backend), not
// Prasad's original backend. Field names below match
// modules/02_nwis_backend/models/schemas.py and
// modules/01_document_intelligence/models/schemas.py exactly — our schemas
// are the source of truth.
//
// Section 3 (Physics Digital Twin / Predictive ML) types are kept from
// Prasad's original frontend UNCHANGED, because modules/03_physics_engine/
// exists in this repo but does NOT YET expose any FastAPI routes — there is
// nothing on our side yet to reconcile these shapes against. They are used
// only by the placeholder Module 03 client in services/api.ts (base URL
// http://localhost:8003) and will need real reconciliation once that
// module ships HTTP endpoints. See services/api.ts's module03 section.
// ============================================================================

// ---------------------------------------------------------------------------
// 1. Module 02 (NWIS Backend Intelligence) — /api/v2/*
// ---------------------------------------------------------------------------

export type WellType = 'Vertical' | 'J-Type' | 'S-Type' | 'Horizontal';
export type WellStatus = 'PRODUCING' | 'COMPLETED' | 'ABANDONED' | 'SUSPENDED' | 'DRILLING';
export type HazardType =
  | 'MUD_LOSS'
  | 'STUCK_PIPE'
  | 'KICK'
  | 'WELLBORE_INSTABILITY'
  | 'TORQUE_SPIKE'
  | 'CEMENTING_FAILURE';
export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type EvidenceStrength = 'HIGH' | 'MODERATE' | 'LOW' | 'INSUFFICIENT';

export interface Well {
  well_id: string;
  well_name: string;
  field: string;
  field_code: string;
  operator: string;
  surface_lat: number;
  surface_lon: number;
  kb_elevation_m: number;
  total_depth_md_m: number;
  well_type: WellType;
  spud_date?: string | null;
  completion_date?: string | null;
  status: WellStatus;
  witsml_uid?: string;
}

export interface FormationTop {
  well_id: string;
  well_name: string;
  formation_name: string;
  top_md_m: number;
  top_tvd_m: number;
  base_md_m: number;
  thickness_m: number;
  pore_pressure_gradient_ppg: number;
  lithology?: string | null;
  confidence: number;
}

export interface SurveyStation {
  md_m: number;
  inclination_deg: number;
  azimuth_deg: number;
  tvd_m: number;
  ns_m: number;
  ew_m: number;
  tvdss_m: number;
}

export interface WellTrajectory {
  well_id: string;
  well_name: string;
  method: string;
  well_type: string;
  stations: SurveyStation[];
}

export interface DrillingEvent {
  event_id: string;
  well_id: string;
  event_type: HazardType;
  severity: string; // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
  depth_start_md_m: number;
  depth_end_md_m?: number | null;
  formation?: string | null;
  raw_narrative: string;
  npt_hours: number;
  iadc_npt_code?: string | null;
  loss_rate_bbl_hr?: number | null;
  mitigation_description?: string | null;
  outcome?: string | null;
  confidence: number;
  source_document?: string | null;
  source_page?: number | null;
}

export interface EventFacets {
  hazard_type: Record<string, number>;
  formation: Record<string, number>;
  severity: Record<string, number>;
  well_id: Record<string, number>;
}

export interface EventSearchResult {
  relevance_score: number;
  event: DrillingEvent;
}

export interface EventSearchResponse {
  query: string;
  search_mode: string; // "semantic" | "keyword_fallback" (see search/knowledge_search.py)
  total_candidates: number;
  total_returned: number;
  facets: EventFacets;
  results: EventSearchResult[];
}

export interface EventStructuredResponse {
  total: number;
  total_npt_hours: number;
  facets: EventFacets;
  events: DrillingEvent[];
}

// TelemetryRecord — GET /api/v2/telemetry/{well_id}. This is depth-indexed,
// polled telemetry (well trajectory replay), NOT the 25 Hz physics digital
// twin stream — that's a different, not-yet-wired subsystem (see Section 3).
export interface TelemetryRecord {
  well_id: string;
  timestamp: string;
  depth_m: number;
  rop_m_hr: number;
  wob_klbs: number;
  rpm: number;
  torque_kn_m: number;
  standpipe_pressure_psi: number;
  flow_in_lpm: number;
  flow_out_lpm: number;
  pit_volume_bbl: number;
  mud_weight_ppg: number;
  d_exponent: number;
}

export interface DORSComponentScores {
  spatial: number;
  formation: number;
  depth: number;
  trajectory: number;
  hazard: number;
  total: number;
  distance_km: number;
  // engines/dors_engine.py::check_structural_fault_heuristic -- when this
  // fires POSSIBLE_FAULT_BOUNDARY, `total` above has already been cut to
  // 20% of its pre-penalty value (FAULT_PENALTY_FACTOR). Real backend
  // field that had no frontend type/display until this audit found it.
  structural_fault_status: 'SAME_FAULT_BLOCK' | 'POSSIBLE_FAULT_BOUNDARY' | null;
}

export interface OffsetWellRanking {
  rank: number;
  well_id: string;
  well_name: string;
  field: string;
  well_type: string;
  dors_score: number;
  component_scores: DORSComponentScores;
  formation_match: string;
  events_in_lookahead: number;
  distance_km: number;
}

export interface RiskCorridor {
  corridor_id: string;
  hazard_type: HazardType;
  depth_start_m: number;
  depth_end_m: number;
  contributing_wells: string[];
  contributing_events: string[];
  event_count: number;
  avg_npt_hours: number;
  max_severity: string;
  historical_frequency: number;
  lead_distance_m?: number | null;
  risk_level: RiskLevel;
  recommended_action: string;
  formation?: string | null;
}

export interface FourPillarConfidence {
  evidence_strength: EvidenceStrength;
  evidence_count: number;
  sensor_anomaly_score: number;
  data_quality_index: number;
  audit_status: string;
  overall_confidence: number;
}

export interface HazardRiskAssessment {
  hazard_type: HazardType;
  risk_level: RiskLevel;
  composite_score: number;
  p_history: number;
  a_sensor: number;
  m_ml: number;
  m_ml_source: string; // "trained_model_real" | "trained_model" | "heuristic_fallback"
  confidence: FourPillarConfidence;
  active_corridor?: RiskCorridor | null;
  lead_time_meters?: number | null;
  recommended_action: string;
  evidence_events: string[];
}

export interface NWISAnalysisResponse {
  active_well_id: string;
  current_depth_m: number;
  analysis_timestamp: string;
  offset_rankings: OffsetWellRanking[];
  hazard_assessments: HazardRiskAssessment[];
  active_risk_corridors: RiskCorridor[];
  formation_at_bit?: string | null;
  overall_risk_level: RiskLevel;
  alert_message?: string | null;
}

// GET /api/v2/casing/{well_id} — real data for 2 real Volve wells only
// (modules/02_nwis_backend's own CasingRecord docstring is honest that
// nothing currently populates this from module 01's extraction output;
// this is the separate real_data/real_casing_records_all.json import).
export interface CasingRecord {
  well_id: string;
  casing_size_inches: number | null;
  shoe_depth_md_m: number;
  top_of_cement_md_m: number | null;
}

// GET /api/v2/ahead_of_bit/{well_id} — 0..max_lookahead_m projection ahead
// of the bit, mapped into offset wells for forward-looking per-hazard risk
// density (Gaussian-smoothed, same sigma as DORS's own S_hazard). Real,
// working endpoint with zero prior frontend consumer before this.
export interface AheadOfBitCorridorPoint {
  depth_ahead_m: number;
  md_m: number;
  tvd_m: number;
  tvdss_m: number;
  formation: string | null;
  window_tier: 'IMMEDIATE_0_20M' | 'SHORT_TERM_20_50M' | 'LOOKAHEAD_50_200M';
  hazard_risk: Record<string, number>;
  evidence_count: number;
  evidence_event_ids: string[];
}

export interface AheadOfBitCorridor {
  active_well_id: string;
  current_md_m: number;
  current_tvd_m: number;
  current_tvdss_m: number;
  current_formation: string | null;
  points: AheadOfBitCorridorPoint[];
}

// Shape from engines/stratigraphic_correlator.py align_horizons_across_wells()
// — a dict keyed by well_id, NOT a list. See server.py's
// /stratigraphic_depth_track/{well_id} route.
export interface HorizonAlignmentEntry {
  well_name: string;
  md_m: number | null;
  tvd_m: number | null;
  tvdss_m: number | null;
  formation: string | null;
  d_strat_m: number | null; // penetration distance into the formation (TVD), not normalized
  is_active: boolean;
}

export interface StratigraphicAlignmentResponse {
  active_well_id: string;
  depth_m: number;
  formation_at_bit?: string | null;
  wells_aligned: number;
  alignment: Record<string, HorizonAlignmentEntry>;
}

export interface MapWell {
  well_id: string;
  well_name: string;
  field: string;
  lat: number;
  lon: number;
  status: string;
  well_type: string;
  total_depth_md_m: number;
  total_events: number;
  is_active: boolean;
}

// ---------------------------------------------------------------------------
// 2. Module 01 (Document Intelligence) — /api/v1/*
// ---------------------------------------------------------------------------

export type IngestJobStatus = 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
export type ValidationStatus =
  | 'PASS'
  | 'FLAGGED_LOW_CONFIDENCE'
  | 'FAILED_PHYSICS_VALIDATION'
  | 'PENDING_MANUAL_REVIEW';

export interface IngestJobResponse {
  job_id: string;
  filename: string;
  status: IngestJobStatus;
  message: string;
  submitted_at: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: IngestJobStatus;
  progress_percent: number;
  current_page: number;
  total_pages: number;
  message: string;
  document_id?: string | null;
  error?: string | null;
}

export interface ExtractedField {
  field_name: string;
  raw_text: string;
  normalized_value: any;
  unit?: string | null;
  confidence: number;
  validation_status: ValidationStatus;
  validation_note?: string | null;
  extraction_tier: string;
}

export interface DocFormationTop {
  formation_name: string;
  top_md_m?: ExtractedField | null;
  top_tvd_m?: ExtractedField | null;
  base_md_m?: ExtractedField | null;
  lithology_description?: string | null;
  confidence: number;
}

export interface DocNPTRecord {
  iadc_code?: string | null;
  description: string;
  start_time_hhmm?: string | null;
  end_time_hhmm?: string | null;
  npt_hours?: ExtractedField | null;
  depth_md_m?: ExtractedField | null;
  cost_usd_estimate?: number | null;
}

export interface DocDrillingEvent {
  event_id: string;
  event_type: string;
  severity: string;
  depth_start_md_m?: ExtractedField | number | null;
  depth_end_md_m?: ExtractedField | number | null;
  formation?: string | null;
  raw_narrative: string;
  loss_rate_bbl_hr?: ExtractedField | number | null;
  npt_hours?: ExtractedField | number | null;
  mitigation_description?: string | null;
  outcome?: string | null;
  confidence: number;
}

// One entry of DocumentExtractionResult.pages — module 01's
// models/schemas.py PageExtractionResult. Only the fields the frontend
// actually needs are declared here (the real API response carries more).
// This is what lets the PDF Evidence Viewer figure out WHICH page a given
// formation top / NPT record came from: individual FormationTop/NPTRecord
// objects don't carry a page number themselves (module 01 never attaches
// one — see DocumentIngestionPage.tsx's derivePageNumbers()), but this
// page-grouped array does, and all_formation_tops/all_npt_records are built
// by flattening these same per-page lists in page order — so page numbers
// can be reconstructed deterministically by consuming counts sequentially.
export interface DocPageResult {
  page_number: number; // 0-indexed, per BoundingBox/PageExtractionResult convention
  formation_tops: DocFormationTop[];
  npt_records: DocNPTRecord[];
  drilling_events: DocDrillingEvent[];
}

export interface DocumentExtractionResult {
  document_id: string;
  job_id: string;
  source_filename: string;
  document_type: string;
  well_name?: string | null;
  operator?: string | null;
  report_date?: string | null;
  total_pages: number;
  pages_processed: number;
  scanned_pages: number;
  template_used?: string | null;
  extraction_started_at: string;
  extraction_completed_at?: string | null;
  total_processing_time_ms: number;
  pages: DocPageResult[];
  all_formation_tops: DocFormationTop[];
  all_npt_records: DocNPTRecord[];
  all_drilling_events: DocDrillingEvent[];
  cloud_fallback_pages_count: number;
  cloud_fallback_providers_used: string[];
  total_npt_hours: number;
  validation_status: ValidationStatus;
  overall_confidence: number;
  flagged_fields_count: number;
  physics_violations_count: number;
  witsml_compliant: boolean;
  reviewed: boolean;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_decision?: string | null;
  review_notes?: string | null;
  field_annotations: any[];
}

export interface ReviewQueueItem {
  document_id: string;
  source_filename: string;
  well_name?: string | null;
  operator?: string | null;
  validation_status: ValidationStatus;
  overall_confidence: number;
  physics_violations_count: number;
  cloud_fallback_pages_count: number;
  extraction_completed_at?: string | null;
}

export interface HealthComponentM01 {
  status: string;
  required: boolean;
  [key: string]: any;
}

export interface HealthResponseM01 {
  status: 'healthy' | 'unhealthy';
  components: {
    pymupdf: HealthComponentM01;
    docling: HealthComponentM01;
    spacy: HealthComponentM01;
    cloud_fallback: HealthComponentM01;
    auth: HealthComponentM01;
  };
  jobs_in_queue: number;
}

export interface HealthResponseM02 {
  service: string;
  version: string;
  status: 'healthy' | 'degraded';
  data_store: Record<string, any>;
  engines: string[];
  auth: {
    status: string;
    role: string;
    rate_limiting: { enabled: boolean; max_requests: number; window_seconds: number };
  };
}

// ---------------------------------------------------------------------------
// 3. Module 03 (Physics Digital Twin / Predictive ML) — NOT YET WIRED
// ---------------------------------------------------------------------------
// modules/03_physics_engine/ is being ported in a parallel effort and has no
// FastAPI routes exposed yet. These types are kept as-is from Prasad's
// original frontend purely so the existing UI code (LiveDrillingPage,
// SimulatorPage, RiskPredictionPage, AlertsAdvisoryPage) keeps compiling
// against a placeholder client (services/api.ts's `m03` axios instance,
// base URL VITE_M03_API_BASE / http://localhost:8003). None of these calls
// will succeed until module 03 ships real HTTP/WS endpoints — see
// services/api.ts for the honest "not yet wired" comments on each function.
// ---------------------------------------------------------------------------

export interface TelemetryData {
  timestamp: string;
  sim_time_s?: number;
  measured_depth_m: number;
  tvd_m: number;
  tvdss_m: number;
  formation: string;
  xi: number;
  rop_m_hr: number;
  wob_kn: number;
  rpm: number;
  torque_knm: number;
  flow_in_lpm: number;
  flow_out_lpm: number;
  delta_flow: number;
  standpipe_pressure_bar: number;
  bottomhole_pressure_bar: number;
  pore_pressure_bar: number;
  fracture_pressure_bar: number;
  ecd_gcc: number;
  pit_volume_m3: number;
  pit_volume_rate_m3_min: number;
  mse_mpa: number;
  stick_slip_index: number;
  overpull_kn: number;
  cuttings_concentration: number;
  quality: 'GOOD' | 'DEGRADED' | 'FAULT';
  provenance?: string;
}

export interface RecommendedAction {
  action_id: string;
  title: string;
  steps: string[];
  urgency: 'IMMEDIATE' | 'HIGH' | 'MEDIUM';
}

export interface AlertAdvisory {
  alert_id: string;
  well_id: string;
  hazard_type: string;
  severity: 'ADVISORY' | 'WARNING' | 'CRITICAL' | 'CLEARED';
  measured_depth_m: number;
  formation: string;
  headline: string;
  causal_evidence_chain: string[];
  recommended_action: RecommendedAction;
  status: 'DETECTED' | 'ACKNOWLEDGED' | 'MITIGATED' | 'CLEARED';
  created_at: string;
}

export interface RiskEvaluation {
  well_id: string;
  measured_depth_m: number;
  fused_hazard_scores: Record<string, number>;
  overall_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  isolation_forest_anomaly?: {
    is_anomaly: boolean;
    anomaly_score: number;
    severity: string;
  };
  xgboost_predictions?: Record<string, number>;
  rule_triggers?: string[];
  alerts?: AlertAdvisory[];
}

export interface SimulationStatus {
  is_running: boolean;
  speed_multiplier: number;
  sim_time_s: number;
  measured_depth_m: number;
  active_scenarios: Record<string, any>;
}
