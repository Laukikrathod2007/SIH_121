import type { Offset3DDataProvider } from './data-contract';
import { nwisLiveProvider } from './nwisLiveProvider';
import { realVolveTrajectoryProvider } from './realVolveTrajectoryProvider';
import { assamDocumentedLocationsProvider } from './assamDocumentedLocationsProvider';

const providers: Record<string, Offset3DDataProvider> = {
  nwis: nwisLiveProvider,
  volve: realVolveTrajectoryProvider,
  assam: assamDocumentedLocationsProvider,
};

const selectedName = String(import.meta.env.VITE_VISUALIZATION_PROVIDER ?? 'volve').toLowerCase();
export const visualizationDataProvider = providers[selectedName] ?? nwisLiveProvider;
export const visualizationDataProviderName = providers[selectedName] ? selectedName : 'nwis';
