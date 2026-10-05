import type {
  Offset3DDataProvider, VisualizationWell, VisualizationWellData, VisualizationTrajectory,
  VisualizationOffset, VisualizationFormation, VisualizationEvent, VisualizationHazard,
  VisualizationCasing, VisualizationTelemetry, VisualizationLayer, VisualizationLayerProvenance,
  VisualizationLayerResult,
} from './data-contract';

export type { Offset3DDataProvider } from './data-contract';

/**
 * The only fetch fan-out used by the renderer-facing application state.
 * Source-specific contracts and response wrappers stay behind a provider.
 */
export async function loadVisualizationWellData(
  provider: Offset3DDataProvider,
  well: VisualizationWell,
  currentMdM: number | null,
  radiusKm: number,
  signal?: AbortSignal,
  includeTelemetry = true,
  telemetryMdM: number | null = currentMdM,
): Promise<VisualizationWellData> {
  const unavailable: Record<string, string> = {};
  const safe = async <T,>(label: string, request: () => Promise<T>, fallback: T): Promise<T> => {
    try { return await request(); }
    catch (error) {
      unavailable[label] = error instanceof Error ? error.message : 'Unavailable from selected provider';
      return fallback;
    }
  };
  const unsupported = <T,>(label: string, fallback: T): Promise<T> => {
    unavailable[label] = `${provider.source} does not provide this layer.`;
    return Promise.resolve(fallback);
  };
  const noOffsets: VisualizationOffset[] = [];
  const noFormations: VisualizationFormation[] = [];
  const noEvents: VisualizationEvent[] = [];
  const noHazards: VisualizationHazard[] = [];
  const noCasing: VisualizationCasing[] = [];
  const noTelemetry: VisualizationTelemetry[] = [];
  const noTrajectory: VisualizationTrajectory | null = null;
  const [wellResult, trajectory, formations, events, casing, offsets, hazards, telemetry] = await Promise.all([
    provider.getWell ? safe('well', () => provider.getWell!(well.well_id, signal), well) : Promise.resolve(well),
    provider.getTrajectory ? safe('trajectory', () => provider.getTrajectory!(well.well_id, signal), noTrajectory) : unsupported('trajectory', noTrajectory),
    provider.getFormations ? safe('formations', () => provider.getFormations!(well.well_id, signal), noFormations) : unsupported('formations', noFormations),
    provider.getEvents ? safe('events', () => provider.getEvents!(well.well_id, signal), noEvents) : unsupported('events', noEvents),
    provider.getCasing ? safe('casing', () => provider.getCasing!(well.well_id, signal), noCasing) : unsupported('casing', noCasing),
    provider.getDorsOffsets ? safe('DORS offsets', () => provider.getDorsOffsets!(well.well_id, radiusKm, currentMdM, signal), noOffsets) : unsupported('DORS offsets', noOffsets),
    provider.getHazards ? safe('hazards', () => provider.getHazards!(well.well_id, currentMdM, signal), noHazards) : unsupported('hazards', noHazards),
    includeTelemetry && !provider.getTelemetryAtDepth ? unsupported('telemetry', noTelemetry)
      : includeTelemetry && telemetryMdM != null
        ? safe('telemetry', () => provider.getTelemetryAtDepth!(well.well_id, telemetryMdM, signal), noTelemetry)
      : Promise.resolve(noTelemetry),
  ]);
  if (includeTelemetry && telemetryMdM == null && provider.getTelemetryAtDepth) {
    unavailable.telemetry = 'A confirmed measured-depth query is required by this telemetry provider.';
  }
  if (!trajectory && !unavailable.trajectory) unavailable.trajectory = `No trajectory is available from ${provider.source}.`;
  const hasFailure = (key: string) => Object.hasOwn(unavailable, key);
  const availability = (key: string): VisualizationLayerProvenance['availability'] => hasFailure(key) ? 'unavailable' : 'available';
  const isSynthetic = provider.provenance?.isSynthetic ?? provider.source === 'NWIS_TESTBED_SYNTHETIC';
  const isVerified = provider.provenance?.isVerified ?? (provider.source === 'VOLVE_SURVEY' || provider.source === 'NWIS_TESTBED_SYNTHETIC');
  const isDerived = provider.provenance?.isDerived ?? provider.source === 'VOLVE_SURVEY';
  const provenance = (layer: VisualizationLayer, state: VisualizationLayerProvenance['availability'], detail?: string): VisualizationLayerProvenance => ({
    source: provider.source, availability: state, isVerified, isSynthetic,
    isDerived, ...(detail ? { detail } : {}),
  });
  const layerProvenance: Record<VisualizationLayer, VisualizationLayerProvenance> = {
    well: provenance('well', availability('well')),
    trajectory: provenance('trajectory', !trajectory ? 'unavailable' : trajectory.coverage_status === 'partial' ? 'partial' : 'available', unavailable.trajectory ?? (trajectory?.coverage_status === 'partial' ? `Survey coverage is partial: ${trajectory.stations[0]?.md_m}–${trajectory.stations.at(-1)?.md_m} m MD.` : undefined)),
    formations: provenance('formations', availability('formations'), unavailable.formations ?? (!formations.length ? 'Source returned no formation records for this well.' : undefined)),
    events: provenance('events', availability('events'), unavailable.events ?? (!events.length ? 'Source returned no event records for this well.' : undefined)),
    hazards: provenance('hazards', availability('hazards'), unavailable.hazards ?? (!hazards.length ? 'Source returned no hazard intervals for this well.' : undefined)),
    casing: provenance('casing', availability('casing'), unavailable.casing ?? (!casing.length ? 'Source returned no casing records for this well.' : undefined)),
    dors: provenance('dors', availability('DORS offsets'), unavailable['DORS offsets'] ?? (!offsets.length ? 'Source returned no ranked offsets for this well.' : undefined)),
    telemetry: provenance('telemetry', includeTelemetry ? availability('telemetry') : 'unavailable', unavailable.telemetry ?? (!telemetry.length ? 'No telemetry samples returned for the confirmed query.' : undefined)),
  };
  const toLayer = <T,>(key: VisualizationLayer, items: T[], status = layerProvenance[key].availability, reason = layerProvenance[key].detail): VisualizationLayerResult<T> => ({ availability: status, items, provenance: layerProvenance[key], ...(reason ? { reason } : {}) });
  const trajectoryCoverage = trajectory?.stations.length ? { startMdM: trajectory.stations[0].md_m, endMdM: trajectory.stations.at(-1)!.md_m, stationCount: trajectory.stations.length } : undefined;
  const layers: Record<VisualizationLayer, VisualizationLayerResult<unknown>> = {
    well: toLayer('well', [wellResult]),
    trajectory: { ...toLayer('trajectory', trajectory ? [trajectory] : []), ...(trajectoryCoverage ? { coverage: trajectoryCoverage } : {}) },
    formations: toLayer('formations', formations), events: toLayer('events', events), hazards: toLayer('hazards', hazards),
    casing: toLayer('casing', casing), dors: toLayer('dors', offsets), telemetry: toLayer('telemetry', telemetry),
  };
  return { source: provider.source, well: wellResult, trajectory, formations, events, casing, offsets, corridors: hazards, telemetry, unavailable, layerProvenance, layers };
}
