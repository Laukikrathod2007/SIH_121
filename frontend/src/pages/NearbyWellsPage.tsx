import React, { useState, useEffect } from 'react';
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
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { Well, DORSOffset, FormationTop, DrillingEvent } from '../types';

export const NearbyWellsPage: React.FC = () => {
  const { activeWellId, setActiveWellId, wells, activeWell, telemetry } = useApp();

  const [dorsOffsets, setDorsOffsets] = useState<DORSOffset[]>([]);
  const [selectedWellId, setSelectedWellId] = useState<string>('WELL-NHK-002');
  const [selectedWellFormations, setSelectedWellFormations] = useState<FormationTop[]>([]);
  const [selectedWellEvents, setSelectedWellEvents] = useState<DrillingEvent[]>([]);
  const [filterField, setFilterField] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const depth = telemetry?.measured_depth_m || 2450.0;

  // Load DORS offsets for active well
  useEffect(() => {
    const fetchDors = async () => {
      try {
        const res = await api.getDORS(activeWellId, depth);
        if (res && res.ranked_offsets) {
          setDorsOffsets(res.ranked_offsets);
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
    return matchesField && matchesSearch;
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
              Upper Assam Shelf | Total Catalog: {wells.length} Wells | Active Radius: 25 km
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

          {/* Basin SVG Surface Map */}
          <div className="relative w-full h-[380px] bg-[#090c12] rounded border border-slate-800 mt-2 overflow-hidden flex items-center justify-center">
            <svg viewBox="0 0 800 450" className="w-full h-full select-none">
              {/* Grid Lines */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#131c2e" strokeWidth="1" />
                </pattern>
              </defs>
              <rect width="800" height="450" fill="url(#grid)" />

              {/* Tectonic Fault Lines */}
              <path
                d="M 120 40 Q 350 200 680 380"
                fill="none"
                stroke="#dc2626"
                strokeWidth="2"
                strokeDasharray="6 4"
                opacity="0.6"
              />
              <text x="580" y="340" fill="#ef4444" fontSize="10" fontFamily="monospace">
                Naga Thrust Fault Barrier (β = 0.20)
              </text>

              {/* Distance Concentric Circles from Active Well */}
              <circle cx="360" cy="220" r="80" fill="none" stroke="#06b6d4" strokeWidth="1" strokeDasharray="3 3" opacity="0.3" />
              <text x="365" y="145" fill="#0891b2" fontSize="9" fontFamily="monospace">5 km</text>
              <circle cx="360" cy="220" r="160" fill="none" stroke="#06b6d4" strokeWidth="1" strokeDasharray="3 3" opacity="0.2" />
              <text x="365" y="65" fill="#0891b2" fontSize="9" fontFamily="monospace">15 km</text>

              {/* Well Pins */}
              {wells.map((w, idx) => {
                const isActive = w.well_id === activeWellId;
                const isSelected = w.well_id === selectedWellId;

                // Project GPS (lat ~27.1-27.3, lon ~95.2-95.4) to 800x450
                const cx = 360 + ((w.surface_lon - 95.29) * 2200);
                const cy = 220 - ((w.surface_lat - 27.18) * 1800);

                return (
                  <g
                    key={w.well_id}
                    onClick={() => setSelectedWellId(w.well_id)}
                    className="cursor-pointer transition-transform hover:scale-110"
                  >
                    {isActive ? (
                      <>
                        <circle cx={cx} cy={cy} r="14" fill="#06b6d4" opacity="0.2" className="pulse-green" />
                        <circle cx={cx} cy={cy} r="7" fill="#06b6d4" stroke="#e0f2fe" strokeWidth="2" />
                        <text x={cx + 10} y={cy + 4} fill="#38bdf8" fontSize="11" fontWeight="bold" fontFamily="monospace">
                          {w.well_name} (ACTIVE)
                        </text>
                      </>
                    ) : isSelected ? (
                      <>
                        <circle cx={cx} cy={cy} r="10" fill="#f59e0b" opacity="0.3" />
                        <circle cx={cx} cy={cy} r="6" fill="#f59e0b" stroke="#fef3c7" strokeWidth="2" />
                        <text x={cx + 8} y={cy + 3} fill="#fbbf24" fontSize="10" fontWeight="bold" fontFamily="monospace">
                          {w.well_name}
                        </text>
                      </>
                    ) : (
                      <>
                        <circle cx={cx} cy={cy} r="4.5" fill="#475569" stroke="#64748b" strokeWidth="1" />
                        <text x={cx + 7} y={cy + 3} fill="#94a3b8" fontSize="9" fontFamily="monospace">
                          {w.well_name}
                        </text>
                      </>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Basin Info Overlay */}
            <div className="absolute bottom-2 left-2 bg-slate-900/90 border border-slate-800 p-2 rounded text-[10px] font-mono text-slate-400 space-y-0.5 pointer-events-none">
              <div>FIELD: Nahorkatiya & Greater Assam Shelf</div>
              <div>GEOLOGICAL PROVINCE: Upper Assam Shelf / Brahmaputra Basin</div>
              <div>REGIONAL DIP: 3.5° SE towards Naga Fold Belt</div>
            </div>
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
                      key={o.offset_well_id}
                      onClick={() => setSelectedWellId(o.offset_well_id)}
                      className={`hover:bg-slate-800/50 cursor-pointer transition ${
                        selectedWellId === o.offset_well_id ? 'bg-cyan-950/30 text-cyan-200' : ''
                      }`}
                    >
                      <td className="p-2 font-bold">{idx + 1}</td>
                      <td className="p-2 text-cyan-400 font-semibold">{o.offset_well_id}</td>
                      <td className="p-2">{o.distance_km.toFixed(2)}</td>
                      <td className="p-2">{(o.component_scores.spatial * 100).toFixed(0)}%</td>
                      <td className="p-2">{(o.component_scores.formation * 100).toFixed(0)}%</td>
                      <td className="p-2">{(o.component_scores.depth * 100).toFixed(0)}%</td>
                      <td className="p-2">{(o.component_scores.trajectory * 100).toFixed(0)}%</td>
                      <td className="p-2 font-bold text-amber-400">{(o.omega_score * 100).toFixed(1)}%</td>
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
                    <span className="text-slate-400">{f.top_tvdss_m != null ? f.top_tvdss_m.toFixed(0) : f.top_md_m.toFixed(0)}m {f.top_tvdss_m != null ? 'TVDSS' : 'MD'}</span>
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
                        <span className="text-rose-400 font-bold">{evt.hazard_type}</span>
                        <span className="text-[10px] bg-slate-800 text-slate-300 px-1 rounded">
                          {evt.depth_md_m}m MD
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-300 leading-tight">{evt.description}</div>
                      <div className="text-[10px] text-slate-400 flex items-center justify-between">
                        <span>IADC Code: {evt.iadc_code || 'N/A'}</span>
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

          <button
            onClick={() => setActiveWellId(selectedWellId)}
            className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs font-mono rounded transition flex items-center justify-center gap-1.5 shadow-md shadow-cyan-600/30"
          >
            SET AS ACTIVE WELL FOR DRILLING
          </button>
        </div>
      </div>
    </div>
  );
};
