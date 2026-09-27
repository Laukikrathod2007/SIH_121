import React from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  Zap,
  Activity,
  Layers,
  ChevronDown,
  Circle,
  AlertTriangle,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';

export const Header: React.FC = () => {
  const {
    activeWellId,
    setActiveWellId,
    wells,
    activeWell,
    telemetry,
    activeRisk,
    simStatus,
    isBackendOnline,
    isWsConnected,
    startSim,
    pauseSim,
    resetSim,
    injectScenario,
  } = useApp();

  const handleScenarioChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === 'NORMAL') {
      // Clear scenarios
      injectScenario('NORMAL', 1.0);
    } else if (val) {
      injectScenario(val, 1.0);
    }
  };

  const riskLevel = activeRisk?.overall_risk_level || 'LOW';

  const riskColorClass = 
    riskLevel === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
    riskLevel === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
    riskLevel === 'MEDIUM' ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40' :
    'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';

  return (
    <header className="h-14 bg-[#0e121a] border-b border-slate-800/80 px-4 flex items-center justify-between z-10 shrink-0">
      {/* Left: Active Well Selector & Geological Coordinates */}
      <div className="flex items-center space-x-4">
        {/* Well Dropdown */}
        <div className="relative">
          <select
            value={activeWellId}
            onChange={(e) => setActiveWellId(e.target.value)}
            className="appearance-none bg-slate-900 border border-slate-700 hover:border-cyan-500/50 text-slate-100 font-mono text-xs font-semibold py-1.5 pl-3 pr-8 rounded focus:outline-none focus:ring-1 focus:ring-cyan-500 cursor-pointer"
          >
            {wells.length > 0 ? (
              wells.map((w) => (
                <option key={w.well_id} value={w.well_id}>
                  {w.well_name} ({w.field_code}) - {w.well_type}
                </option>
              ))
            ) : (
              <option value="WELL-NHK-001">NHK-001 (Nahorkatiya) - Active</option>
            )}
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
        </div>

        {/* Real-time Depth Readout */}
        <div className="hidden md:flex items-center space-x-3 text-xs font-mono">
          <div className="bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded flex items-center gap-1.5">
            <span className="text-slate-400">MD:</span>
            <span className="text-cyan-400 font-bold">
              {telemetry?.measured_depth_m?.toFixed(1) ?? '2450.0'} m
            </span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded flex items-center gap-1.5">
            <span className="text-slate-400">TVDSS:</span>
            <span className="text-slate-200">
              {telemetry?.tvdss_m?.toFixed(1) ?? '2315.6'} m
            </span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded flex items-center gap-1.5">
            <Layers className="w-3 h-3 text-amber-400" />
            <span className="text-slate-400">FORMATION:</span>
            <span className="text-amber-300 font-semibold truncate max-w-[140px]">
              {telemetry?.formation?.replace(/_/g, ' ') ?? 'Barail Sand'}
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-1 rounded">
              ξ: {telemetry?.xi?.toFixed(3) ?? '0.250'}
            </span>
          </div>
        </div>
      </div>

      {/* Right: Simulator Quick Actions & Connection Status */}
      <div className="flex items-center space-x-3">
        {/* Overall Fused Risk Indicator */}
        <div className={`px-2.5 py-1 rounded border text-xs font-mono flex items-center gap-1.5 ${riskColorClass}`}>
          <AlertTriangle className="w-3.5 h-3.5" />
          <span className="font-bold">RISK: {riskLevel}</span>
        </div>

        {/* Scenario Injection Selector */}
        <div className="relative">
          <select
            onChange={handleScenarioChange}
            defaultValue=""
            className="appearance-none bg-slate-900 border border-amber-500/40 text-amber-300 text-xs font-mono font-medium py-1.5 pl-2.5 pr-7 rounded focus:outline-none focus:ring-1 focus:ring-amber-500 cursor-pointer"
          >
            <option value="" disabled>⚡ Inject Scenario...</option>
            <option value="NORMAL">NORMAL DRILLING</option>
            <option value="LOST_CIRCULATION">⚠️ LOST CIRCULATION</option>
            <option value="KICK_OVERPRESSURE">🚨 KICK / OVERPRESSURE</option>
            <option value="STUCK_PIPE">🛑 STUCK PIPE</option>
            <option value="STICK_SLIP">🌀 STICK-SLIP VIBRATION</option>
            <option value="WASHOUT">💧 BIT WASHOUT</option>
            <option value="SENSOR_FAULT">📡 SENSOR FAULT</option>
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-amber-400 absolute right-2 top-2.5 pointer-events-none" />
        </div>

        {/* Simulator Controls */}
        <div className="flex items-center bg-slate-900 border border-slate-700 rounded p-0.5">
          {simStatus?.is_running ? (
            <button
              onClick={pauseSim}
              title="Pause Simulation"
              className="p-1 hover:bg-slate-800 text-amber-400 rounded transition"
            >
              <Pause className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={startSim}
              title="Start Simulation"
              className="p-1 hover:bg-slate-800 text-emerald-400 rounded transition"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
            </button>
          )}
          <button
            onClick={() => resetSim()}
            title="Reset Simulator"
            className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Status Pills */}
        <div className="hidden lg:flex items-center space-x-2 pl-2 border-l border-slate-800 text-[10px] font-mono">
          <div className="flex items-center gap-1 text-slate-400" title="FastAPI Core">
            <Circle className={`w-2 h-2 fill-current ${isBackendOnline ? 'text-emerald-400' : 'text-rose-500'}`} />
            API
          </div>
          <div className="flex items-center gap-1 text-slate-400" title="WebSocket Telemetry">
            <Circle className={`w-2 h-2 fill-current ${isWsConnected ? 'text-emerald-400' : 'text-slate-600'}`} />
            WS
          </div>
          <div className="flex items-center gap-1 text-slate-400" title="ML Risk Fusion">
            <Circle className="w-2 h-2 fill-current text-cyan-400" />
            ML
          </div>
        </div>
      </div>
    </header>
  );
};
