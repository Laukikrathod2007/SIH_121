/** Known provenance labels plus labels supplied by a future host/backend adapter. */
export type VisualizationSource = 'VOLVE_SURVEY' | 'NWIS_TESTBED_SYNTHETIC' | 'NWIS_LIVE' | 'OIL_BACKEND' | (string & {});
export type Stage = 'global' | 'field' | 'subsurface';
export type DepthKind = 'md_m' | 'tvd_m' | 'tvdss_m';

export interface VisualizationWell {
  well_id: string;
  name: string;
  source: VisualizationSource;
  field?: string | null;
  operator?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  total_depth_md_m?: number | null;
  total_depth_tvd_m?: number | null;
  [key: string]: unknown;
}

export interface VisualizationSurveyStation {
  md_m: number;
  inclination_deg: number | null;
  azimuth_deg: number | null;
  tvd_m: number;
  ns_m: number;
  ew_m: number;
  tvdss_m: number | null;
}

export interface VisualizationTrajectory {
  well_id: string;
  source: VisualizationSource;
  stations: VisualizationSurveyStation[];
  coverage_status?: 'complete' | 'partial' | 'unknown';
  [key: string]: unknown;
}

export interface VisualizationOffset {
  well_id: string;
  dors_score?: number | null;
  distance_km?: number | null;
  component_scores?: { spatial?: number; formation?: number; depth?: number; trajectory?: number; hazard?: number; total?: number; distance_km?: number; [key: string]: unknown };
  [key: string]: unknown;
}
export interface VisualizationFormation {
  well_id?: string; formation?: string; formation_name?: string; name?: string;
  depth_top_md_m?: number; depth_md_m?: number; md_m?: number; depth_top_tvd_m?: number;
  depth_tvd_m?: number; tvd_m?: number; top_depth_m?: number; [key: string]: unknown;
}
export interface VisualizationEvent {
  well_id: string; depth_start_md_m?: number; formation?: string; event_type?: string; severity?: string; [key: string]: unknown;
}
export interface VisualizationHazard {
  well_id?: string; depth_start_m: number; depth_end_m: number; risk_level?: string; [key: string]: unknown;
}
export interface VisualizationCasing {
  well_id: string; depth_start_md_m?: number; depth_end_md_m?: number; [key: string]: unknown;
}
export interface VisualizationTelemetry {
  measured_depth_m?: number; timestamp?: string; [key: string]: unknown;
}

export interface VisualizationWellData {
  source: VisualizationSource;
  well: VisualizationWell;
  trajectory: VisualizationTrajectory | null;
  offsets: VisualizationOffset[];
  formations: VisualizationFormation[];
  events: VisualizationEvent[];
  corridors: VisualizationHazard[];
  casing: VisualizationCasing[];
  telemetry: VisualizationTelemetry[];
  unavailable: Record<string, string>;
  layerProvenance: Record<VisualizationLayer, VisualizationLayerProvenance>;
  layers: Record<VisualizationLayer, VisualizationLayerResult<unknown>>;
}

export type VisualizationLayer = 'well' | 'trajectory' | 'formations' | 'events' | 'hazards' | 'casing' | 'dors' | 'telemetry';
export interface VisualizationLayerProvenance {
  source: VisualizationSource;
  availability: 'available' | 'partial' | 'unavailable';
  isVerified: boolean;
  isSynthetic: boolean;
  isDerived: boolean;
  detail?: string;
}

/** Normalized layer envelope. An empty successful query remains distinguishable from a failed/unavailable query. */
export interface VisualizationLayerResult<T> {
  availability: 'available' | 'partial' | 'unavailable';
  items: T[];
  provenance: VisualizationLayerProvenance;
  reason?: string;
  coverage?: { startMdM?: number; endMdM?: number; stationCount?: number };
}

// Stable short aliases used by renderer/components; providers are the only
// code allowed to translate backend/source-specific records into these types.
export type Well = VisualizationWell;
export type SurveyStation = VisualizationSurveyStation;
export type WellTrajectory = VisualizationTrajectory;
export type OffsetScore = VisualizationOffset;
export type FormationObservation = VisualizationFormation;
export type DrillingEvent = VisualizationEvent;
export type RiskCorridor = VisualizationHazard;
export type CasingSection = VisualizationCasing;
export type TelemetryRecord = VisualizationTelemetry;
export type WellData = VisualizationWellData;

export interface Offset3DDataProvider {
  readonly source: VisualizationSource;
  /** Optional source-level provenance for adapters outside the built-in datasets. */
  readonly provenance?: { isVerified: boolean; isSynthetic: boolean; isDerived: boolean };
  getWells(signal?: AbortSignal): Promise<VisualizationWell[]>;
  getWell?(wellId: string, signal?: AbortSignal): Promise<VisualizationWell>;
  getTrajectory?(wellId: string, signal?: AbortSignal): Promise<VisualizationTrajectory | null>;
  getFormations?(wellId: string, signal?: AbortSignal): Promise<VisualizationFormation[]>;
  getEvents?(wellId: string, signal?: AbortSignal): Promise<VisualizationEvent[]>;
  getCasing?(wellId: string, signal?: AbortSignal): Promise<VisualizationCasing[]>;
  getDorsOffsets?(wellId: string, radiusKm: number, currentMdM: number | null, signal?: AbortSignal): Promise<VisualizationOffset[]>;
  getHazards?(wellId: string, currentMdM: number | null, signal?: AbortSignal): Promise<VisualizationHazard[]>;
  getTelemetryAtDepth?(wellId: string, md: number, signal?: AbortSignal): Promise<VisualizationTelemetry[]>;
  getHealth?(signal?: AbortSignal): Promise<Record<string, unknown>>;
}
