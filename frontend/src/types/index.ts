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
  well_type: string;
  spud_date?: string;
  completion_date?: string;
  status: string;
  witsml_uid?: string;
}

export interface FormationTop {
  well_id?: string;
  formation_name: string;
  top_md_m: number;
  top_tvd_m: number;
  top_tvdss_m: number | null;
  base_tvdss_m?: number;
  thickness_m?: number;
  lithology?: string;
}

export interface DrillingEvent {
  event_id: string;
  well_id: string;
  hazard_type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  depth_md_m: number;
  tvdss_m?: number;
  formation?: string;
  description: string;
  iadc_code?: string;
  provenance?: 'OBSERVED' | 'SYNTHETIC' | 'INFERRED';
  source_doc?: string;
  date_logged?: string;
}

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

export interface DORSOffset {
  offset_well_id: string;
  offset_well_name: string;
  distance_km: number;
  omega_score: number;
  component_scores: {
    spatial: number;
    formation: number;
    depth: number;
    trajectory: number;
    hazard: number;
  };
  historical_event_count: number;
}

export interface XiCorrelationActive {
  well_id: string;
  bit_depth_md: number;
  bit_tvdss: number;
  formation: string;
  formation_top_tvdss: number;
  formation_base_tvdss: number;
  formation_thickness: number;
  xi: number;
  confidence: number;
}

export interface XiOffsetMapping {
  offset_well_id: string;
  formation: string;
  offset_top_tvdss: number;
  offset_base_tvdss: number;
  offset_thickness: number;
  mapped_equivalent_tvdss: number;
  search_window_m: number;
  correlated_events: DrillingEvent[];
  confidence: number;
  offset_mapping?: any;
  events?: any[];
  correlation_confidence?: number;
}

export interface XiCorrelationResult {
  active_well?: XiCorrelationActive;
  active_xi?: any;
  offsets: XiOffsetMapping[];
  active_well_id?: string;
  active_md_m?: number;
  status?: string;
  correlation_status?: string;
}

export interface SimulationStatus {
  is_running: boolean;
  speed_multiplier: number;
  sim_time_s: number;
  measured_depth_m: number;
  active_scenarios: Record<string, any>;
}

export interface DocumentJob {
  job_id: string;
  filename: string;
  status: 'QUEUED' | 'PARSING' | 'EXTRACTING' | 'VALIDATING' | 'COMPLETED' | 'FAILED';
  progress_pct: number;
  created_at: string;
  result_summary?: {
    formations_count: number;
    events_count: number;
    npt_hours: number;
  };
}
