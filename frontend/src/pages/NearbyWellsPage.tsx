import React, { useState, useEffect, Suspense, lazy } from 'react';
import {
  Compass,
  MapPin,
  Layers,
  ArrowUpDown,
  Filter,
  Eye,
  CheckCircle,
  AlertTriangle,
  FileText,
  Navigation,
  Box,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { Well, OffsetWellRanking, FormationTop, DrillingEvent } from '../types';
import { BasinMap } from '../components/BasinMap';
// Priority 7 remediation (2026-10-04): this page used to define its own
// byte-identical copy of haversineKm; consolidated to the one canonical
// implementation (also used by the 3D globe) so there's a single source of
// truth for this formula across the app. No behavior change — confirmed
// identical before removing the local copy.
import { haversineKm } from '../lib/globeGeometry';

// Lazy-loaded: pulls in three.js + @react-three/fiber (~800kB), only needed
// when the user actually opens the 3D trajectory view, not on initial load
// of every page in the app.
const WellInspector3DModal = lazy(() =>
  import('../components/WellInspector3DModal').then((m) => ({ default: m.WellInspector3DModal }))
);

export const NearbyWellsPage: React.FC = () => {
  const { activeWellId, setActiveWellId, wells, activeWell, telemetry } = useApp();

  const [dorsOffsets, setDorsOffsets] = useState<OffsetWellRanking[]>([]);
  const [selectedWellId, setSelectedWellId] = useState<string>('WELL-NHK-002');
  const [selectedWellFormations, setSelectedWellFormations] = useState<FormationTop[]>([]);
  const [selectedWellEvents, setSelectedWellEvents] = useState<DrillingEvent[]>([]);
  const [filterField, setFilterField] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [radiusKm, setRadiusKm] = useState<number>(25);
  const [show3D, setShow3D] = useState<boolean>(false);

  const depth = telemetry?.measured_depth_m || 2450.0;

  // Load DORS offsets for active well
  useEffect(() => {
    const fetchDors = async () => {
      try {
        const res = await api.getOffsetRank(activeWellId, depth);
        if (res && res.rankings) {
          setDorsOffsets(res.rankings);
        }
      } catch (err) {
        // Fallback
      }
    };
    fetchDors();
  }, [activeWellId, Math.floor(depth / 20)]);

  // Load details for selected offset well
  useEffect(() => {
    const fetchWellDetails = async () => {
      try {
        const [forms, evts] = await Promise.all([
          api.getFormations(selectedWellId).catch(() => []),
          api.getWellEvents(selectedWellId).catch(() => []),
        ]);
        setSelectedWellFormations(forms);
        setSelectedWellEvents(evts);
      } catch (err) {
        // Fallback
      }
    };
    fetchWellDetails();
  }, [selectedWellId]);

  const selectedWell = wells.find((w) => w.well_id === selectedWellId) || wells[0];

  const filteredWells = wells.filter((w) => {
    const matchesField = filterField === 'ALL' || w.field.toLowerCase().includes(filterField.toLowerCase());
    const matchesSearch = w.well_name.toLowerCase().includes(searchQuery.toLowerCase()) || w.well_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesRadius =
      w.well_id === activeWellId ||
      !activeWell ||
      haversineKm(activeWell.surface_lat, activeWell.surface_lon, w.surface_lat, w.surface_lon) <= radiusKm;
    return matchesField && matchesSearch && matchesRadius;
  });

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              MODULE 2: NEARBY WELL INTELLIGENCE & GEOSPATIAL MAP
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                HAVERSINE + 5-FACTOR DORS
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Upper Assam Shelf | Total Catalog: {wells.length} Wells | Showing {filteredWells.length} within {radiusKm} km
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <input
            type="text"
            placeholder="Search Well ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-slate-900 border border-slate-700 px-2 py-1 rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
          <select
            value={filterField}
            onChange={(e) => setFilterField(e.target.value)}
            className="bg-slate-900 border border-slate-700 px-2 py-1 rounded text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Fields</option>
            <option value="Nahorkatiya">Nahorkatiya</option>
            <option value="Tengakhat">Tengakhat</option>
            <option value="Borpothar">Borpothar</option>
          </select>
        </div>
      </div>

      {/* Offset Radius Control -- drag to redefine "nearby" for both the map
          circle and the well list/DORS table below, live. */}
      <div className="scada-panel px-4 py-3 flex items-center gap-4">
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
      </div>

      {/* Main Grid: Interactive GIS Map & Well List + Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left 2 Cols: Interactive SCADA Basin Map */}
        <div className="lg:col-span-2 scada-panel p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
              <Navigation className="w-4 h-4 text-cyan-400" />
              UPPER ASSAM BASIN SPATIAL CLUSTERING (27.15°N, 95.30°E)
            </div>
            <div className="text-[10px] font-mono text-slate-400 flex items-center gap-3">
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span> Active Well</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Offset Target</span>
              <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span> Catalog Well</span>
            </div>
          </div>

          {/* Real interactive map — Leaflet + free CartoDB dark tiles, real
              lat/lon projection, not a hand-rolled schematic. */}
          <div className="relative w-full h-[380px] rounded border border-slate-800 mt-2 overflow-hidden">
            <BasinMap
              wells={filteredWells}
              activeWellId={activeWellId}
              selectedWellId={selectedWellId}
              onSelectWell={setSelectedWellId}
              radiusKm={radiusKm}
            />
          </div>

          {/* DORS 5-Factor Ranking Table for Active Well */}
          <div className="mt-3">
            <div className="text-xs font-mono font-bold text-slate-300 pb-1.5">
              DORS 5-FACTOR OFFSET RELEVANCE RANKING (FOR {activeWellId})
            </div>
            <div className="overflow-x-auto max-h-48 border border-slate-800 rounded">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-slate-900 text-slate-400 text-[10px] uppercase border-b border-slate-800 sticky top-0">
                  <tr>
                    <th className="p-2">Rank</th>
                    <th className="p-2">Well ID</th>
                    <th className="p-2">Dist (km)</th>
                    <th className="p-2">Spatial</th>
                    <th className="p-2">Formation</th>
                    <th className="p-2">Depth</th>
                    <th className="p-2">Traj</th>
                    <th className="p-2">Composite Ω</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {dorsOffsets.map((o, idx) => (
                    <tr
                      key={o.well_id}
                      onClick={() => setSelectedWellId(o.well_id)}
                      className={`hover:bg-slate-800/50 cursor-pointer transition ${
                        selectedWellId === o.well_id ? 'bg-cyan-950/30 text-cyan-200' : ''
                      }`}
                    >
                      <td className="p-2 font-bold">{idx + 1}</td>
                      <td className="p-2 text-cyan-400 font-semibold">{o.well_id}</td>
                      <td className="p-2">{o.distance_km.toFixed(2)}</td>
                      <td className="p-2">{(o.component_scores.spatial * 100).toFixed(0)}%</td>
                      <td className="p-2">{(o.component_scores.formation * 100).toFixed(0)}%</td>
                      <td className="p-2">{(o.component_scores.depth * 100).toFixed(0)}%</td>
                      <td className="p-2">{(o.component_scores.trajectory * 100).toFixed(0)}%</td>
                      <td className="p-2 font-bold text-amber-400">{(o.dors_score * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Col: Selected Offset Well Detailed Dossier */}
        <div className="scada-panel p-4 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
                <FileText className="w-4 h-4 text-amber-400" />
                WELL DOSSIER: {selectedWell?.well_name}
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {selectedWell?.status}
              </span>
            </div>

            {/* Well Meta */}
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">TOTAL DEPTH</div>
                <div className="font-bold text-slate-100">{selectedWell?.total_depth_md_m} m MD</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">PROFILE</div>
                <div className="font-bold text-slate-100">{selectedWell?.well_type}</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">KB ELEVATION</div>
                <div className="font-bold text-slate-100">{selectedWell?.kb_elevation_m} m</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">OPERATOR</div>
                <div className="font-bold text-slate-100 truncate">{selectedWell?.operator}</div>
              </div>
            </div>

            {/* Formations Penetrated */}
            <div className="mt-3">
              <div className="text-xs font-mono text-slate-400 font-bold mb-1 flex items-center justify-between">
                <span>STRATIGRAPHIC TOPS</span>
                <span className="text-[10px] text-cyan-400">{selectedWellFormations.length} Formations</span>
              </div>
              <div className="max-h-36 overflow-y-auto space-y-1 text-xs font-mono border border-slate-800 rounded p-1">
                {selectedWellFormations.map((f) => (
                  <div key={f.formation_name} className="flex items-center justify-between p-1 bg-slate-900/50 rounded">
                    <span className="text-amber-300 font-semibold">{f.formation_name}</span>
                    <span className="text-slate-400">{f.top_tvd_m.toFixed(0)}m TVD</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Historical Drilling Hazards */}
            <div className="mt-3">
              <div className="text-xs font-mono text-slate-400 font-bold mb-1 flex items-center justify-between">
                <span>HISTORICAL NPT HAZARDS</span>
                <span className="text-[10px] text-rose-400">{selectedWellEvents.length} Events Logged</span>
              </div>
              <div className="max-h-40 overflow-y-auto space-y-1.5 text-xs font-mono border border-slate-800 rounded p-1">
                {selectedWellEvents.length > 0 ? (
                  selectedWellEvents.map((evt) => (
                    <div key={evt.event_id} className="p-2 bg-slate-900/70 border border-slate-800 rounded space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-rose-400 font-bold">{evt.event_type}</span>
                        <span className="text-[10px] bg-slate-800 text-slate-300 px-1 rounded">
                          {evt.depth_start_md_m}m MD
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300 leading-tight">{evt.raw_narrative || evt.outcome || 'No narrative recorded'}</div>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>IADC Code: {evt.iadc_npt_code || 'N/A'}</span>
                        <span className="text-cyan-400">{evt.formation}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-3 text-center text-slate-400 text-xs font-mono">
                    No severe drilling hazards reported for this well.
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => setShow3D(true)}
              className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 border border-cyan-500/40 text-cyan-300 font-bold text-xs font-mono rounded transition flex items-center justify-center gap-1.5"
            >
              <Box className="w-3.5 h-3.5" /> VIEW 3D TRAJECTORY
            </button>
            <button
              onClick={() => setActiveWellId(selectedWellId)}
              className="flex-1 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs font-mono rounded transition flex items-center justify-center gap-1.5 shadow-md shadow-cyan-600/30"
            >
              SET AS ACTIVE WELL
            </button>
          </div>
        </div>
      </div>

      {show3D && (
        <Suspense
          fallback={
            <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center text-slate-400 font-mono text-xs">
              Loading 3D viewer...
            </div>
          }
        >
          <WellInspector3DModal
            wellId={selectedWellId}
            wellName={selectedWell?.well_name || selectedWellId}
            offsetWellId={dorsOffsets[0]?.well_id !== selectedWellId ? dorsOffsets[0]?.well_id : dorsOffsets[1]?.well_id}
            offsetWellName={dorsOffsets[0]?.well_id !== selectedWellId ? dorsOffsets[0]?.well_id : dorsOffsets[1]?.well_id}
            onClose={() => setShow3D(false)}
          />
        </Suspense>
      )}
    </div>
  );
};
