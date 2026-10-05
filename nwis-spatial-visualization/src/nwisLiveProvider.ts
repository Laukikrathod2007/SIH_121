import type {
  Offset3DDataProvider, VisualizationWell, VisualizationOffset, VisualizationFormation,
  VisualizationEvent, VisualizationHazard, VisualizationCasing, VisualizationTelemetry,
} from './data-contract';
import { ApiError, extractList, extractTrajectory, getJson, getTelemetryAtDepth, normalizeWells, pathId } from './api';

function rows<T>(raw: unknown, wrappers: string[]): T[] { return extractList<T>(raw, wrappers); }
function requireDepth(depth: number | null): number {
  if (depth == null || !Number.isFinite(depth) || depth < 0) throw new ApiError('A confirmed measured depth in metres is required by this endpoint.', 400);
  return depth;
}
const isVolveWell = (well: Pick<VisualizationWell, 'well_id' | 'field'>) =>
  String(well.field ?? '').toLowerCase() === 'volve' || /^\d+\/\d+-f-/i.test(well.well_id);
const isHgjDemoWell = (id: string) => /^WELL-HGJ-/i.test(id);

/**
 * NWIS Module 02 adapter. The backend's store currently contains both the
 * generated HGJ testbed and two Volve records; this provider intentionally
 * selects only HGJ testbed rows. Genuine Volve surveys use the separate local
 * Volve provider and are never joined to HGJ identifiers.
 */
export const nwisLiveProvider: Offset3DDataProvider = {
  source: 'NWIS_TESTBED_SYNTHETIC',
  async getHealth(signal) { return getJson<Record<string, unknown>>('/api/v2/health', signal); },
  async getWells(signal) {
    const wells = normalizeWells(await getJson<unknown>('/api/v2/wells', signal));
    return wells.filter(w => !isVolveWell(w) && isHgjDemoWell(w.well_id)).map(w => ({ ...w, source: 'NWIS_TESTBED_SYNTHETIC' as const }));
  },
  async getWell(wellId, signal) {
    if (!isHgjDemoWell(wellId)) throw new ApiError('This provider only serves NWIS HGJ synthetic/demo wells.', 404);
    const raw = await getJson<Record<string, unknown>>(`/api/v2/wells/${pathId(wellId)}`, signal);
    const item = (raw.well ?? raw.data ?? raw) as Record<string, unknown>;
    const normalized = normalizeWells([item])[0];
    if (!normalized) throw new ApiError(`Well response is missing an identifier for ${wellId}.`, 502);
    return { ...normalized, source: 'NWIS_TESTBED_SYNTHETIC' };
  },
  // Generated trajectories are displayed only as explicitly labelled testbed
  // data. They are never joined to the independent Volve survey provider.
  async getTrajectory(wellId, signal) {
    if (!isHgjDemoWell(wellId)) return null;
    const raw = await getJson<unknown>(`/api/v2/trajectory/${pathId(wellId)}`, signal);
    const trajectory = extractTrajectory(raw, wellId, 'NWIS_TESTBED_SYNTHETIC');
    return trajectory ? { ...trajectory, provenance: { source: 'NWIS Module 02 generated testbed', isVerified: true, isSynthetic: true, isDerived: true } } : null;
  },
  async getFormations(wellId, signal) {
    if (!isHgjDemoWell(wellId)) return [];
    return rows<VisualizationFormation>(await getJson(`/api/v2/formations/${pathId(wellId)}`, signal), ['formation_tops', 'formations', 'tops', 'observations', 'items', 'data']);
  },
  async getEvents(wellId, signal) {
    if (!isHgjDemoWell(wellId)) return [];
    return rows<VisualizationEvent>(await getJson(`/api/v2/events/${pathId(wellId)}`, signal), ['events', 'items', 'data']);
  },
  async getCasing(wellId, signal) {
    if (!isHgjDemoWell(wellId)) return [];
    return rows<VisualizationCasing>(await getJson(`/api/v2/casing/${pathId(wellId)}`, signal), ['casing_records', 'casing', 'sections', 'items', 'data']);
  },
  async getDorsOffsets(wellId, radiusKm, currentMdM, signal) {
    const depth = requireDepth(currentMdM);
    if (!isHgjDemoWell(wellId)) return [];
    const raw = await getJson<unknown>(`/api/v2/offset_rank/${pathId(wellId)}?depth=${encodeURIComponent(String(depth))}&radius_km=${encodeURIComponent(String(radiusKm))}&top_n=20`, signal);
    return rows<VisualizationOffset>(raw, ['rankings', 'offsets', 'ranked_offsets', 'results', 'items'])
      .filter(o => isHgjDemoWell(String(o.well_id ?? '')))
      .map(o => ({ ...o, well_id: String(o.well_id), source: 'NWIS_TESTBED_SYNTHETIC' } as VisualizationOffset));
  },
  async getHazards(wellId, currentMdM, signal) {
    const depth = requireDepth(currentMdM);
    if (!isHgjDemoWell(wellId)) return [];
    return rows<VisualizationHazard & { contributing_wells?: string[] }>(await getJson(`/api/v2/corridors/${pathId(wellId)}?depth=${encodeURIComponent(String(depth))}`, signal), ['corridors', 'risk_corridors', 'items', 'data'])
      .filter(c => Array.isArray(c.contributing_wells) && c.contributing_wells.length > 0 && c.contributing_wells.every(isHgjDemoWell));
  },
  async getTelemetryAtDepth(wellId, md, signal) {
    if (!isHgjDemoWell(wellId)) return [];
    const raw = await getTelemetryAtDepth(wellId, md, signal);
    return rows<Record<string, unknown>>(raw, ['records', 'telemetry', 'items', 'data'])
      // Module 02's telemetry query currently reads the active stream. Keep
      // records scoped to their actual well ID if the response is unexpected.
      .filter(r => String(r.well_id ?? '') === wellId)
      .map(r => ({ ...r, measured_depth_m: finiteOrNull(r.depth_m ?? r.measured_depth_m) } as VisualizationTelemetry));
  },
};

function finiteOrNull(value: unknown): number | null {
  const number = typeof value === 'number' ? value : Number(value);
  return value == null || !Number.isFinite(number) ? null : number;
}
