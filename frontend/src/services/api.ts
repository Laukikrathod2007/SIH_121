import axios, { AxiosInstance } from 'axios';
import {
  Well,
  FormationTop,
  DrillingEvent,
  EventSearchResponse,
  EventStructuredResponse,
  TelemetryRecord,
  OffsetWellRanking,
  RiskCorridor,
  NWISAnalysisResponse,
  StratigraphicAlignmentResponse,
  MapWell,
  IngestJobResponse,
  JobStatusResponse,
  DocumentExtractionResult,
  ReviewQueueItem,
  HealthResponseM01,
  HealthResponseM02,
  TelemetryData,
  WellTrajectory,
  RiskEvaluation,
  AlertAdvisory,
  SimulationStatus,
} from '../types';

// ============================================================================
// Two real backends + one placeholder.
//
//  - Module 01 (Document Intelligence)  -> http://localhost:8001/api/v1/*
//  - Module 02 (NWIS Backend Intel.)     -> http://localhost:8012/api/v2/*
//  - Module 03 (Physics Digital Twin)    -> http://localhost:8003 (PLACEHOLDER —
//    modules/03_physics_engine/ has no FastAPI routes exposed yet; see the
//    "MODULE 03" section at the bottom of this file.)
//
// Both real backends require an `X-API-Key` header on every route except
// health/root when NWIS_API_KEY is configured server-side (see
// modules/01_document_intelligence/api/auth.py and
// modules/02_nwis_backend/auth.py — both read `Header(default=None,
// alias="X-API-Key")` and compare with secrets.compare_digest). Configure the
// matching keys here via .env (copy .env.example -> .env):
//   VITE_M01_API_KEY=<value of NWIS_API_KEY in modules/01_document_intelligence/.env>
//   VITE_M02_API_KEY=<value of NWIS_API_KEY in modules/02_nwis_backend/.env>
// Both modules run with auth OFF (any/no key accepted) if their own
// NWIS_API_KEY is unset, which matches their documented default-dev behavior.
// ============================================================================

const M01_BASE = (import.meta.env.VITE_M01_API_BASE as string | undefined) || 'http://localhost:8001';
const M02_BASE = (import.meta.env.VITE_M02_API_BASE as string | undefined) || 'http://localhost:8012';
const M03_BASE = (import.meta.env.VITE_M03_API_BASE as string | undefined) || 'http://localhost:8003';

const M01_KEY = (import.meta.env.VITE_M01_API_KEY as string | undefined) || '';
const M02_KEY = (import.meta.env.VITE_M02_API_KEY as string | undefined) || '';
const M03_KEY = (import.meta.env.VITE_M03_API_KEY as string | undefined) || '';

function withApiKey(client: AxiosInstance, key: string) {
  client.interceptors.request.use((config) => {
    if (key) {
      config.headers = (config.headers ?? {}) as typeof config.headers;
      (config.headers as unknown as Record<string, string>)['X-API-Key'] = key;
    }
    return config;
  });
  return client;
}

const m01 = withApiKey(
  axios.create({ baseURL: `${M01_BASE}/api/v1`, timeout: 20000 }),
  M01_KEY,
);
const m02 = withApiKey(
  axios.create({ baseURL: `${M02_BASE}/api/v2`, timeout: 15000 }),
  M02_KEY,
);
// Placeholder client — see MODULE 03 section below. Kept so call sites don't
// need to change once module 03 exposes real routes; only this baseURL/key
// wiring (and the routes themselves) need to change then.
const m03 = withApiKey(
  axios.create({ baseURL: `${M03_BASE}/api/v3`, timeout: 10000 }),
  M03_KEY,
);

export const api = {
  // ==========================================================================
  // MODULE 01 — Document Intelligence (modules/01_document_intelligence)
  // Real, live-tested endpoints. See api/server.py + api/routes/*.py.
  // ==========================================================================

  /** POST /api/v1/ingest — multipart upload. Returns 202 + IngestJobResponse. */
  ingestDocument: async (file: File): Promise<IngestJobResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    // Do NOT set Content-Type manually — the browser/axios must generate the
    // multipart boundary itself, or FastAPI's UploadFile parsing breaks.
    const res = await m01.post('/ingest', formData);
    return res.data;
  },

  /** GET /api/v1/jobs/{job_id} — poll pipeline progress. */
  getJobStatus: async (jobId: string): Promise<JobStatusResponse> => {
    const res = await m01.get(`/jobs/${jobId}`);
    return res.data;
  },

  /** GET /api/v1/jobs — list all jobs in the current session. */
  listJobs: async (): Promise<{ total_jobs: number; jobs: any[] }> => {
    const res = await m01.get('/jobs');
    return res.data;
  },

  /** GET /api/v1/results/{doc_id} — full WITSML-compliant extraction result. */
  getResult: async (docId: string): Promise<DocumentExtractionResult> => {
    const res = await m01.get(`/results/${docId}`);
    return res.data;
  },

  /** GET /api/v1/results — list all processed document results on disk. */
  listResults: async (): Promise<{ total_results: number; results: any[] }> => {
    const res = await m01.get('/results');
    return res.data;
  },

  /** GET /api/v1/results/{doc_id}/benchmark — extraction quality report. */
  getExtractionBenchmark: async (docId: string): Promise<any> => {
    const res = await m01.get(`/results/${docId}/benchmark`);
    return res.data;
  },

  /** GET /api/v1/review/queue — documents awaiting human curation review. */
  getReviewQueue: async (): Promise<{ total: number; queue: ReviewQueueItem[] }> => {
    const res = await m01.get('/review/queue');
    return res.data;
  },

  /** GET /api/v1/review/{doc_id} — full detail for one document under review. */
  getReviewDetail: async (docId: string): Promise<DocumentExtractionResult> => {
    const res = await m01.get(`/review/${docId}`);
    return res.data;
  },

  /** POST /api/v1/review/{doc_id}/decision — approve/reject a flagged document. */
  submitReviewDecision: async (
    docId: string,
    body: { reviewer: string; decision: 'approved' | 'rejected'; notes?: string },
  ): Promise<any> => {
    const res = await m01.post(`/review/${docId}/decision`, body);
    return res.data;
  },

  /** POST /api/v1/review/{doc_id}/annotate — attach a field-level correction note. */
  annotateField: async (
    docId: string,
    body: { reviewer: string; field_path: string; note: string },
  ): Promise<any> => {
    const res = await m01.post(`/review/${docId}/annotate`, body);
    return res.data;
  },

  /** GET /api/v1/templates — list all learned document coordinate templates. */
  getTemplates: async (): Promise<any> => {
    const res = await m01.get('/templates');
    return res.data;
  },

  /** GET /api/v1/health — no auth required. */
  getHealthM01: async (): Promise<HealthResponseM01> => {
    const res = await m01.get('/health');
    return res.data;
  },

  /**
   * GET /api/v1/documents/{doc_id}/file — raw bytes of the ORIGINAL uploaded
   * PDF for a processed document. Powers PdfEvidenceViewer.tsx ("1-click PDF
   * proof"). responseType 'arraybuffer' so pdfjs-dist can load it directly
   * via getDocument({ data }) — an <iframe src="..."> can't carry the
   * X-API-Key header this route requires, so the bytes must be fetched
   * through this authenticated client instead.
   */
  getDocumentFile: async (docId: string): Promise<ArrayBuffer> => {
    const res = await m01.get(`/documents/${docId}/file`, { responseType: 'arraybuffer' });
    return res.data;
  },

  // ==========================================================================
  // MODULE 02 — NWIS Backend Intelligence (modules/02_nwis_backend)
  // Real, live-tested endpoints. See server.py + models/schemas.py.
  // ==========================================================================

  /** GET /api/v2/wells */
  getWells: async (field?: string, status?: string): Promise<Well[]> => {
    const res = await m02.get('/wells', { params: { field, status } });
    return res.data?.wells ?? [];
  },

  /** GET /api/v2/wells/{well_id} */
  getWell: async (wellId: string): Promise<{ well: Well; trajectory_stations: number; formation_tops: FormationTop[]; total_events: number }> => {
    const res = await m02.get(`/wells/${wellId}`);
    return res.data;
  },

  /** GET /api/v2/trajectory/{well_id} — real survey stations for the 3D trajectory viewer. */
  getTrajectory: async (wellId: string): Promise<WellTrajectory> => {
    const res = await m02.get(`/trajectory/${wellId}`);
    return res.data;
  },

  /** GET /api/v2/map/wells — for the GIS map. */
  getMapWells: async (): Promise<MapWell[]> => {
    const res = await m02.get('/map/wells');
    return res.data?.wells ?? [];
  },

  /** GET /api/v2/formations/{well_id} */
  getFormations: async (wellId: string): Promise<FormationTop[]> => {
    const res = await m02.get(`/formations/${wellId}`);
    return res.data?.formation_tops ?? [];
  },

  /** GET /api/v2/formations — all formation tops across all wells, optional name filter. */
  getAllFormations: async (formationName?: string): Promise<FormationTop[]> => {
    const res = await m02.get('/formations', { params: { formation_name: formationName } });
    return res.data?.formation_tops ?? [];
  },

  /**
   * GET /api/v2/events/search — free-text/semantic search over event
   * narratives, mitigation descriptions, and outcomes. `search_mode` in the
   * response tells you whether this was genuinely semantic
   * (sentence-transformers loaded) or a keyword-match fallback.
   */
  searchEventsSemantic: async (params: {
    query: string;
    hazard_type?: string;
    formation?: string;
    min_severity?: string;
    depth_min?: number;
    depth_max?: number;
    top_n?: number;
  }): Promise<EventSearchResponse> => {
    const res = await m02.get('/events/search', { params });
    return res.data;
  },

  /** GET /api/v2/events — structured-field filtering (no free-text ranking). */
  searchEventsStructured: async (params?: {
    hazard_type?: string;
    formation?: string;
    min_severity?: string;
    depth_min?: number;
    depth_max?: number;
  }): Promise<EventStructuredResponse> => {
    const res = await m02.get('/events', { params });
    return res.data;
  },

  /** GET /api/v2/events/{well_id} — all events for a well (Evidence Proof Modal). */
  getWellEvents: async (wellId: string): Promise<DrillingEvent[]> => {
    const res = await m02.get(`/events/${wellId}`);
    return res.data?.events ?? [];
  },

  /** GET /api/v2/telemetry/{well_id} — depth-indexed replayed telemetry (NOT the 25Hz physics twin stream). */
  getTelemetryRecords: async (wellId: string, depth: number, window: number = 300): Promise<{ latest: TelemetryRecord | null; records: TelemetryRecord[] }> => {
    const res = await m02.get(`/telemetry/${wellId}`, { params: { depth, window } });
    return res.data;
  },

  /** GET /api/v2/stratigraphic_depth_track/{well_id} — Engine 2: offset horizon alignment at current bit depth. */
  getStratigraphicDepthTrack: async (wellId: string, depth: number, topN: number = 10): Promise<StratigraphicAlignmentResponse> => {
    const res = await m02.get(`/stratigraphic_depth_track/${wellId}`, { params: { depth, top_n: topN } });
    return res.data;
  },

  /** GET /api/v2/offset_rank/{well_id} — DORS 5-factor offset well ranking. */
  getOffsetRank: async (
    wellId: string,
    depth: number,
    radiusKm: number = 25.0,
    topN: number = 10,
  ): Promise<{ active_well_id: string; formation_at_bit: string | null; rankings: OffsetWellRanking[]; dors_formula: string }> => {
    const res = await m02.get(`/offset_rank/${wellId}`, { params: { depth, radius_km: radiusKm, top_n: topN } });
    return res.data;
  },

  /** GET /api/v2/analyze/{well_id} — full NWIS intelligence analysis (DORS -> Stratigraphy -> Corridors -> 4-Pillar Confidence). */
  analyzeWell: async (
    wellId: string,
    depth: number,
    radiusKm: number = 25.0,
    mudWeightPpg: number = 9.5,
  ): Promise<NWISAnalysisResponse> => {
    const res = await m02.get(`/analyze/${wellId}`, { params: { depth, radius_km: radiusKm, mud_weight_ppg: mudWeightPpg } });
    return res.data;
  },

  /** GET /api/v2/corridors/{well_id} — historical risk corridors ahead of current bit depth. */
  getRiskCorridors: async (
    wellId: string,
    depth: number,
    hazardType?: string,
  ): Promise<{ well_id: string; formation_at_bit: string | null; total_corridors: number; corridors: RiskCorridor[] }> => {
    const res = await m02.get(`/corridors/${wellId}`, { params: { depth, hazard_type: hazardType } });
    return res.data;
  },

  /**
   * GET /api/v2/live/replay/{well_id} — Server-Sent Events stream of
   * risk/alert updates as simulated bit depth advances. A browser
   * EventSource cannot set the X-API-Key header the backend requires (this
   * is documented as a known gap directly in server.py's live_replay()
   * docstring), so this reads the stream manually via fetch + a
   * ReadableStream reader instead of the EventSource API. Returns an abort
   * function to stop the stream.
   */
  openLiveReplay: (
    wellId: string,
    params: { n_ticks?: number; tick_seconds?: number; start_depth_m?: number; end_depth_m?: number },
    onMessage: (data: any) => void,
    onError?: (err: unknown) => void,
    onDone?: () => void,
  ): (() => void) => {
    const controller = new AbortController();
    const qs = new URLSearchParams();
    if (params.n_ticks != null) qs.set('n_ticks', String(params.n_ticks));
    if (params.tick_seconds != null) qs.set('tick_seconds', String(params.tick_seconds));
    if (params.start_depth_m != null) qs.set('start_depth_m', String(params.start_depth_m));
    if (params.end_depth_m != null) qs.set('end_depth_m', String(params.end_depth_m));

    const headers: Record<string, string> = {};
    if (M02_KEY) headers['X-API-Key'] = M02_KEY;

    (async () => {
      try {
        const res = await fetch(`${M02_BASE}/api/v2/live/replay/${wellId}?${qs.toString()}`, {
          headers,
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`live/replay HTTP ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split('\n\n');
          buffer = events.pop() ?? '';
          for (const evt of events) {
            const dataLine = evt.split('\n').find((l) => l.startsWith('data: '));
            if (!dataLine) continue;
            try {
              onMessage(JSON.parse(dataLine.slice(6)));
            } catch {
              /* ignore malformed frame */
            }
          }
        }
        onDone?.();
      } catch (err) {
        if ((err as any)?.name !== 'AbortError') onError?.(err);
      }
    })();

    return () => controller.abort();
  },

  /** GET /api/v2/health — no auth required. */
  getHealthM02: async (): Promise<HealthResponseM02> => {
    const res = await m02.get('/health');
    return res.data;
  },

  // ==========================================================================
  // MODULE 03 — Physics Digital Twin & Predictive ML — NOT YET WIRED.
  //
  // modules/03_physics_engine/ is being ported into this project in a
  // parallel effort and, as of this port, exposes NO FastAPI routes — no
  // start/pause/step/reset controls, no WebSocket telemetry stream, no
  // /predictive/evaluate or /predictive/alerts/*. Every function below talks
  // to a placeholder base URL (VITE_M03_API_BASE, default
  // http://localhost:8003/api/v3) and will fail with a network error until
  // that module ships real endpoints. The call shapes/paths are kept
  // unchanged from Prasad's original frontend on purpose — once module 03
  // exposes real routes, wiring this up should be a base-URL + path fix
  // here, not a rewrite of every page that calls it (LiveDrillingPage,
  // SimulatorPage, and the physics-twin-dependent parts of
  // RiskPredictionPage / AlertsAdvisoryPage via AppContext).
  // ==========================================================================

  getSimStatus: async (): Promise<SimulationStatus> => {
    const res = await m03.get('/physics/status');
    return res.data;
  },

  startSim: async () => (await m03.post('/physics/start')).data,
  pauseSim: async () => (await m03.post('/physics/pause')).data,

  stepSim: async (): Promise<TelemetryData> => (await m03.post('/physics/step')).data,

  resetSim: async (initial_md_m: number = 2500) =>
    (await m03.post('/physics/reset', { initial_md_m })).data,

  setSimSpeed: async (speed_multiplier: number) =>
    (await m03.post('/physics/speed', { speed_multiplier })).data,

  injectScenario: async (scenario_type: string, severity: number = 1.0, duration_s?: number) =>
    (await m03.post('/physics/scenario', { scenario_type, severity, duration_s: duration_s || 180 })).data,

  clearScenarios: async () => (await m03.delete('/physics/scenario')).data,

  setOperatorInputs: async (inputs: { wob_kn?: number; rpm?: number; flow_in_lpm?: number; mud_weight_gcc?: number }) =>
    (await m03.post('/physics/operator-inputs', inputs)).data,

  getHistorian: async (limit: number = 100): Promise<TelemetryData[]> =>
    (await m03.get(`/physics/historian?limit=${limit}`)).data,

  evaluateTelemetry: async (telemetry: Record<string, any>): Promise<RiskEvaluation> => {
    const res = await m03.post('/predictive/evaluate', { telemetry });
    const d = res.data ?? {};
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
    const res = await m03.get(`/predictive/alerts/${wellId}`);
    return res.data;
  },

  mitigateAlert: async (wellId: string, alertId: string): Promise<any> => {
    const res = await m03.post('/predictive/alerts/mitigate', { well_id: wellId, alert_id: alertId });
    return res.data;
  },

  getRegisteredModels: async (): Promise<any[]> => {
    const res = await m03.get('/predictive/models');
    return res.data;
  },
};
