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
  CasingRecord,
  AheadOfBitCorridor,
} from '../types';

// ============================================================================
// ONE unified backend (Backend/app/main.py, port 8000 by default) serving
// all of document intelligence (/api/v1), well/geospatial intelligence
// (/api/v2), and physics digital twin + predictive analytics (/api/v3) --
// consolidated from 3 previously independently-launched FastAPI processes
// (modules/01_document_intelligence :8001, modules/02_nwis_backend :8002,
// modules/04_physics_engine+05_predictive_analytics :8003). Evidence/PDF
// delivery (previously the standalone Node evidence-server/ on :4100) is
// now /api/evidence/* on the same origin -- see NwisMapPage.tsx.
//
// The unified backend requires an `X-API-Key` header on every data/analysis
// route except health/root/docs (see Backend/app/core/auth.py). Configure
// the matching key here via .env (copy .env.example -> .env):
//   VITE_API_KEY=<value of NWIS_API_KEY in Backend/.env>
// Auth is OFF (any/no key accepted) if NWIS_API_KEY is unset server-side,
// matching the unified backend's documented default-dev behavior.
// ============================================================================

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || 'http://localhost:8000';
const API_KEY = (import.meta.env.VITE_API_KEY as string | undefined) || '';

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
  axios.create({ baseURL: `${API_BASE}/api/v1`, timeout: 20000 }),
  API_KEY,
);
const m02 = withApiKey(
  axios.create({ baseURL: `${API_BASE}/api/v2`, timeout: 15000 }),
  API_KEY,
);
const m03 = withApiKey(
  axios.create({ baseURL: `${API_BASE}/api/v3`, timeout: 10000 }),
  API_KEY,
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

  /** GET /api/v1/results/{doc_id} — full extraction result, WITSML-aligned field naming (not a certified WITSML schema). */
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

  /**
   * GET /api/v2/map/wells — for the GIS map. Called with no params, this
   * returns ALL wells unfiltered (original behavior, unchanged) — the 2D/3D
   * map pages apply their own client-side Haversine radius filter on top of
   * this, which remains correct and is NOT redundant with the backend's
   * optional filter below (see NearbyWellsPage.tsx / GlobeMapPage.tsx).
   * The backend also now accepts an optional real hard filter
   * (centerWellId + radiusKm, Priority 2 fix) for callers that want
   * server-side filtering instead; unused by the current pages, which
   * already have a working client-side equivalent.
   */
  getMapWells: async (centerWellId?: string, radiusKm?: number): Promise<MapWell[]> => {
    const res = await m02.get('/map/wells', { params: { center_well_id: centerWellId, radius_km: radiusKm } });
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

  /**
   * GET /api/v2/casing/{well_id} — real casing records. Only 2 real Volve
   * wells have any (10 records total) — every synthetic well correctly
   * returns an empty list, not a 404 (this endpoint didn't exist until it
   * was added directly in this session; the data was already loaded in
   * data_store.py with nothing serving it).
   */
  getCasing: async (wellId: string): Promise<CasingRecord[]> => {
    const res = await m02.get(`/casing/${wellId}`);
    return res.data?.casing_records ?? [];
  },

  /** GET /api/v2/stratigraphic_depth_track/{well_id} — Engine 2: offset horizon alignment at current bit depth. */
  getStratigraphicDepthTrack: async (wellId: string, depth: number, topN: number = 10): Promise<StratigraphicAlignmentResponse> => {
    const res = await m02.get(`/stratigraphic_depth_track/${wellId}`, { params: { depth, top_n: topN } });
    return res.data;
  },

  /**
   * GET /api/v2/offset_rank/{well_id} — DORS 5-factor offset well ranking.
   * `radiusKm` is a SCORING DECAY, not a hard filter — every well is still
   * ranked and returned regardless of its value (see server.py's docstring
   * for why: several pages rely on getting the full ranked list). Pass
   * `maxDistanceKm` for a real, additive hard exclusion filter if a caller
   * specifically needs wells beyond a distance removed server-side; omit it
   * for the original unfiltered-ranking behavior (default, unchanged).
   */
  getOffsetRank: async (
    wellId: string,
    depth: number,
    radiusKm: number = 25.0,
    topN: number = 10,
    maxDistanceKm?: number,
  ): Promise<{ active_well_id: string; formation_at_bit: string | null; rankings: OffsetWellRanking[]; dors_formula: string; radius_km_is_scoring_decay_not_a_filter?: boolean }> => {
    const res = await m02.get(`/offset_rank/${wellId}`, { params: { depth, radius_km: radiusKm, top_n: topN, max_distance_km: maxDistanceKm } });
    return res.data;
  },

  /**
   * GET /api/v2/ahead_of_bit/{well_id} — 0..max_lookahead_m projected risk
   * density ahead of the bit, mapped into offset wells per step. Real,
   * working endpoint (engines/risk_corridor_engine.py's
   * compute_ahead_of_bit_corridor) with no prior frontend consumer.
   */
  getAheadOfBit: async (
    wellId: string,
    depth: number,
    maxLookaheadM: number = 200,
    stepM: number = 10,
  ): Promise<AheadOfBitCorridor> => {
    const res = await m02.get(`/ahead_of_bit/${wellId}`, {
      params: { depth, max_lookahead_m: maxLookaheadM, step_m: stepM },
    });
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
    if (API_KEY) headers['X-API-Key'] = API_KEY;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v2/live/replay/${wellId}?${qs.toString()}`, {
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
  // MODULE 03 — served by modules/04_physics_engine/api/server.py, which also
  // hosts modules/05_predictive_analytics's predictive code via a sys.path
  // import (see that file's own docstring). Real FastAPI app, real routes,
  // real WebSocket telemetry stream, real /predictive/evaluate and
  // /predictive/alerts/* — confirmed live (VITE_M03_API_BASE, default
  // http://localhost:8003/api/v3) during the end-to-end verification pass.
  // The isolation-forest/XGBoost ML pillars are typically UNFITTED_FALLBACK
  // on a fresh checkout (no trained .joblib artifacts ship by default) — the
  // rule-engine pillar is always ACTIVE. See AUDIT/02_CORE_INTEGRATION.md and
  // AUDIT/04_E2E_VERIFICATION.md.
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
