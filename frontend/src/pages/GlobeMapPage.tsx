import React, { useEffect, useState } from 'react';
import { Globe2, Compass } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { MapWell, OffsetWellRanking } from '../types';
import { OffsetGlobe3D } from '../components/globe/OffsetGlobe3D';
import { haversineKm } from '../lib/globeGeometry';

// Real interactive 3D offset-well globe -- the "actual map" requested
// during the 3D-integration phase, built from the same real backend data
// as the existing 2D Offset Map (NwisMapPage) and Nearby Wells page, not a
// second/fake dataset. See AUDIT/03_3D_INTEGRATION.md for why this is a
// NEW page (mounted under /app, alongside the 2D views) rather than a
// retrofit of DrillWise-Frontend (a single-well marketing hero animation,
// no map/selection concept at all) or visualization_3d (a Blender offline
// render pipeline, not a runnable web component -- its own idea.md says
// interactive selection "is not started").
export const GlobeMapPage: React.FC = () => {
  const { activeWellId, setActiveWellId, telemetry } = useApp();
  const depth = telemetry?.measured_depth_m || 2450.0;
  const [wells, setWells] = useState<MapWell[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [radiusKm, setRadiusKm] = useState<number>(25);
  const [dorsOffsets, setDorsOffsets] = useState<OffsetWellRanking[]>([]);

  // Real data fetch -- identical endpoint to the 2D map (GET /api/v2/map/wells),
  // so both views are always showing the same well catalog.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await api.getMapWells();
        if (!cancelled) {
          setWells(data);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError('Could not load the well map data. Contact your system administrator if this persists.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Real DORS ranking for the currently active well, same endpoint
  // NearbyWellsPage uses -- shown in the side panel so selecting a well on
  // the globe and reading its real offset-relevance score is one real
  // round trip, not an invented metric.
  //
  // radius_km is passed to the endpoint, but confirmed from
  // engines/dors_engine.py (score_spatial) that it's a scoring-decay
  // parameter, not a hard filter -- rank_offset_wells() returns every
  // other well, just scoring distant ones near zero on the spatial
  // component. The endpoint's own `total_ranked` is therefore NOT "wells
  // within radius" despite the parameter name. NearbyWellsPage already
  // works around this by filtering client-side with real Haversine
  // distance before using the count; this page matches that same pattern
  // rather than trusting the raw ranking length (confirmed by testing with
  // radius_km=5 directly against the live endpoint -- it still returned
  // all 10 other wells, several thousand km away).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getOffsetRank(activeWellId, depth, radiusKm);
        if (!cancelled && res?.rankings) setDorsOffsets(res.rankings);
      } catch {
        if (!cancelled) setDorsOffsets([]);
      }
    })();
    return () => { cancelled = true; };
  }, [activeWellId, radiusKm, Math.floor(depth / 20)]);

  const activeWell = wells.find((w) => w.well_id === activeWellId);

  const inRadiusOffsets = activeWell
    ? dorsOffsets.filter((o) => {
        const w = wells.find((x) => x.well_id === o.well_id);
        if (!w) return false;
        return haversineKm(activeWell.lat, activeWell.lon, w.lat, w.lon) <= radiusKm;
      })
    : [];

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto h-full flex flex-col">
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Globe2 className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              3D OFFSET WELL GLOBE
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                NEW
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Real well catalog ({wells.length} wells) &middot; same data as Offset Map / Nearby Wells
            </div>
          </div>
        </div>
      </div>

      <div className="scada-panel px-4 py-3 flex items-center gap-4 shrink-0">
        <div className="flex items-center gap-2 shrink-0 text-xs font-mono text-slate-300">
          <Compass className="w-4 h-4 text-cyan-400" />
          <span className="font-bold">OFFSET SEARCH RADIUS</span>
        </div>
        <input
          type="range"
          min={5}
          max={50}
          step={1}
          value={radiusKm}
          onChange={(e) => setRadiusKm(Number(e.target.value))}
          className="scada-slider flex-1"
          style={{ ['--slider-fill' as any]: `${((radiusKm - 5) / (50 - 5)) * 100}%` }}
        />
        <div className="shrink-0 text-xs font-mono bg-slate-900 border border-cyan-500/40 text-cyan-300 font-bold px-2.5 py-1 rounded min-w-[64px] text-center">
          {radiusKm} km
        </div>
        <div className="shrink-0 text-xs font-mono text-slate-400">
          {inRadiusOffsets.length} offset well{inRadiusOffsets.length === 1 ? '' : 's'} within radius of <span className="text-cyan-300">{activeWellId}</span>
        </div>
      </div>

      <div className="flex-1 min-h-[500px] grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 scada-panel p-2 relative overflow-hidden">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500 font-mono text-xs z-10 bg-slate-950/60">
              Loading real well catalog...
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center text-rose-400 font-mono text-xs z-10 bg-slate-950/80 p-4 text-center">
              {error}
            </div>
          )}
          {!loading && !error && (
            <OffsetGlobe3D
              wells={wells}
              activeWellId={activeWellId}
              radiusKm={radiusKm}
              onSelectWell={setActiveWellId}
            />
          )}
        </div>

        <div className="scada-panel p-4 flex flex-col space-y-3 overflow-y-auto">
          <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800">
            ACTIVE WELL: {activeWell?.well_name ?? activeWellId}
          </div>
          {activeWell && (
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">FIELD</div>
                <div className="font-bold text-slate-100">{activeWell.field}</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">TOTAL DEPTH</div>
                <div className="font-bold text-slate-100">{activeWell.total_depth_md_m.toFixed(0)} m MD</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">STATUS</div>
                <div className="font-bold text-slate-100">{activeWell.status}</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">EVENTS LOGGED</div>
                <div className="font-bold text-slate-100">{activeWell.total_events}</div>
              </div>
            </div>
          )}

          <div className="text-xs font-mono font-bold text-slate-300 pt-2 border-t border-slate-800">
            REAL DORS OFFSET RANKING
            <span className="text-slate-500 font-normal ml-1">(all catalog wells, not radius-limited)</span>
          </div>
          <div className="space-y-1.5 text-xs font-mono">
            {dorsOffsets.length === 0 && (
              <div className="text-slate-500 p-2 text-center">No offset wells ranked for this well yet.</div>
            )}
            {dorsOffsets.map((o, idx) => (
              <button
                key={o.well_id}
                onClick={() => setActiveWellId(o.well_id)}
                className="w-full flex items-center justify-between p-2 bg-slate-900/70 border border-slate-800 rounded hover:border-cyan-500/40 transition text-left"
              >
                <span className="text-cyan-400 font-semibold">#{idx + 1} {o.well_id}</span>
                <span className="text-slate-400">{o.distance_km.toFixed(1)} km</span>
                <span className="text-amber-400 font-bold">{(o.dors_score * 100).toFixed(0)}%</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
