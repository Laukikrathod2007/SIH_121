/**
 * Typed client for the unified NWIS backend (/api/v1, proxied by Vite to :8008).
 * Every screen talks to the backend only through this file.
 */

export const API = '/api/v1';

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type Hazard =
  | 'MUD_LOSS'
  | 'STUCK_PIPE'
  | 'KICK'
  | 'WELLBORE_INSTABILITY'
  | 'TORQUE_SPIKE'
  | 'CEMENTING_FAILURE';

export interface Well {
  well_id: string;
  well_name: string;
  field: string;
  surface_lat: number;
  surface_lon: number;
  kb_elevation_m: number;
  total_depth_md_m: number;
  well_type: string;
  status: string;
  spud_date?: string;
  completion_date?: string;
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
  distance_km: number;
  in_radius: boolean;
  is_active: boolean;
  total_events: number;
  npt_hours: number;
  events_by_type: Record<string, number>;
}

export interface NearbyResponse {
  center_well_id: string;
  center: { lat: number; lon: number };
  radius_km: number;
  total: number;
  in_radius: number;
  wells: MapWell[];
}

export interface DrillingEvent {
  event_id: string;
  well_id: string;
  event_type: Hazard;
  severity: Severity;
  depth_start_md_m: number;
  depth_end_md_m?: number | null;
  formation?: string | null;
  raw_narrative: string;
  npt_hours: number;
  loss_rate_bbl_hr?: number | null;
  mitigation_description?: string | null;
  outcome?: string | null;
  confidence: number;
  provenance_tier: string;
  source_document?: string | null;
  source_page?: number | null;
}

export interface FormationTop {
  formation_name: string;
  top_md_m: number;
  top_tvd_m: number;
  base_md_m?: number | null;
  thickness_m?: number | null;
  pore_pressure_gradient_ppg?: number | null;
  lithology?: string | null;
}

export interface CasingString {
  casing_size: string;
  hole_size: string;
  top_md_m: number;
  shoe_md_m: number;
  set_in_formation: string;
  purpose: string;
  cement_top_md_m: number;
  source_document: string;
}

export interface MudInterval {
  formation: string;
  from_md_m: number;
  to_md_m: number;
  mud_type: string;
  mud_weight_ppg: number;
  pore_pressure_ppg: number;
  overbalance_ppg: number;
}

export interface WellProfile {
  well: Well;
  trajectory_summary: { stations: number; max_inclination_deg: number; td_tvd_m: number | null; horizontal_displacement_m: number | null };
  formations: FormationTop[];
  casing_program: CasingString[];
  mud_program: MudInterval[];
  events: DrillingEvent[];
  total_npt_hours: number;
  lessons: { event_id: string; event_type: Hazard; depth_m: number; formation?: string; mitigation: string; outcome?: string; source_document?: string; source_page?: number }[];
  documents: string[];
}

export interface Station { md_m: number; inclination_deg: number; azimuth_deg: number; tvd_m: number; ns_m: number; ew_m: number; tvdss_m: number }

export interface EvidenceItem {
  event_id: string;
  well_id: string;
  well_name: string;
  event_type: Hazard;
  severity: Severity;
  depth_m: number;
  formation?: string;
  narrative: string;
  mitigation?: string;
  outcome?: string;
  npt_hours?: number;
  source_document?: string;
  source_page?: number;
}

export interface Alert {
  alert_id: string;
  status: 'ACTIVE' | 'ACKNOWLEDGED';
  well_id: string;
  hazard_type: Hazard;
  severity: Severity;
  title: string;
  message: string;
  depth_m: number;
  formation_at_bit?: string;
  zone?: { from_m: number; to_m: number } | null;
  lead_distance_m?: number | null;
  risk_score: number;
  score_breakdown: { offset_history: number; live_sensors: number; model: number; model_source: string };
  offset_wells: string[];
  evidence: EvidenceItem[];
  recommendation: {
    summary: string;
    offset_well_practice: { action: string; from_well: string; outcome?: string; source_document?: string; source_page?: number }[];
  };
  created_at: string;
  updated_at: string;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  ack_note?: string | null;
  source: string;
}

export interface ReplayTick {
  tick: number;
  well_id: string;
  depth_m: number;
  formation_at_bit?: string | null;
  overall_risk_level: string;
  alert_message?: string | null;
  hazard_summary: { hazard_type: Hazard; risk_level: string; composite_score: number; m_ml_source: string }[];
  alerts: Pick<Alert, 'alert_id' | 'hazard_type' | 'severity' | 'title' | 'message' | 'lead_distance_m' | 'offset_wells'>[];
  corridors_ahead: { hazard_type: Hazard; from_m: number; to_m: number; lead_distance_m: number | null; wells: string[]; event_count: number }[];
  top_offsets: { well_id: string; well_name: string; distance_km: number; score: number }[];
}

export interface AskSource extends Omit<EvidenceItem, 'depth_m'> {
  ref: number;
  relevance: number;
  depth_m: number | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  statements: { text: string; refs: number[] }[];
  interpreted: { hazards: Hazard[]; formation: string | null; depth_m: number | null; well_id: string | null; nearby_of: string | null };
  search_mode: string;
  confidence: { level: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE'; reason: string };
  wells: string[];
  sources: AskSource[];
}

export interface DepthTrackRow {
  well_id: string;
  well_name?: string;
  [k: string]: unknown;
}

export interface DocumentResult {
  document_id: string;
  job_id: string;
  source_filename: string;
  document_type?: string;
  well_name?: string | null;
  operator?: string | null;
  total_pages?: number;
  overall_confidence?: number;
  validation_status?: string;
  reviewed: boolean;
  review_decision?: string | null;
  events_count: number;
  formations_count: number;
  npt_count: number;
  processing_time_ms?: number;
  extraction_completed_at?: string;
}

export interface Job {
  job_id: string;
  filename: string;
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | string;
  progress_percent: number;
  current_page: number;
  total_pages: number;
  message: string;
  document_id?: string | null;
  error?: string | null;
  submitted_at?: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...init,
      headers: init?.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json', ...(init?.headers || {}) } : init?.headers,
    });
  } catch {
    throw new ApiError(0, 'Cannot reach the NWIS backend. Is it running on port 8008?');
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const q = (params: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') s.set(k, String(v));
  });
  const str = s.toString();
  return str ? `?${str}` : '';
};

export const api = {
  health: () => req<{ status: string; data_store: { wells: number; events: number; active_well_id: string } }>('/health'),
  wells: () => req<Well[] | { wells: Well[] }>('/wells').then((r) => (Array.isArray(r) ? r : r.wells)),
  nearby: (wellId: string, radiusKm: number) => req<NearbyResponse>(`/map/wells/nearby/${wellId}${q({ radius_km: radiusKm })}`),
  profile: (wellId: string) => req<WellProfile>(`/wells/${wellId}/profile`),
  trajectory: (wellId: string) => req<{ well_id: string; stations: Station[] }>(`/trajectory/${wellId}`),
  depthTrack: (wellId: string, depth: number, topN = 5) =>
    req<{ active_well_id: string; depth_m: number; formation_at_bit: string | null; alignment: DepthTrackRow[] }>(
      `/stratigraphic_depth_track/${wellId}${q({ depth, top_n: topN })}`,
    ),
  offsets: (wellId: string, depth: number, topN = 8) => req<any>(`/offset_rank/${wellId}${q({ depth, top_n: topN })}`),
  analyze: (wellId: string, depth: number) => req<any>(`/analyze/${wellId}${q({ depth })}`),
  events: (params: { hazard_type?: string; formation?: string; min_severity?: string; depth_min?: number; depth_max?: number } = {}) =>
    req<any>(`/events${q(params)}`).then((r) => (Array.isArray(r) ? r : r.events ?? []) as DrillingEvent[]),
  search: (params: { query: string; hazard_type?: string; formation?: string; min_severity?: string; well_id?: string; top_n?: number }) =>
    req<{ search_mode: string; total_candidates: number; facets: Record<string, Record<string, number>>; results: { relevance_score: number; event: DrillingEvent }[] }>(
      `/events/search${q(params)}`,
    ),
  facets: () => req<{ total: number; facets: Record<string, Record<string, number>> }>('/events/facets'),
  ask: (body: { question: string; well_id?: string; depth_m?: number; radius_km?: number }) =>
    req<AskResponse>('/knowledge/ask', { method: 'POST', body: JSON.stringify(body) }),

  alerts: (params: { well_id?: string; status?: string } = {}) => req<{ total: number; active: number; alerts: Alert[] }>(`/alerts${q(params)}`),
  evaluateAlerts: (wellId: string, depth: number) => req<{ alerts_raised_or_updated: Alert[]; overall_risk_level: string }>(`/alerts/evaluate/${wellId}${q({ depth })}`, { method: 'POST' }),
  acknowledge: (alertId: string, user: string, note?: string) =>
    req<Alert>(`/alerts/${alertId}/acknowledge`, { method: 'POST', body: JSON.stringify({ user, note }) }),
  clearAlerts: (wellId?: string) => req<{ cleared: number }>(`/alerts${q({ well_id: wellId })}`, { method: 'DELETE' }),

  evidenceUrl: (sourceDocument: string, page?: number | null) =>
    `${API}/evidence/document${q({ name: sourceDocument })}${page ? `#page=${page}` : ''}`,
  replayUrl: (wellId: string, opts: { start?: number; end?: number; ticks?: number; tickSeconds?: number }) =>
    `${API}/live/replay/${wellId}${q({ start_depth_m: opts.start, end_depth_m: opts.end, n_ticks: opts.ticks, tick_seconds: opts.tickSeconds })}`,

  jobs: () => req<Job[]>('/documents/jobs'),
  job: (id: string) => req<Job>(`/documents/jobs/${id}`),
  results: () => req<{ total_results: number; results: DocumentResult[] }>('/documents/results'),
  result: (docId: string) => req<any>(`/documents/results/${docId}`),
  ingest: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return req<{ job_id: string; filename: string; status: string; message: string }>('/documents/ingest', { method: 'POST', body: fd });
  },
  samples: () => req<{ samples: { name: string; size_kb: number }[] }>('/documents/samples'),
  ingestSample: (name: string) => req<{ job_id: string }>(`/documents/samples/${encodeURIComponent(name)}/ingest`, { method: 'POST' }),
  reviewQueue: () => req<{ total: number; queue: any[] }>('/documents/review/queue'),
  reviewDecision: (docId: string, reviewer: string, decision: 'approved' | 'rejected', notes?: string) =>
    req<any>(`/documents/review/${docId}/decision`, { method: 'POST', body: JSON.stringify({ reviewer, decision, notes }) }),
  documentFileUrl: (docId: string, page?: number) => `${API}/documents/${docId}/file${page ? `#page=${page}` : ''}`,

  // Rig sensors (physics digital twin + predictive engine)
  simStatus: () => req<any>('/physics/status'),
  simStart: () => req<any>('/physics/start', { method: 'POST' }),
  simPause: () => req<any>('/physics/pause', { method: 'POST' }),
  simReset: (initial_md_m = 2500) => req<any>('/physics/reset', { method: 'POST', body: JSON.stringify({ initial_md_m }) }),
  simSpeed: (speed_multiplier: number) => req<any>('/physics/speed', { method: 'POST', body: JSON.stringify({ speed_multiplier }) }),
  simScenario: (scenario_type: string, severity = 1.0, duration_s = 240) =>
    req<any>('/physics/scenario', { method: 'POST', body: JSON.stringify({ scenario_type, severity, duration_s }) }),
  simClearScenarios: () => req<any>('/physics/scenario', { method: 'DELETE' }),
  evaluate: (telemetry: any) => req<any>('/predictive/evaluate', { method: 'POST', body: JSON.stringify({ telemetry }) }),
  predictiveAlerts: (wellId: string) => req<any[]>(`/predictive/alerts/${wellId}`),
  mitigate: (well_id: string, alert_id: string) => req<any>('/predictive/alerts/mitigate', { method: 'POST', body: JSON.stringify({ well_id, alert_id }) }),
  models: () => req<any[]>('/predictive/models'),
  benchmarks: () => req<any>('/models/benchmarks'),
};
