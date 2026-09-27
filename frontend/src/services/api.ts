import axios from 'axios';
import {
  Well,
  FormationTop,
  DrillingEvent,
  TelemetryData,
  RiskEvaluation,
  AlertAdvisory,
  DORSOffset,
  XiCorrelationResult,
  SimulationStatus,
  DocumentJob,
} from '../types';

const API_BASE = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // --- WELL INTELLIGENCE (Module 2) ---
  getWells: async (): Promise<Well[]> => {
    const res = await apiClient.get('/wells');
    return res.data;
  },

  getWell: async (wellId: string): Promise<Well> => {
    const res = await apiClient.get(`/wells/${wellId}`);
    return res.data;
  },

  getMapWells: async (): Promise<any[]> => {
    const res = await apiClient.get('/map/wells');
    return res.data;
  },

  getFormations: async (wellId: string): Promise<FormationTop[]> => {
    const res = await apiClient.get(`/formations/${wellId}`);
    return res.data?.formation_tops ?? [];
  },

  // --- CORRELATION & DORS (Module 4) ---
  getXiCorrelation: async (wellId: string, depth: number, offsetWellId?: string): Promise<any> => {
    const url = offsetWellId 
      ? `/xi_correlate/${wellId}?depth=${depth}&offset_well_id=${offsetWellId}&window_m=50`
      : `/xi_correlate/${wellId}?depth=${depth}&window_m=50`;
    const res = await apiClient.get(url);
    const data = res.data;
    if (data) {
      if (data.active_xi && !data.active_well) {
        data.active_well = {
          well_id: data.active_well_id || wellId,
          bit_depth_md: data.active_md_m || depth,
          bit_tvdss: data.active_xi.depth_tvdss_m ?? data.active_xi.depth_tvdss ?? 0,
          formation: data.active_xi.formation_name ?? '',
          formation_top_tvdss: data.active_xi.top_tvdss_m ?? data.active_xi.top_tvdss ?? 0,
          formation_base_tvdss: data.active_xi.base_tvdss_m ?? data.active_xi.base_tvdss ?? 0,
          formation_thickness: data.active_xi.thickness_m ?? data.active_xi.thickness ?? 0,
          xi: data.active_xi.xi ?? 0,
          confidence: data.active_xi.confidence ?? 0.95,
        };
      }
      if (Array.isArray(data.offsets)) {
        data.offsets = data.offsets.map((o: any) => ({
          ...o,
          offset_well_id: o.offset_well_id || o.offset_mapping?.well_id || '',
          formation: o.formation || o.offset_mapping?.formation_name || '',
          offset_top_tvdss: o.offset_top_tvdss ?? o.offset_mapping?.offset_top_tvdss_m ?? 0,
          offset_base_tvdss: o.offset_base_tvdss ?? o.offset_mapping?.offset_base_tvdss_m ?? 0,
          offset_thickness: o.offset_thickness ?? o.offset_mapping?.offset_thickness_m ?? 0,
          mapped_equivalent_tvdss: o.mapped_equivalent_tvdss ?? o.offset_mapping?.equivalent_tvdss_m ?? (depth - 50),
          search_window_m: o.search_window_m ?? 50,
          correlated_events: o.correlated_events || o.events || [],
          confidence: o.confidence ?? o.correlation_confidence ?? 0.85,
        }));
      }
    }
    return data;
  },

  getDORS: async (wellId: string, depth: number): Promise<{ well_id: string; ranked_offsets: DORSOffset[] }> => {
    const res = await apiClient.get(`/offset_rank/${wellId}?depth=${depth}&top_n=10`);
    const data = res.data;
    const rawList = data?.rankings || data?.ranked_offsets || (Array.isArray(data) ? data : []);
    const normalized: DORSOffset[] = rawList.map((r: any) => ({
      offset_well_id: r.well_id || r.offset_well_id || '',
      offset_well_name: r.well_name || r.offset_well_name || r.well_id || '',
      distance_km: r.distance_km || 0,
      omega_score: r.dors_score ?? r.omega_score ?? 0.8,
      component_scores: {
        spatial: r.component_scores?.spatial ?? 0.8,
        formation: r.component_scores?.formation ?? 0.85,
        depth: r.component_scores?.depth ?? 0.9,
        trajectory: r.component_scores?.trajectory ?? 0.75,
        hazard: r.component_scores?.hazard ?? 0.7,
      },
      historical_event_count: r.events_in_lookahead ?? r.historical_event_count ?? 0,
    }));
    return {
      well_id: data?.active_well_id || wellId,
      ranked_offsets: normalized,
    };
  },

  getAheadCorridor: async (wellId: string, depth: number): Promise<any> => {
    const res = await apiClient.get(`/corridors/ahead/${wellId}?depth=${depth}&max_lookahead_m=150`);
    return res.data;
  },

  getWellAnalysis: async (wellId: string, depth: number): Promise<any> => {
    const res = await apiClient.get(`/analyze/${wellId}?depth=${depth}`);
    return res.data;
  },

  // --- HISTORICAL KNOWLEDGE & EVENTS (Module 3) ---
  searchEvents: async (params?: {
    hazard_type?: string;
    formation?: string;
    min_severity?: string;
    depth_min?: number;
    depth_max?: number;
  }): Promise<DrillingEvent[]> => {
    const res = await apiClient.get('/events', { params });
    if (res.data && Array.isArray(res.data.events)) {
      return res.data.events;
    }
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  getWellEvents: async (wellId: string): Promise<DrillingEvent[]> => {
    const res = await apiClient.get(`/events/${wellId}`);
    if (res.data && Array.isArray(res.data.events)) {
      return res.data.events;
    }
    if (Array.isArray(res.data)) {
      return res.data;
    }
    return [];
  },

  // --- PHYSICS ENGINE & SCENARIO CONTROL (Module 5) ---
  getSimStatus: async (): Promise<SimulationStatus> => {
    const res = await apiClient.get('/physics/status');
    return res.data;
  },

  startSim: async () => {
    return (await apiClient.post('/physics/start')).data;
  },

  pauseSim: async () => {
    return (await apiClient.post('/physics/pause')).data;
  },

  stepSim: async (): Promise<TelemetryData> => {
    return (await apiClient.post('/physics/step')).data;
  },

  resetSim: async (initial_md_m: number = 2500) => {
    return (await apiClient.post('/physics/reset', { initial_md_m })).data;
  },

  setSimSpeed: async (speed_multiplier: number) => {
    return (await apiClient.post('/physics/speed', { speed_multiplier })).data;
  },

  injectScenario: async (scenario_type: string, severity: number = 1.0, duration_s?: number) => {
    return (await apiClient.post('/physics/scenario', {
      scenario_type,
      severity,
      duration_s: duration_s || 180,
    })).data;
  },

  clearScenarios: async () => {
    return (await apiClient.delete('/physics/scenario')).data;
  },

  setOperatorInputs: async (inputs: { wob_kn?: number; rpm?: number; flow_in_lpm?: number; mud_weight_gcc?: number }) => {
    return (await apiClient.post('/physics/operator-inputs', inputs)).data;
  },

  getHistorian: async (limit: number = 100): Promise<TelemetryData[]> => {
    return (await apiClient.get(`/physics/historian?limit=${limit}`)).data;
  },

  // --- PREDICTIVE ML & RISK FUSION (Module 5 & 6) ---
  evaluateTelemetry: async (telemetry: Record<string, any>): Promise<RiskEvaluation> => {
    const res = await apiClient.post('/predictive/evaluate', { telemetry });
    const d = res.data ?? {};
    // Backend returns {hazards: {lost_circulation: {score, state, contributors}}}; UI reads fused_hazard_scores.LOST_CIRCULATION.
    const hazards: Record<string, any> = d.hazards ?? {};
    const scores: Record<string, number> = {};
    const triggers: string[] = [];
    let maxAnomaly = 0;
    const rank = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 } as const;
    let overall: RiskEvaluation['overall_risk_level'] = 'LOW';
    for (const [name, h] of Object.entries(hazards)) {
      const key = name.toUpperCase();
      scores[key] = Number(h?.score ?? 0);
      const state = String(h?.state ?? 'LOW').toUpperCase() as RiskEvaluation['overall_risk_level'];
      if (state in rank && rank[state] > rank[overall]) overall = state;
      if (state !== 'LOW') triggers.push(key);
      maxAnomaly = Math.max(maxAnomaly, Number(h?.contributors?.anomaly_score ?? 0));
    }
    return {
      well_id: d.well_id,
      measured_depth_m: d.md,
      fused_hazard_scores: scores,
      overall_risk_level: overall,
      isolation_forest_anomaly: {
        is_anomaly: maxAnomaly >= 0.8,
        anomaly_score: maxAnomaly,
        severity: maxAnomaly >= 0.8 ? 'HIGH' : maxAnomaly >= 0.6 ? 'MEDIUM' : 'LOW',
      },
      rule_triggers: triggers,
      alerts: d.alerts ?? [],
    };
  },

  getAlerts: async (wellId: string): Promise<AlertAdvisory[]> => {
    const res = await apiClient.get(`/predictive/alerts/${wellId}`);
    return res.data;
  },

  mitigateAlert: async (wellId: string, alertId: string): Promise<any> => {
    const res = await apiClient.post('/predictive/alerts/mitigate', {
      well_id: wellId,
      alert_id: alertId,
    });
    return res.data;
  },

  getRegisteredModels: async (): Promise<any[]> => {
    const res = await apiClient.get('/predictive/models');
    return res.data;
  },

  // --- DOCUMENT INTELLIGENCE (Module 1) ---
  getDocumentJobs: async (): Promise<DocumentJob[]> => {
    const res = await apiClient.get('/documents/jobs');
    return res.data;
  },

  ingestDocument: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/documents/ingest', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // --- SYSTEM HEALTH ---
  getHealth: async (): Promise<any> => {
    const res = await apiClient.get('/health');
    return res.data;
  },
};
