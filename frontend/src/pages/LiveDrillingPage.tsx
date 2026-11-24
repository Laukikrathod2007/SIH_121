import React, { useMemo, useState, useEffect, lazy, Suspense } from 'react';
import { Gauge, Play, Pause, RotateCcw, StepForward, Box, Radar, Clock, AlertTriangle, Layers, ChevronRight, ShieldAlert } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { StripChart, StripSeries } from '../components/StripChart';
import { WellCutawayCockpit } from '../components/WellCutawayCockpit';
import { WellTrajectory, FormationTop } from '../types';

// Lazy-loaded: pulls in three.js (~800kB), only needed once mounted.
const LiveDrillingScene3D = lazy(() =>
  import('../components/LiveDrillingScene3D').then((m) => ({ default: m.LiveDrillingScene3D }))
);

const FLOW_SERIES: StripSeries[] = [
  { key: 'flow_in', label: 'Flow In (LPM)', color: '#06b6d4' },
  { key: 'flow_out', label: 'Flow Out (LPM)', color: '#10b981' },
  { key: 'pit_volume', label: 'Pit Vol (m³)', color: '#a855f7', axis: 'right', dashed: true },
];
const PRESSURE_SERIES: StripSeries[] = [
  { key: 'spp', label: 'SPP (bar)', color: '#38bdf8', width: 1.5 },
  { key: 'bhp', label: 'BHP (bar)', color: '#eab308', width: 2.5 },
  { key: 'pore_pressure', label: 'Pore Press (bar)', color: '#ec4899', dashed: true, width: 1.5 },
  { key: 'frac_pressure', label: 'Frac Press (bar)', color: '#ef4444', dashed: true, width: 1.5 },
];
const TORSION_SERIES: StripSeries[] = [
  { key: 'torque', label: 'Torque (kN·m)', color: '#f43f5e' },
  { key: 'rpm', label: 'Surface RPM', color: '#3b82f6', axis: 'right' },
];
const ROP_SERIES: StripSeries[] = [
  { key: 'rop', label: 'ROP (m/hr)', color: '#10b981' },
  { key: 'wob', label: 'WOB (kN)', color: '#6366f1', axis: 'right', dashed: true },
];

export const LiveDrillingPage: React.FC = () => {
  const {
    activeWellId,
    activeWell,
    telemetry,
    telemetryHistory,
    activeRisk,
    simStatus,
    startSim,
    pauseSim,
    stepSim,
    resetSim,
    setSimSpeed,
    injectScenario,
    telemetryRateHz,
    telemetryLatencyMs,
  } = useApp();

  const [trajectory3D, setTrajectory3D] = useState<WellTrajectory | null>(null);
  const [formations3D, setFormations3D] = useState<FormationTop[]>([]);
  const [show3DLive, setShow3DLive] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.getTrajectory(activeWellId).catch(() => null),
      api.getFormations(activeWellId).catch(() => []),
    ]).then(([traj, forms]) => {
      if (cancelled) return;
      setTrajectory3D(traj);
      setFormations3D(forms);
    });
    return () => { cancelled = true; };
  }, [activeWellId]);

  const chartData = useMemo(() => {
    return telemetryHistory.map((t, idx) => ({
      t: t.sim_time_s ?? idx,
      depth: t.measured_depth_m,
      flow_in: t.flow_in_lpm,
      flow_out: t.flow_out_lpm,
      delta_flow: t.delta_flow,
      pit_volume: t.pit_volume_m3,
      spp: t.standpipe_pressure_bar,
      bhp: t.bottomhole_pressure_bar,
      pore_pressure: t.pore_pressure_bar,
      frac_pressure: t.fracture_pressure_bar,
      torque: t.torque_knm,
      rpm: t.rpm,
      rop: t.rop_m_hr,
      wob: t.wob_kn,
      ssi: t.stick_slip_index,
    }));
  }, [telemetryHistory]);

  const activeScenario = simStatus?.active_scenarios
    ? Object.keys(simStatus.active_scenarios)[0] || 'NORMAL'
    : 'NORMAL';

  const currentDepth = telemetry?.measured_depth_m || 2450.0;
  const currentRop = telemetry?.rop_m_hr || 25.0;

  // Ahead-of-bit stratigraphic projection (50m - 150m ahead of bit)
  const sortedFormations = useMemo(() => {
    return [...formations3D].sort((a, b) => a.top_tvd_m - b.top_tvd_m);
  }, [formations3D]);

  const activeFormation = sortedFormations.find(
    (f) => currentDepth >= f.top_tvd_m && currentDepth <= (f.top_tvd_m + f.thickness_m)
  ) || sortedFormations[0];

  const nextFormation = sortedFormations.find(
    (f) => f.top_tvd_m > currentDepth
  );

  const distToNextM = nextFormation ? nextFormation.top_tvd_m - currentDepth : null;
  const leadTimeMin = distToNextM != null ? (distToNextM / Math.max(currentRop, 1)) * 60 : null;

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* 1. Cockpit Header & Simulator Real-Time Controls */}
      <div className="scada-panel p-3 flex flex-wrap items-center justify-between gap-3 border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              REAL-TIME DRILLING COCKPIT & SENSOR GAUGES
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                {telemetryRateHz} Hz TELEMETRY BUS
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Provenance: <span className="text-amber-400">SYNTHETIC (NWIS Coupled Physics ODE Twin)</span> | Latency:{' '}
              {telemetryLatencyMs != null ? `${telemetryLatencyMs} ms` : '—'} | Bit MD:{' '}
              <span className="text-cyan-300">{telemetry?.measured_depth_m.toFixed(3)} m</span>
            </div>
          </div>
        </div>

        {/* Live Simulator Toolbar */}
        <div className="flex items-center space-x-2 bg-slate-900/90 border border-slate-700 p-1.5 rounded">
          <span className="text-[10px] font-mono text-slate-400 px-2 uppercase">SIM ENGINE:</span>
          {simStatus?.is_running ? (
            <button
              onClick={pauseSim}
              className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded text-xs font-mono font-bold flex items-center gap-1 transition"
            >
              <Pause className="w-3.5 h-3.5" /> PAUSE
            </button>
          ) : (
            <button
              onClick={startSim}
              className="px-2.5 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 rounded text-xs font-mono font-bold flex items-center gap-1 transition"
            >
              <Play className="w-3.5 h-3.5 fill-current" /> RUN
            </button>
          )}

          <button
            onClick={stepSim}
            className="p-1 hover:bg-slate-800 text-slate-300 rounded transition"
            title="Step 1 Second"
          >
            <StepForward className="w-4 h-4" />
          </button>

          <button
            onClick={() => resetSim()}
            className="p-1 hover:bg-slate-800 text-slate-300 rounded transition"
            title="Reset Simulator to 2500m"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Speed Selector */}
          <div className="flex items-center pl-2 border-l border-slate-700 space-x-1">
            {[1, 2, 5, 10, 20].map((spd) => (
              <button
                key={spd}
                onClick={() => setSimSpeed(spd)}
                className={`px-1.5 py-0.5 rounded text-[11px] font-mono ${
                  simStatus?.speed_multiplier === spd
                    ? 'bg-cyan-500 text-slate-950 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 1.5. Real Cutaway Cockpit -- earth cross-section, real formation
          bands, real wellbore path, real live bit position, real INC/AZI
          survey track. Replaces the flat metric-only opening view. */}
      <WellCutawayCockpit
        wellId={activeWellId}
        wellName={activeWell?.well_name || activeWellId}
        telemetry={telemetry}
        activeRisk={activeRisk}
      />

      {/* 1.55. Outcome vi: Proactive Ahead-of-Bit Lookahead Radar (50m - 150m Corridor) */}
      <div className="scada-panel p-3 border-l-4 border-l-cyan-500 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Radar className="w-5 h-5 animate-spin" style={{ animationDuration: '6s' }} />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-100 flex items-center gap-2">
              <span>AHEAD-OF-BIT GEOLOGICAL RADAR (50m–150m LOOKAHEAD)</span>
              <span className="text-[10px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 px-1.5 py-0.2 rounded">
                OUTCOME VI PROACTIVE
              </span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
              <span>Active Horizon: <strong className="text-amber-300">{activeFormation?.formation_name || 'Alluvium'}</strong></span>
              <ChevronRight className="w-3 h-3 text-slate-600" />
              <span>
                Next Boundary:{' '}
                {nextFormation ? (
                  <strong className="text-cyan-300">{nextFormation.formation_name} (@ {nextFormation.top_tvd_m.toFixed(0)}m TVD)</strong>
                ) : (
                  <span className="text-slate-500">Terminal Depth Reached</span>
                )}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {distToNextM != null && (
            <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
              <span className="text-slate-400 text-[10px]">DISTANCE TO TRANSITION:</span>
              <span className="font-bold text-cyan-400 text-sm">{distToNextM.toFixed(1)} m</span>
            </div>
          )}
          {leadTimeMin != null && (
            <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span className="text-slate-400 text-[10px]">DYNAMIC LEAD TIME (ΔD/ROP):</span>
              <span className="font-bold text-amber-300 text-sm">{leadTimeMin.toFixed(0)} min</span>
              <span className="text-[10px] text-slate-500">(@ {currentRop.toFixed(1)} m/h)</span>
            </div>
          )}
          <div className="bg-slate-950 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-slate-400 text-[10px]">OFFSET ADVISORY:</span>
            <span className="text-rose-300 font-semibold text-[11px]">
              {nextFormation?.formation_name.includes('Barail')
                ? 'Narrow MW Window (10.4-11.2 ppg)'
                : nextFormation?.formation_name.includes('Kopili')
                ? 'High Sloughing Shale Pack-Off Risk'
                : 'Maintain Baseline ECD & Flow Monitoring'}
            </span>
          </div>
        </div>
      </div>

      {/* 1.6. Live 3D Rig View -- real trajectory, real formations, real
          live bit position (moves with the actual telemetry WebSocket
          stream), switchable camera perspectives (Rig Floor / Cross-
          Section / Downhole Follow / Free Orbit). */}
      <div className="scada-panel overflow-hidden">
        <div className="px-4 py-2.5 flex items-center justify-between border-b border-slate-800 bg-slate-900/60">
          <div className="flex items-center gap-2 text-xs font-mono">
            <Box className="w-4 h-4 text-cyan-400" />
            <span className="font-bold text-slate-200 uppercase">Live 3D Rig View</span>
          </div>
          <button
            onClick={() => setShow3DLive(!show3DLive)}
            className="text-[10px] font-mono text-slate-400 hover:text-slate-200 border border-slate-700 rounded px-2 py-1"
          >
            {show3DLive ? 'Hide' : 'Show'}
          </button>
        </div>
        {show3DLive && (
          <div className="h-[460px]">
            <Suspense fallback={<div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">Loading 3D scene...</div>}>
              <LiveDrillingScene3D
                trajectory={trajectory3D}
                formations={formations3D}
                telemetry={telemetry}
                wellName={activeWell?.well_name || activeWellId}
              />
            </Suspense>
          </div>
        )}
      </div>

      {/* 2. Top Metric Cards (16 Industrial Channels) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
        <div className="scada-panel p-2.5 border-t-2 border-t-cyan-500">
          <div className="text-[10px] font-mono text-slate-400">ROP</div>
          <div className="text-lg font-bold font-mono text-cyan-400">{telemetry?.rop_m_hr.toFixed(1)}</div>
          <div className="text-[10px] font-mono text-slate-400">m/hr</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-cyan-500">
          <div className="text-[10px] font-mono text-slate-400">WOB</div>
          <div className="text-lg font-bold font-mono text-slate-100">{telemetry?.wob_kn.toFixed(0)}</div>
          <div className="text-[10px] font-mono text-slate-400">kN</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-amber-500">
          <div className="text-[10px] font-mono text-slate-400">SURFACE RPM</div>
          <div className="text-lg font-bold font-mono text-amber-300">{telemetry?.rpm.toFixed(0)}</div>
          <div className="text-[10px] font-mono text-slate-400">RPM</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-amber-500">
          <div className="text-[10px] font-mono text-slate-400">TORQUE</div>
          <div className="text-lg font-bold font-mono text-amber-400">{telemetry?.torque_knm.toFixed(1)}</div>
          <div className="text-[10px] font-mono text-slate-400">kN·m</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-emerald-500">
          <div className="text-[10px] font-mono text-slate-400">FLOW IN</div>
          <div className="text-lg font-bold font-mono text-emerald-400">{telemetry?.flow_in_lpm.toFixed(0)}</div>
          <div className="text-[10px] font-mono text-slate-400">LPM</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-emerald-500">
          <div className="text-[10px] font-mono text-slate-400">FLOW OUT</div>
          <div className="text-lg font-bold font-mono text-emerald-300">{telemetry?.flow_out_lpm.toFixed(0)}</div>
          <div className="text-[10px] font-mono text-slate-400">LPM</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-purple-500">
          <div className="text-[10px] font-mono text-slate-400">STANDPIPE PRESS.</div>
          <div className="text-lg font-bold font-mono text-purple-300">{telemetry?.standpipe_pressure_bar.toFixed(1)}</div>
          <div className="text-[10px] font-mono text-slate-400">bar</div>
        </div>

        <div className="scada-panel p-2.5 border-t-2 border-t-purple-500">
          <div className="text-[10px] font-mono text-slate-400">PIT VOLUME</div>
          <div className="text-lg font-bold font-mono text-purple-400">{telemetry?.pit_volume_m3.toFixed(2)}</div>
          <div className="text-[10px] font-mono text-slate-400">m³</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">BHP DYNAMIC</div>
          <div className="text-base font-bold font-mono text-slate-200">{telemetry?.bottomhole_pressure_bar.toFixed(1)}</div>
          <div className="text-[10px] font-mono text-slate-400">bar</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">ECD</div>
          <div className="text-base font-bold font-mono text-slate-200">{telemetry?.ecd_gcc.toFixed(2)}</div>
          <div className="text-[10px] font-mono text-slate-400">g/cc</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">DELTA FLOW ΔQ</div>
          <div className={`text-base font-bold font-mono ${
            (telemetry?.delta_flow || 0) < -30 ? 'text-rose-400 font-extrabold' :
            (telemetry?.delta_flow || 0) > 30 ? 'text-cyan-400 font-extrabold' :
            'text-slate-300'
          }`}>
            {telemetry?.delta_flow.toFixed(1)}
          </div>
          <div className="text-[10px] font-mono text-slate-400">LPM</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">MSE (TEALE)</div>
          <div className="text-base font-bold font-mono text-slate-200">{telemetry?.mse_mpa.toFixed(0)}</div>
          <div className="text-[10px] font-mono text-slate-400">MPa</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">STICK-SLIP SSI</div>
          <div className={`text-base font-bold font-mono ${
            (telemetry?.stick_slip_index || 0) > 0.40 ? 'text-rose-400' : 'text-emerald-400'
          }`}>
            {telemetry?.stick_slip_index.toFixed(2)}
          </div>
          <div className="text-[10px] font-mono text-slate-400">Index</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">OVERPULL</div>
          <div className="text-base font-bold font-mono text-slate-200">{telemetry?.overpull_kn.toFixed(1)}</div>
          <div className="text-[10px] font-mono text-slate-400">kN</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">PORE PRESS. MARGIN</div>
          <div className="text-base font-bold font-mono text-slate-200">
            {((telemetry?.bottomhole_pressure_bar || 0) - (telemetry?.pore_pressure_bar || 0)).toFixed(1)}
          </div>
          <div className="text-[10px] font-mono text-slate-400">bar</div>
        </div>

        <div className="scada-panel p-2.5">
          <div className="text-[10px] font-mono text-slate-400">FRAC MARGIN</div>
          <div className="text-base font-bold font-mono text-slate-200">
            {((telemetry?.fracture_pressure_bar || 0) - (telemetry?.bottomhole_pressure_bar || 0)).toFixed(1)}
          </div>
          <div className="text-[10px] font-mono text-slate-400">bar</div>
        </div>
      </div>

      {/* 3. Live Recharts Time-Series Grids */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Chart 1: Flow In vs Flow Out & Pit Volume Trend */}
        <div className="scada-panel p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
              HYDRAULIC FLOW BALANCE & ACTIVE PIT VOLUME
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              ΔQ = {telemetry?.delta_flow.toFixed(1)} LPM
            </div>
          </div>
          <div className="mt-2">
            <StripChart data={chartData} series={FLOW_SERIES} leftPad={25} rightPad={0.3} rightDigits={2} />
          </div>
        </div>

        {/* Chart 2: Pressure Regimes (SPP, BHP, Pore, Fracture) */}
        <div className="scada-panel p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              PRESSURE OPERATING WINDOW (EATON PP / HUBBERT-WILLIS FG)
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              BHP: {telemetry?.bottomhole_pressure_bar.toFixed(1)} bar
            </div>
          </div>
          <div className="mt-2">
            <StripChart data={chartData} series={PRESSURE_SERIES} leftPad={10} />
          </div>
        </div>

        {/* Chart 3: Torsional Limit Cycles (Torque vs RPM Stick-Slip) */}
        <div className="scada-panel p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-rose-400"></span>
              2-DOF STRIBECK TORSIONAL OSCILLATIONS (STICK-SLIP DYNAMICS)
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              SSI: {telemetry?.stick_slip_index.toFixed(2)}
            </div>
          </div>
          <div className="mt-2">
            <StripChart data={chartData} series={TORSION_SERIES} leftPad={0.5} leftDigits={1} rightPad={3} />
          </div>
        </div>

        {/* Chart 4: ROP & WOB Penetration Dynamics */}
        <div className="scada-panel p-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              PENETRATION MECHANICS (BOURGOYNE-YOUNG ROP & WOB)
            </div>
            <div className="text-[11px] font-mono text-slate-400">
              ROP: {telemetry?.rop_m_hr.toFixed(1)} m/hr
            </div>
          </div>
          <div className="mt-2">
            <StripChart data={chartData} series={ROP_SERIES} leftPad={0.5} leftDigits={1} rightPad={3} />
          </div>
        </div>
      </div>
    </div>
  );
};
