import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import type { WellPoint } from './NearbyWellsMap';
import type { WellEvent } from './WellDetailPanel';

// Adapter between our real backend and the imported nwis-map-package
// components (NearbyWellsMap / WellDetailPanel / EvidenceViewer), which
// are used completely unchanged -- see those files' own headers. This
// file does the data shaping only; it does not modify the package.
//
// Fetches every real well (api.getWells()) and, per well, its real events
// (api.getWellEvents) to compute the events_by_type/npt_hours aggregates
// WellPoint needs, plus the full per-well WellEvent[] map WellDetailPanel
// needs. All 14 wells currently in the live store (12 synthetic + the 2
// real Volve wells wired in this session) are included -- "every well we
// have data for", not a filtered subset.
export function useNwisMapData() {
  const [wells, setWells] = useState<WellPoint[]>([]);
  const [eventsByWell, setEventsByWell] = useState<Record<string, WellEvent[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const realWells = await api.getWells().catch(() => []);
      const eventLists = await Promise.all(
        realWells.map((w) => api.getWellEvents(w.well_id).catch(() => [])),
      );
      if (cancelled) return;

      const nextEventsByWell: Record<string, WellEvent[]> = {};
      const nextWells: WellPoint[] = realWells.map((w, i) => {
        const events = eventLists[i];
        nextEventsByWell[w.well_id] = events as unknown as WellEvent[];

        const events_by_type: Record<string, number> = {};
        let npt_hours = 0;
        for (const e of events) {
          events_by_type[e.event_type] = (events_by_type[e.event_type] ?? 0) + 1;
          npt_hours += e.npt_hours ?? 0;
        }

        return {
          well_id: w.well_id,
          well_name: w.well_name,
          field: w.field,
          lat: w.surface_lat,
          lon: w.surface_lon,
          status: w.status,
          well_type: w.well_type,
          total_depth_md_m: w.total_depth_md_m,
          total_events: events.length,
          npt_hours: Math.round(npt_hours * 10) / 10,
          events_by_type,
        };
      });

      setWells(nextWells);
      setEventsByWell(nextEventsByWell);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  return { wells, eventsByWell, loading };
}
