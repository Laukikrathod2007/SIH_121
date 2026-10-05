import type {
  Offset3DDataProvider, VisualizationCasing, VisualizationEvent, VisualizationFormation,
  VisualizationHazard, VisualizationOffset, VisualizationSource, VisualizationTelemetry,
  VisualizationTrajectory, VisualizationWell,
} from './data-contract';

/** A request function should call same-origin host proxy routes, never embed a secret. */
export type ProviderRequest = (path: string, signal?: AbortSignal) => Promise<unknown>;

/**
 * Endpoint and response mapping for a backend with a different route/schema.
 * Supply only layers the backend actually supports; omitted layers become
 * unavailable in the renderer automatically.
 */
export interface MappedHttpProviderConfig {
  source: VisualizationSource;
  provenance?: { isVerified: boolean; isSynthetic: boolean; isDerived: boolean };
  request: ProviderRequest;
  endpoints: {
    wells: string;
    well?: (wellId: string) => string;
    trajectory?: (wellId: string) => string;
    formations?: (wellId: string) => string;
    events?: (wellId: string) => string;
    casing?: (wellId: string) => string;
    dorsOffsets?: (wellId: string, radiusKm: number, depthM: number | null) => string;
    hazards?: (wellId: string, depthM: number | null) => string;
    telemetryAtDepth?: (wellId: string, mdM: number) => string;
    health?: string;
  };
  map: {
    wells(raw: unknown, source: VisualizationSource): VisualizationWell[];
    well?(raw: unknown, requestedId: string, source: VisualizationSource): VisualizationWell;
    trajectory?(raw: unknown, requestedId: string, source: VisualizationSource): VisualizationTrajectory | null;
    formations?(raw: unknown, wellId: string): VisualizationFormation[];
    events?(raw: unknown, wellId: string): VisualizationEvent[];
    casing?(raw: unknown, wellId: string): VisualizationCasing[];
    dorsOffsets?(raw: unknown, wellId: string): VisualizationOffset[];
    hazards?(raw: unknown, wellId: string): VisualizationHazard[];
    telemetry?(raw: unknown, wellId: string): VisualizationTelemetry[];
    health?(raw: unknown): Record<string, unknown>;
  };
}

/** Build a provider from backend-specific endpoint and field mappings. */
export function createMappedHttpProvider(config: MappedHttpProviderConfig): Offset3DDataProvider {
  const provider: Offset3DDataProvider = {
    source: config.source,
    provenance: config.provenance,
    async getWells(signal) {
      return config.map.wells(await config.request(config.endpoints.wells, signal), config.source);
    },
  };
  const { endpoints, map, request } = config;
  if (endpoints.well && map.well) provider.getWell = async (id, signal) => map.well!(await request(endpoints.well!(id), signal), id, config.source);
  if (endpoints.trajectory && map.trajectory) provider.getTrajectory = async (id, signal) => map.trajectory!(await request(endpoints.trajectory!(id), signal), id, config.source);
  if (endpoints.formations && map.formations) provider.getFormations = async (id, signal) => map.formations!(await request(endpoints.formations!(id), signal), id);
  if (endpoints.events && map.events) provider.getEvents = async (id, signal) => map.events!(await request(endpoints.events!(id), signal), id);
  if (endpoints.casing && map.casing) provider.getCasing = async (id, signal) => map.casing!(await request(endpoints.casing!(id), signal), id);
  if (endpoints.dorsOffsets && map.dorsOffsets) provider.getDorsOffsets = async (id, radiusKm, depthM, signal) => map.dorsOffsets!(await request(endpoints.dorsOffsets!(id, radiusKm, depthM), signal), id);
  if (endpoints.hazards && map.hazards) provider.getHazards = async (id, depthM, signal) => map.hazards!(await request(endpoints.hazards!(id, depthM), signal), id);
  if (endpoints.telemetryAtDepth && map.telemetry) provider.getTelemetryAtDepth = async (id, mdM, signal) => map.telemetry!(await request(endpoints.telemetryAtDepth!(id, mdM), signal), id);
  if (endpoints.health && map.health) provider.getHealth = async signal => map.health!(await request(endpoints.health!, signal));
  return provider;
}
