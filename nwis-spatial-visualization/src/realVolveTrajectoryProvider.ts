import type { Offset3DDataProvider, VisualizationWell, VisualizationTrajectory } from './data-contract';
import { extractTrajectory } from './api';

interface VolveSourceRecord extends Record<string, unknown> {
  well_id: string;
  well_name?: string;
  method?: string;
  well_type?: string;
  stations: Array<Record<string, unknown>>;
}

let sourceRecords: Promise<Map<string, VolveSourceRecord>> | undefined;

// Explicit ID joins from Module 02's REAL_TRAJECTORY_KEY and REAL_WELL_F12/F1
// metadata. Coordinates are present only for these two exact Volve trajectories;
// other Volve records remain unpositioned until verified wellhead metadata exists.
const verifiedVolveWellheads: Record<string, { latitude: number; longitude: number; matchedWellId: string }> = {
  'WELL-15_9-F-12': { latitude: 58.441613, longitude: 1.887480, matchedWellId: '15/9-F-12' },
  'WELL-15_9-F-1': { latitude: 58.441641, longitude: 1.887419, matchedWellId: '15/9-F-1' },
};

async function loadSource(): Promise<Map<string, VolveSourceRecord>> {
  if (!sourceRecords) {
    sourceRecords = fetch('/data/volve/real_trajectories_witsml.json', { headers: { Accept: 'application/json' } })
      .then(async response => {
        if (!response.ok) throw new Error(`Equinor Volve trajectory source request failed (${response.status}).`);
        const raw: unknown = await response.json();
        if (!Array.isArray(raw)) throw new Error('Equinor Volve trajectory source must be a JSON array.');
        const records = new Map<string, VolveSourceRecord>();
        for (const value of raw) {
          if (!value || typeof value !== 'object') continue;
          const row = value as VolveSourceRecord;
          if (typeof row.well_id !== 'string' || !Array.isArray(row.stations) || !row.stations.length) continue;
          if (records.has(row.well_id)) throw new Error(`Duplicate well_id in Volve source: ${row.well_id}`);
          records.set(row.well_id, row);
        }
        return records;
      })
      .catch(error => { sourceRecords = undefined; throw error; });
  }
  return sourceRecords;
}

async function recordFor(id: string): Promise<VolveSourceRecord | null> {
  const records = await loadSource();
  return records.get(id) ?? null;
}

function toWell(record: VolveSourceRecord): VisualizationWell {
  const last = record.stations.at(-1) ?? {};
  const location = verifiedVolveWellheads[record.well_id];
  return {
    well_id: record.well_id,
    name: String(record.well_name ?? record.well_id),
    field: 'Volve',
    operator: 'Equinor',
    latitude: location?.latitude ?? null,
    longitude: location?.longitude ?? null,
    survey_start_md_m: finiteOrNull(record.stations[0]?.md_m),
    survey_end_md_m: finiteOrNull(last.md_m),
    source: 'VOLVE_SURVEY',
    trajectory_method: record.method ?? null,
    well_type: record.well_type ?? null,
    station_count: record.stations.length,
    provenance: {
      source: 'Equinor Volve WITSML survey dataset', isVerified: true, isSynthetic: false, isDerived: true,
      wellheadSource: location ? `Module 02 verified Volve wellhead metadata (${location.matchedWellId})` : 'Unavailable in trajectory dataset',
    },
  };
}

export const realVolveTrajectoryProvider: Offset3DDataProvider = {
  source: 'VOLVE_SURVEY',
  async getWells() {
    const records = await loadSource();
    return [...records.values()].map(toWell);
  },
  async getWell(wellId) {
    const record = await recordFor(wellId);
    if (!record) throw new Error(`The Volve survey dataset has no exact well ID '${wellId}'.`);
    return toWell(record);
  },
  async getTrajectory(wellId): Promise<VisualizationTrajectory | null> {
    const record = await recordFor(wellId);
    if (!record) return null;
    const trajectory = extractTrajectory(record, wellId, 'VOLVE_SURVEY');
    if (!trajectory) throw new Error(`Volve survey for ${wellId} contains no valid 3D survey stations.`);
    return { ...trajectory, coverage_status: wellId === 'WELL-15_9-F-1' ? 'partial' : 'unknown', provenance: { source: 'Equinor Volve WITSML survey dataset', isVerified: true, isSynthetic: false, isDerived: true }, station_count: trajectory.stations.length };
  },
  async getFormations() { throw new Error('Unavailable for this dataset.'); },
  async getEvents() { throw new Error('Unavailable for this dataset.'); },
  async getCasing() { throw new Error('Unavailable for this dataset.'); },
  async getDorsOffsets() { throw new Error('DORS offsets are unavailable for this dataset.'); },
  async getHazards() { throw new Error('Unavailable for this dataset.'); },
  async getTelemetryAtDepth() { throw new Error('Telemetry is unavailable for this historical survey dataset.'); },
};

export const realVolve3DProvider = realVolveTrajectoryProvider;

function finiteOrNull(value: unknown): number | null {
  const number = typeof value === 'number' ? value : Number(value);
  return value == null || !Number.isFinite(number) ? null : number;
}
