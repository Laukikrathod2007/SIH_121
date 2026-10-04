import React, { useEffect, useState } from 'react';
import {
  Compass,
  Layers,
  Gauge,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { OffsetWellRanking, FormationTop, HorizonAlignmentEntry } from '../types';
import { Link } from 'react-router-dom';
import { LiveValue } from '../components/LiveValue';
import { MiniSparkline } from '../components/MiniSparkline';
import { BackendStatusStrip } from '../components/commandcenter/BackendStatusStrip';

export const DashboardPage: React.FC = () => {
  const {
    activeWellId,
    activeWell,
    telemetry,
    telemetryHistory,
    activeRisk,
    alerts,
    mitigateAlert,
    isWsConnected,
  } = useApp();

  const [offsetRankings, setOffsetRankings] = useState<OffsetWellRanking[]>([]);
  const [alignment, setAlignment] = useState<Record<string, HorizonAlignmentEntry>>({});
  const [activeFormations, setActiveFormations] = useState<FormationTop[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const depth = telemetry?.measured_depth_m || 2450.0;

  useEffect(() => {
    if (!activeWellId) return;
    let cancelled = false;
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [dorsRes, alignRes, formsRes] = await Promise.all([
          api.getOffsetRank(activeWellId, depth).catch(() => ({ rankings: [] as OffsetWellRanking[] })),
          api.getStratigraphicDepthTrack(activeWellId, depth).catch(() => ({ alignment: {} })),
          api.getFormations(activeWellId).catch(() => []),
        ]);
        if (cancelled) return;
        setOffsetRankings((dorsRes as any).rankings ?? []);
        setAlignment((alignRes as any).alignment ?? {});
        setActiveFormations(formsRes);
      } catch (err) {
        console.error('Error fetching dashboard summary', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchDashboardData();
    return () => { cancelled = true; };
  }, [activeWellId, Math.floor(depth / 20)]);

  const criticalAlert = alerts.find((a) => a.severity === 'CRITICAL' || a.severity === 'WARNING');

  const activeAlign = alignment[activeWellId];
  const activeFormation = activeFormations.find((f) => f.formation_name === activeAlign?.formation) || activeFormations[0];
  const currentXi = activeFormation && activeFormation.thickness_m > 0 && activeAlign?.d_strat_m != null
    ? Math.min(1, Math.max(0, activeAlign.d_strat_m / activeFormation.thickness_m))
    : null;

  const topOffset = offsetRankings[0];

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
              {loading ? 'LOADING' : 'ONLINE'}
            </span>
          </div>
          <div className="text-xl font-bold text-slate-100 flex items-center gap-2 mt-0.5">
            {activeWell ? activeWell.well_name : activeWellId}
            <span className="text-xs text-slate-400 font-normal">
              ({activeWell ? activeWell.field : '—'})
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">MEASURED DEPTH</div>
            <div className="text-base font-bold text-cyan-400">
              <LiveValue value={`${depth.toFixed(1)} m`} />
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">BIT TVDSS</div>
            <div className="text-base font-bold text-slate-200">
              {activeAlign?.tvdss_m != null ? activeAlign.tvdss_m.toFixed(1) : '—'} m
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">ACTIVE FORMATION</div>
            <div className="text-base font-bold text-amber-400 truncate max-w-[130px]">
              {activeFormation?.formation_name ?? '—'}
            </div>
          </div>
          <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded">
            <div className="text-slate-400 text-[10px]">STRATIGRAPHIC ξ</div>
            <div className="text-base font-bold text-emerald-400">
              {currentXi != null ? currentXi.toFixed(3) : 'n/a'}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Backend Connectivity Bus -- real health-checked strip (see
          BackendStatusStrip's own header comment); this used to be a
          hardcoded-green block that never reflected actual backend health,
          found during the core-integration pass (AUDIT/02_CORE_INTEGRATION.md). */}
      <BackendStatusStrip />

      {/* 3. Operational Critical Alert & Mitigation Card (If Active — module 03 placeholder) */}
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
              to="/app/alerts"
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded transition font-mono border border-slate-700"
            >
              DETAILS →
            </Link>
          </div>
        </div>
      )}

      {/* 4. Four Operational Quadrants */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Quadrant 1: WHERE ARE WE? */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-amber-400" />
                <span className="font-semibold text-sm text-slate-100">Stratigraphic Correlation</span>
              </div>
              <Link to="/app/correlation" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Full Cross-Section <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 space-y-3">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Formation Boundary Progress:</span>
                <span className="text-amber-300 font-bold">
                  {currentXi != null ? `${(currentXi * 100).toFixed(1)}% through interval` : 'n/a'}
                </span>
              </div>

              <div className="w-full bg-slate-900 h-4 rounded border border-slate-800 overflow-hidden relative">
                <div
                  className="h-full bg-gradient-to-r from-amber-600 via-yellow-500 to-amber-400 transition-all duration-500"
                  style={{ width: `${currentXi != null ? Math.min(100, Math.max(0, currentXi * 100)) : 0}%` }}
                ></div>
                <div className="absolute inset-0 flex items-center justify-between px-2 text-[10px] font-mono text-slate-300 pointer-events-none">
                  <span>Top (ξ=0.0)</span>
                  <span>Mid (ξ=0.5)</span>
                  <span>Base (ξ=1.0)</span>
                </div>
              </div>

              {topOffset && (
                <div className="bg-slate-900/80 border border-slate-800/80 p-2.5 rounded text-xs space-y-1 font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Top Correlated Offset (DORS):</span>
                    <span className="text-cyan-400 font-bold">{topOffset.well_id}</span>
                  </div>
                  <div className="flex items-center justify-between text-slate-300">
                    <span>Formation Match:</span>
                    <span className="text-slate-100 font-bold">{topOffset.formation_match}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Source: GET /api/v2/stratigraphic_depth_track</span>
            <span className="text-emerald-400 font-semibold">Live</span>
          </div>
        </div>

        {/* Quadrant 2: WHAT IS AROUND US? (DORS) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Compass className="w-4 h-4 text-cyan-400" />
                <span className="font-semibold text-sm text-slate-100">Nearby Offset Wells (DORS)</span>
              </div>
              <Link to="/app/wells" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Field GIS Map <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 space-y-2">
              {offsetRankings.slice(0, 3).map((offset) => (
                <div
                  key={offset.well_id}
                  className="bg-slate-900/70 border border-slate-800 p-2 rounded flex items-center justify-between text-xs font-mono"
                >
                  <div className="flex items-center space-x-2.5">
                    <span className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-bold text-[10px]">
                      {offset.rank}
                    </span>
                    <div>
                      <div className="font-bold text-slate-200">{offset.well_id}</div>
                      <div className="text-[10px] text-slate-400">{offset.distance_km.toFixed(2)} km away</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-cyan-400 font-bold">DORS: {(offset.dors_score * 100).toFixed(1)}%</div>
                    <div className="text-[10px] text-amber-400">{offset.events_in_lookahead} NPT Events</div>
                  </div>
                </div>
              ))}
              {offsetRankings.length === 0 && (
                <div className="text-xs font-mono text-slate-500 p-2">No offset wells ranked yet.</div>
              )}
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>DORS 5-Factor: Spatial, Formation, Depth, Trajectory, Hazard</span>
            <span className="text-cyan-400">GET /api/v2/offset_rank</span>
          </div>
        </div>

        {/* Quadrant 3: WHAT IS HAPPENING NOW? (Live Telemetry — module 03 placeholder) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Gauge className="w-4 h-4 text-emerald-400" />
                <span className="font-semibold text-sm text-slate-100">Live Drilling Cockpit</span>
              </div>
              <Link to="/app/drilling" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Full Cockpit <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="mt-3 grid grid-cols-3 gap-2 text-xs font-mono">
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="text-slate-400 text-[10px]">ROP</div>
                  <MiniSparkline data={telemetryHistory.slice(-30).map((t) => t.rop_m_hr)} color="#10b981" width={44} height={16} />
                </div>
                <div className="text-sm font-bold text-slate-100"><LiveValue value={`${telemetry?.rop_m_hr.toFixed(1) ?? '—'} m/hr`} /></div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="text-slate-400 text-[10px]">TORQUE</div>
                  <MiniSparkline data={telemetryHistory.slice(-30).map((t) => t.torque_knm)} color="#f59e0b" width={44} height={16} />
                </div>
                <div className="text-sm font-bold text-slate-100"><LiveValue value={`${telemetry?.torque_knm.toFixed(1) ?? '—'} kN·m`} /></div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="text-slate-400 text-[10px]">SPP</div>
                  <MiniSparkline data={telemetryHistory.slice(-30).map((t) => t.standpipe_pressure_bar)} color="#a855f7" width={44} height={16} />
                </div>
                <div className="text-sm font-bold text-slate-100"><LiveValue value={`${telemetry?.standpipe_pressure_bar.toFixed(1) ?? '—'} bar`} /></div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">FLOW IN/OUT</div>
                <div className="text-sm font-bold text-slate-100">
                  <LiveValue value={telemetry?.flow_in_lpm.toFixed(0) ?? '—'} /> / <LiveValue value={telemetry?.flow_out_lpm.toFixed(0) ?? '—'} />
                </div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">PIT VOLUME</div>
                <div className="text-sm font-bold text-slate-100"><LiveValue value={`${telemetry?.pit_volume_m3.toFixed(2) ?? '—'} m³`} /></div>
              </div>
              <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                <div className="text-slate-400 text-[10px]">ECD</div>
                <div className="text-sm font-bold text-slate-100"><LiveValue value={`${telemetry?.ecd_gcc.toFixed(2) ?? '—'} g/cc`} /></div>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span className="flex items-center gap-1 text-slate-400">
              <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-emerald-400' : 'bg-slate-500'}`}></span>
              Physics Digital Twin (module 04/05, /api/v3)
            </span>
            <span className="text-slate-300">{isWsConnected ? 'Connected' : 'Not connected — start the simulator'}</span>
          </div>
        </div>

        {/* Quadrant 4: WHAT COULD GO WRONG? (module 03 placeholder) */}
        <div className="scada-panel p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span className="font-semibold text-sm text-slate-100">Multi-Signal Hazard Forecast</span>
              </div>
              <Link to="/app/risk" className="text-xs font-mono text-cyan-400 hover:underline flex items-center gap-1">
                Risk Details <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            {activeRisk ? (
              <div className="mt-3 space-y-2">
                {['LOST_CIRCULATION', 'KICK', 'STUCK_PIPE', 'TORQUE_DRAG'].map((hazard) => {
                  const score = activeRisk?.fused_hazard_scores[hazard] || 0;
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
            ) : (
              <div className="mt-3 text-xs font-mono text-slate-500 p-2 bg-slate-900/60 rounded border border-slate-800">
                No live hazard forecast yet — module 04/05's risk-fusion engine (real, served at /api/v3) only
                evaluates once live telemetry is flowing. Start the simulator (Scenario Simulator page) to see
                real fused hazard scores here.
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Predictive ML fusion (module 04/05, /api/v3)</span>
            <span className="text-cyan-400">{activeRisk ? 'Live' : 'Idle — simulator not running'}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
