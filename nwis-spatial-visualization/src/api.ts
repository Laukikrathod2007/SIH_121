import type { SurveyStation, Well, WellTrajectory, VisualizationSource } from './data-contract';

// All requests stay same-origin. Vite (or the production reverse proxy) forwards
// /api server-side; the backend URL and API key are never browser variables.
const API_ORIGIN = '';
export const API_BASE = 'SAME-ORIGIN /api PROXY';

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); }
}

function apiPathId(id: string): string {
  // The backend contract is a catch-all path parameter. Preserve slashes in Volve IDs.
  return encodeURIComponent(id).replace(/%2F/gi, '/');
}

export async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_ORIGIN}${path}`, {
    headers: { Accept: 'application/json' }, signal,
  });
  if (!response.ok) {
    let body = '';
    try { body = await response.text(); } catch { /* preserve status if body cannot be read */ }
    if (response.status === 401 || response.status === 403) throw new ApiError('API key was rejected or is missing.', response.status);
    if (response.status === 404) throw new ApiError(`Endpoint or record not found: ${path}`, 404);
    throw new ApiError(`API request failed (${response.status})${body ? `: ${body.slice(0, 180)}` : ''}`, response.status);
  }
  return response.json() as Promise<T>;
}

function list<T>(data: unknown, keys: string[]): T[] {
  if (Array.isArray(data)) return data as T[];
  if (!data || typeof data !== 'object') return [];
  const obj = data as Record<string, unknown>;
  for (const k of keys) if (Array.isArray(obj[k])) return obj[k] as T[];
  return [];
}

export function normalizeWells(data: unknown, source: VisualizationSource = 'NWIS_TESTBED_SYNTHETIC'): Well[] {
  return list<Record<string, unknown>>(data, ['items', 'wells', 'results', 'data']).flatMap((r) => {
    const id = String(r.well_id ?? r.id ?? r.code ?? '');
    if (!id) return [];
    const lat = r.latitude ?? r.surface_lat ?? r.lat;
    const lon = r.longitude ?? r.surface_lon ?? r.lon ?? r.lng;
    return [{ ...r, well_id: id, name: String(r.name ?? r.well_name ?? id), latitude: lat == null ? null : Number(lat), longitude: lon == null ? null : Number(lon), elevation_m: r.elevation_m ?? r.kb_elevation_m ?? null, total_depth_md_m: r.total_depth_md_m == null ? null : Number(r.total_depth_md_m), source } as Well];
  });
}

function stationsOf(raw: unknown, id: string, source: VisualizationSource): WellTrajectory | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const root = raw as Record<string, unknown>;
  const stationsRaw = Array.isArray(raw) ? raw : root.stations ?? root.trajectory ?? root.survey_stations ?? root.items;
  if (!Array.isArray(stationsRaw)) return undefined;
  const stations = stationsRaw.flatMap((v) => {
    if (!v || typeof v !== 'object') return [];
    const s = v as Record<string, unknown>;
    const md = Number(s.md_m), tvd = Number(s.tvd_m), ns = Number(s.ns_m), ew = Number(s.ew_m);
    if (![md, tvd, ns, ew].every(Number.isFinite)) return [];
    return [{ md_m: md, tvd_m: tvd, ns_m: ns, ew_m: ew,
      inclination_deg: s.inclination_deg == null ? null : Number(s.inclination_deg),
      azimuth_deg: s.azimuth_deg == null ? null : Number(s.azimuth_deg), tvdss_m: s.tvdss_m == null ? null : Number(s.tvdss_m) } as SurveyStation];
  }).sort((a, b) => a.md_m - b.md_m);
  return stations.length ? { ...(root as object), source, well_id: String(root.well_id ?? id), stations } : undefined;
}

export const extractList = list;
export const extractTrajectory = (raw: unknown, id: string, source: VisualizationSource = 'NWIS_TESTBED_SYNTHETIC') => stationsOf(raw, id, source);
export const pathId = apiPathId;

export async function getTelemetryAtDepth(wellId: string, md: number, signal?: AbortSignal): Promise<unknown> {
  if (!Number.isFinite(md) || md < 0) throw new ApiError('Telemetry requires a confirmed non-negative MD query.', 400);
  const id = apiPathId(wellId);
  return getJson<unknown>(`/api/v2/telemetry/${id}?depth=${encodeURIComponent(String(md))}&window=300`, signal);
}
