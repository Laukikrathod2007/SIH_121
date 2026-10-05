import type { Offset3DDataProvider, VisualizationWell } from './data-contract';

interface SourceWell {
  well_id: string; name: string; field: string;
  latitude: number; longitude: number;
  latitude_dms: string; longitude_dms: string;
}
interface SourceFile {
  source: string; operator: string; source_url: string; document_context: string;
  coordinate_note: string; wells: SourceWell[];
}

let sourcePromise: Promise<SourceFile> | undefined;
function loadSource() {
  sourcePromise ??= fetch('/data/assam/documented-wellheads.json', { headers: { Accept: 'application/json' } })
    .then(async response => {
      if (!response.ok) throw new Error(`Public Assam well-location source failed (${response.status}).`);
      const file = await response.json() as SourceFile;
      if (!Array.isArray(file.wells) || !file.wells.length) throw new Error('The Assam source contains no well records.');
      for (const well of file.wells) {
        if (!well.well_id || !Number.isFinite(well.latitude) || !Number.isFinite(well.longitude)) {
          throw new Error('The Assam source contains an invalid well ID or coordinate.');
        }
      }
      return file;
    }).catch(error => { sourcePromise = undefined; throw error; });
  return sourcePromise;
}

function normalize(row: SourceWell, file: SourceFile): VisualizationWell {
  return {
    well_id: row.well_id,
    name: row.name,
    field: row.field,
    operator: file.operator,
    latitude: row.latitude,
    longitude: row.longitude,
    source: 'OIL_ASSAM_PUBLIC_LOCATIONS',
    location_source: file.source,
    source_url: file.source_url,
    source_well_name: row.name,
    reported_latitude_dms: row.latitude_dms,
    reported_longitude_dms: row.longitude_dms,
    location_datum: 'Not specified in source document',
    provenance: {
      source: file.source,
      sourceUrl: file.source_url,
      documentContext: file.document_context,
      coordinateNote: file.coordinate_note,
      isVerified: true,
      isSynthetic: false,
      isDerived: true,
      derivation: 'Published DMS latitude/longitude converted to decimal degrees; no trajectory or operations inferred.',
    },
  };
}

/** Publicly documented OIL Assam wellhead coordinates only; no subsurface layers are implied. */
export const assamDocumentedLocationsProvider: Offset3DDataProvider = {
  source: 'OIL_ASSAM_PUBLIC_LOCATIONS',
  provenance: { isVerified: true, isSynthetic: false, isDerived: true },
  async getWells() {
    const file = await loadSource();
    return file.wells.map(row => normalize(row, file));
  },
  async getWell(wellId) {
    const wells = await this.getWells();
    const well = wells.find(candidate => candidate.well_id === wellId);
    if (!well) throw new Error(`The public Assam location source has no exact well ID '${wellId}'.`);
    return well;
  },
  async getTrajectory() { return null; },
  async getFormations() { throw new Error('Unavailable for this public coordinate dataset.'); },
  async getEvents() { throw new Error('Unavailable for this public coordinate dataset.'); },
  async getCasing() { throw new Error('Unavailable for this public coordinate dataset.'); },
  async getDorsOffsets() { throw new Error('DORS is unavailable for this public coordinate dataset.'); },
  async getHazards() { throw new Error('Unavailable for this public coordinate dataset.'); },
  async getTelemetryAtDepth() { throw new Error('Telemetry is unavailable for this public coordinate dataset.'); },
};
