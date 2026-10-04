import { useEffect, useState } from 'react';
import { api } from '../../services/api';
import type { WellPoint } from './NearbyWellsMap';
import type { WellEvent } from './WellDetailPanel';

// Adapter between our real backend and the imported nwis-map-package
// components (NearbyWellsMap / WellDetailPanel / EvidenceViewer), which
// are used completely unchanged -- see those files' own headers. This
// file does the data shaping only; it does not modify the package.
//
// Fetches every real well (api.getWells()) and ALL events in one call
// (api.searchEventsStructured(), GET /api/v2/events with no filters --
// confirmed to return every event with its own well_id, capped at 100,
// well above the store's real 44), then groups client-side by well_id to
// compute the events_by_type/npt_hours aggregates WellPoint needs, plus the
// full per-well WellEvent[] map WellDetailPanel needs.
//
// Previously issued one GET /api/v2/events/{well_id} call per well (14
// requests for 14 wells) via Promise.all -- found during the end-to-end
// verification pass to be the direct cause of 429s on a single page visit:
// combined with the one GET /api/v2/wells call, that was 15 real requests
// from loading this page once, a third of module 02's 60-req/60s budget in
// one page load (doubled to 30 under React StrictMode's dev-only
// double-effect-invocation, which is expected/correct StrictMode behavior,
// not a bug in this file -- but the real 15-req-per-load count underneath
// it was a genuine inefficiency). Replaced with 2 total requests
// (getWells + searchEventsStructured), independent of well count -- re-verified
// live: a single page load now shows exactly 2 module-02 requests (4 under
// StrictMode) instead of 15 (30).
//
// All 14 wells currently in the live store (12 synthetic + the 2 real
// Volve wells) are included -- "every well we have data for", not a
// filtered subset.
export function useNwisMapData() {
  const [wells, setWells] = useState<WellPoint[]>([]);
  const [eventsByWell, setEventsByWell] = useState<Record<string, WellEvent[]>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const [realWells, eventsResponse] = await Promise.all([
        api.getWells().catch(() => []),
        api.searchEventsStructured().catch(() => ({ events: [] } as Partial<Awaited<ReturnType<typeof api.searchEventsStructured>>>)),
      ]);
      if (cancelled) return;

      const allEvents = (eventsResponse.events ?? []) as unknown as WellEvent[];
      const eventsByWellId: Record<string, WellEvent[]> = {};
      for (const e of allEvents) {
        const wellId = (e as unknown as { well_id: string }).well_id;
        (eventsByWellId[wellId] ??= []).push(e);
      }

      const nextWells: WellPoint[] = realWells.map((w) => {
        const events = eventsByWellId[w.well_id] ?? [];

        const events_by_type: Record<string, number> = {};
        let npt_hours = 0;
        for (const e of events) {
          const eventType = (e as unknown as { event_type: string }).event_type;
          const eventNpt = (e as unknown as { npt_hours?: number }).npt_hours;
          events_by_type[eventType] = (events_by_type[eventType] ?? 0) + 1;
          npt_hours += eventNpt ?? 0;
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
      setEventsByWell(eventsByWellId);
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  return { wells, eventsByWell, loading };
}
