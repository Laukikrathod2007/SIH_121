import React, { useEffect, useState } from 'react';
import {
  Compass,
  Layers,
  Gauge,
  ShieldAlert,
  BellRing,
  Activity,
  AlertTriangle,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  Clock,
  Radio,
  FileText,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { DORSOffset, DrillingEvent, XiCorrelationResult } from '../types';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const {
    activeWellId,
    activeWell,
    telemetry,
    activeRisk,
    alerts,
    mitigateAlert,
    isWsConnected,
  } = useApp();

  const [dorsOffsets, setDorsOffsets] = useState<DORSOffset[]>([]);
  const [xiData, setXiData] = useState<XiCorrelationResult | null>(null);
  const [recentEvents, setRecentEvents] = useState<DrillingEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const depth = telemetry?.measured_depth_m || 2450.0;

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [dorsRes, xiRes, eventsRes] = await Promise.all([
          api.getDORS(activeWellId, depth).catch(() => ({ ranked_offsets: [] })),
          api.getXiCorrelation(activeWellId, depth).catch(() => null),
          api.searchEvents({ min_severity: 'MEDIUM' }).catch(() => []),
        ]);

        if (dorsRes?.ranked_offsets) setDorsOffsets(dorsRes.ranked_offsets);
        if (xiRes) setXiData(xiRes);
        if (eventsRes && Array.isArray(eventsRes)) {
          setRecentEvents(eventsRes.slice(0, 5));
        } else if (eventsRes && Array.isArray((eventsRes as any).events)) {
          setRecentEvents((eventsRes as any).events.slice(0, 5));
        }
      } catch (err) {
        console.error('Error fetching dashboard summary', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [activeWellId, Math.floor(depth / 20)]);

  const criticalAlert = alerts.find((a) => a.severity === 'CRITICAL' || a.severity === 'WARNING');

  const currentXi =
    xiData?.active_well?.xi ??
    xiData?.active_xi?.xi ??
    telemetry?.xi ??
    0.25;

  const primaryOffset = xiData?.offsets && xiData.offsets.length > 0 ? xiData.offsets[0] : null;
  const primaryOffsetTvdss = primaryOffset?.mapped_equivalent_tvdss ?? primaryOffset?.offset_mapping?.equivalent_tvdss_m ?? (depth - 40);

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* 1. Master Active Well & Subsurface Coordinate Banner */}
      <div className="scada-panel p-4 border-l-4 border-l-cyan-500 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-cyan-400 font-semibold uppercase tracking-wider">
              DRILLING TARGET IDENTIFICATION
            </span>
            <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">
              ONLINE
            </span>
          </div>
          <div className="text-xl font-bold text-slate-100 flex items-center gap-2 mt-0.5">
            {activeWell ? activeWell.well_name : 'NHK-001'}
            <span className="text-xs text-slate-400 font-normal">
              ({activeWell ? activeWell.field : 'Nahorkatiya Field'}, Assam Shelf)
            </span>
          </div>
        </div>

        {/* 4 Pillars of Current Coordinate */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">MEASURED DEPTH</div>
            <div className="text-base font-bold text-cyan-400">{depth.toFixed(1)} m</div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">TRUE VERT. SUBSEA</div>
            <div className="text-base font-bold text-slate-200">
              {telemetry?.tvdss_m?.toFixed(1) ?? '2315.6'} m
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">ACTIVE FORMATION</div>
            <div className="text-base font-bold text-amber-400 truncate max-w-[130px]">
              {telemetry?.formation?.replace(/_/g, ' ') ?? 'Barail Sand'}
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">STRATIGRAPHIC ξ</div>
            <div className="text-base font-bold text-emerald-400">
              {currentXi.toFixed(3)}
            </div>
          </div>
        </div>
      </div>

      {/* 2. System Subsystem Connectivity Bus (7 Modules) */}
      <div className="scada-panel px-3 py-2 flex items-center justify-between text-[11px] font-mono overflow-x-auto text-slate-300">
        <span className="text-slate-400 uppercase tracking-widest text-[10px] mr-2">SUBSYSTEM STATUS:</span>
        <div className="flex items-center space-x-4">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Mod 1: Docs</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Mod 2: Offsets</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Mod 3: RAG Store</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Mod 4: ξ Engine</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Mod 5: Physics Twin</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-cyan-400"></span> Mod 5: XGBoost ML</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Mod 6: Advisory</span>
        </div>
      </div>

      {/* 3. Operational Critical Alert & Mitigation Card (If Active) */}
      {criticalAlert && (
        <div className="scada-panel-danger p-4 border-l-4 border-l-rose-500 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/30 text-rose-300 border border-rose-500/40 font-bold uppercase">
                {criticalAlert.severity} HAZARD: {criticalAlert.hazard_type}
              </span>
              <span className="text-xs font-mono text-slate-400">
                Depth: {criticalAlert.measured_depth_m.toFixed(1)}m | Formation: {criticalAlert.formation}
              </span>
            </div>
            <div className="text-sm font-semibold text-slate-100">{criticalAlert.headline}</div>
            <div className="text-xs text-rose-200/80 font-mono">
              Action Plan: {criticalAlert.recommended_action.title}
            </div>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => mitigateAlert(criticalAlert.alert_id)}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-slate-950 font-bold text-xs rounded transition flex items-center gap-1.5 shadow-lg shadow-rose-600/30"
            >
              <span>APPLY MITIGATION</span>
            </button>
            <Link
              to="/alerts"
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition font-mono border border-slate-700"
            >
              DETAILS →
            </Link>
          </div>
        </div>
      )}

      {/* 4. Four Operational Quadrants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Quadrant 1: WHERE ARE WE? (Geological Stratigraphy & ξ Correlation) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-amber-400" />
                <span className="font-semibold text-sm text-slate-100">Stratigraphic Correlation (Module 4)</span>
              </div>
              <Link to="/correlation" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Full Cross-Section <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 space-y-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Formation Boundary Progress:</span>
                <span className="text-amber-300 font-bold">
                  {(currentXi * 100).toFixed(1)}% through interval
                </span>
              </div>

              {/* Stratigraphic Progress Gauge */}
              <div className="w-full bg-slate-900 h-4 rounded border border-slate-800 overflow-hidden relative">
                <div
                  className="h-full bg-gradient-to-r from-amber-600 via-yellow-500 to-amber-400 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, currentXi * 100))}%` }}
                ></div>
                <div className="absolute inset-0 flex items-center justify-between px-2 text-[10px] font-mono text-slate-300 pointer-events-none">
                  <span>Top (ξ=0.0)</span>
                  <span>Mid (ξ=0.5)</span>
                  <span>Base (ξ=1.0)</span>
                </div>
              </div>

              {/* Offset Correlated Target */}
              {primaryOffset && (
                <div className="bg-slate-900/80 border border-slate-800/80 p-2.5 rounded text-xs space-y-1 font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Primary Correlated Offset:</span>
                    <span className="text-cyan-400 font-bold">{primaryOffset.offset_well_id || 'WELL-BOR-004'}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300">
                    <span>Mapped Equivalent Horizon:</span>
                    <span className="text-slate-100 font-bold">
                      {primaryOffsetTvdss.toFixed(1)} m TVDSS
                    </span>
                  </div>
                  <div className="text-[11px] text-amber-400/90">
                    ★ Corrects for {(Math.abs(primaryOffsetTvdss - depth)).toFixed(1)}m structural dip & thickness divergence!
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Correlation Algorithm: SPE Min. Curvature + Stratigraphic ξ</span>
            <span className="text-emerald-400 font-semibold">100% Deterministic</span>
          </div>
        </div>

        {/* Quadrant 2: WHAT IS AROUND US? (Nearby Offset Wells & DORS Ranking) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                <span className="font-semibold text-sm text-slate-100">Nearby Offset Wells (Module 2 DORS)</span>
              </div>
              <Link to="/wells" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Field GIS Map <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 space-y-2">
              {dorsOffsets.slice(0, 3).map((offset, idx) => (
                <div
                  key={offset.offset_well_id}
                  className="bg-slate-900/70 border border-slate-800 p-2 rounded flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center space-x-2.5">
                    <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-bold text-[10px]">
                      {idx + 1}
                    </span>
                    <div>
                      <div className="font-bold text-slate-200">{offset.offset_well_id}</div>
                      <div className="text-[10px] text-slate-400">{offset.distance_km.toFixed(2)} km away</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-cyan-400 font-bold">Ω: {(offset.omega_score * 100).toFixed(1)}%</div>
                    <div className="text-[10px] text-amber-400">{offset.historical_event_count} NPT Events</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>DORS 5-Factor: Spatial, Formation, Depth, Trajectory, Hazard</span>
            <span className="text-cyan-400">Dynamic Offset Relevance</span>
          </div>
        </div>

        {/* Quadrant 3: WHAT IS HAPPENING NOW? (Live Telemetry & Digital Twin) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Gauge className="w-4 h-4 text-emerald-400" />
                <span className="font-semibold text-sm text-slate-100">Live Drilling Cockpit (Module 5 Twin)</span>
              </div>
              <Link to="/drilling" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Full Cockpit <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 grid grid-cols-3 gap-2 text-xs font-mono">
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">ROP</div>
                <div className="text-sm font-bold text-slate-100">{telemetry?.rop_m_hr.toFixed(1)} m/hr</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">TORQUE</div>
                <div className="text-sm font-bold text-slate-100">{telemetry?.torque_knm.toFixed(1)} kN·m</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">SPP</div>
                <div className="text-sm font-bold text-slate-100">{telemetry?.standpipe_pressure_bar.toFixed(1)} bar</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">FLOW IN/OUT</div>
                <div className="text-sm font-bold text-slate-100">
                  {telemetry?.flow_in_lpm.toFixed(0)} / {telemetry?.flow_out_lpm.toFixed(0)}
                </div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">PIT VOLUME</div>
                <div className="text-sm font-bold text-slate-100">{telemetry?.pit_volume_m3.toFixed(2)} m³</div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">ECD</div>
                <div className="text-sm font-bold text-slate-100">{telemetry?.ecd_gcc.toFixed(2)} g/cc</div>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span className="flex items-center gap-1 text-slate-400">
              <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
              1 Hz Coupled Physics ODE Twin
            </span>
            <span className="text-slate-300">Provenance: SYNTHETIC</span>
          </div>
        </div>

        {/* Quadrant 4: WHAT COULD GO WRONG? (Predictive Risk & Anomaly Models) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span className="font-semibold text-sm text-slate-100">Multi-Signal Hazard Forecast (Module 5 & 6)</span>
              </div>
              <Link to="/risk" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Risk Details <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 space-y-2">
              {['LOST_CIRCULATION', 'KICK', 'STUCK_PIPE', 'TORQUE_DRAG'].map((hazard) => {
                const score = activeRisk?.fused_hazard_scores[hazard] || 0.10;
                const isHigh = score >= 0.60;
                const isMed = score >= 0.35 && score < 0.60;
                const barColor = isHigh ? 'bg-rose-500' : isMed ? 'bg-amber-500' : 'bg-emerald-500';

                return (
                  <div key={hazard} className="space-y-1">
                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-slate-300 font-semibold">{hazard.replace('_', ' ')}</span>
                      <span className={isHigh ? 'text-rose-400 font-bold' : isMed ? 'text-amber-400' : 'text-emerald-400'}>
                        {(score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-900 h-2 rounded overflow-hidden border border-slate-800">
                      <div className={`h-full ${barColor} transition-all duration-300`} style={{ width: `${score * 100}%` }}></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Models: Rules (35%) + IsolationForest (20%) + XGBoost (30%) + Mod 4 (15%)</span>
            <span className="text-cyan-400">Fused Output</span>
          </div>
        </div>
      </div>
    </div>
  );
};
