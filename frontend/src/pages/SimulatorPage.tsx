import React, { useState } from 'react';
import {
  Cpu,
  Play,
  Pause,
  RotateCcw,
  StepForward,
  FastForward,
  AlertTriangle,
  Zap,
  Activity,
  CheckCircle,
  Sliders,
  Flame,
  Radio,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

export const SimulatorPage: React.FC = () => {
  const {
    telemetry,
    simStatus,
    startSim,
    pauseSim,
    stepSim,
    resetSim,
    setSimSpeed,
    injectScenario,
    clearScenarios,
  } = useApp();

  const [severity, setSeverity] = useState<number>(1.0);
  const [resetDepth, setResetDepth] = useState<number>(2450.0);

  const scenarioCards = [
    {
      type: 'LOST_CIRCULATION',
      title: 'Lost Circulation (Fracture Breakdown)',
      desc: 'BHP breaches formation fracture gradient in permeable sandstone, producing Darcy loss (150+ LPM), return flow deficit, and pit depletion.',
      color: 'border-amber-500/40 hover:border-amber-500 text-amber-400',
      btnColor: 'bg-amber-600 hover:bg-amber-500',
    },
    {
      type: 'KICK_OVERPRESSURE',
      title: 'Kick / Gas Influx (Pore Overpressure)',
      desc: 'Pore pressure exceeds bottomhole hydrostatic head in permeable reservoir sand, inducing Darcy fluid influx, flow-out acceleration, and pit gain.',
      color: 'border-rose-500/40 hover:border-rose-500 text-rose-400',
      btnColor: 'bg-rose-600 hover:bg-rose-500',
    },
    {
      type: 'STUCK_PIPE',
      title: 'Stuck Pipe (Cuttings Bed & Packoff)',
      desc: 'Inadequate hole cleaning causes annular cuttings bed accumulation, spiking sliding drag and overpull > 25 kN, stalling bit penetration.',
      color: 'border-purple-500/40 hover:border-purple-500 text-purple-400',
      btnColor: 'bg-purple-600 hover:bg-purple-500',
    },
    {
      type: 'STICK_SLIP',
      title: 'Stick-Slip Vibration (Stribeck ODE)',
      desc: 'Velocity-weakening bit reaction friction induces autonomous 2-DOF torsional limit-cycle oscillations (SSI > 0.80), swinging bit RPM between 0 and 260.',
      color: 'border-rose-500/40 hover:border-rose-500 text-rose-400',
      btnColor: 'bg-rose-600 hover:bg-rose-500',
    },
    {
      type: 'WASHOUT',
      title: 'Bit Nozzle Washout',
      desc: 'Severe hydraulic erosion of bit jets causes a sudden 15 bar Standpipe Pressure (SPP) drop with constant surface pump rate.',
      color: 'border-cyan-500/40 hover:border-cyan-500 text-cyan-400',
      btnColor: 'bg-cyan-600 hover:bg-cyan-500',
    },
    {
      type: 'SENSOR_FAULT',
      title: 'Sensor Fault (Resilience Test)',
      desc: 'Injects flow sensor dropout and pressure bias; verifies the system degrades sensor quality without generating false wellbore hazard alerts.',
      color: 'border-slate-500/40 hover:border-slate-500 text-slate-300',
      btnColor: 'bg-slate-700 hover:bg-slate-600',
    },
  ];

  const activeScenarios = simStatus?.active_scenarios || {};
  const activeKeys = Object.keys(activeScenarios);

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              MODULE 5: REDUCED-ORDER DRILLING PHYSICS DIGITAL TWIN CONTROLLER
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                CAUSAL CONSERVATION SOLVER
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Mass & Momentum Balance | 4th-Order Runge-Kutta ODE | Darcy Reservoir Flow
            </div>
          </div>
        </div>

        {/* Live Status Pill */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="text-slate-400">STATE:</span>
          <span className={`px-2.5 py-1 rounded font-bold border ${
            simStatus?.is_running
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              : 'bg-slate-800 text-slate-400 border-slate-700'
          }`}>
            {simStatus?.is_running ? 'SIMULATION RUNNING' : 'PAUSED'}
          </span>
        </div>
      </div>

      {/* Simulator Master Control Console */}
      <div className="scada-panel p-4 space-y-3">
        <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
          <span>OPERATIONAL CONTROL CONSOLE</span>
          <span className="text-[11px] text-cyan-400 font-mono">Sim Time: {simStatus?.sim_time_s.toFixed(1)}s</span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* Main Action Buttons */}
          <div className="flex items-center space-x-2">
            {simStatus?.is_running ? (
              <button
                onClick={pauseSim}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold font-mono text-xs rounded transition flex items-center gap-1.5 shadow-md shadow-amber-600/30"
              >
                <Pause className="w-4 h-4" /> PAUSE SIMULATION
              </button>
            ) : (
              <button
                onClick={startSim}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold font-mono text-xs rounded transition flex items-center gap-1.5 shadow-md shadow-emerald-600/30"
              >
                <Play className="w-4 h-4 fill-current" /> START SIMULATION
              </button>
            )}

            <button
              onClick={stepSim}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-mono text-xs rounded border border-slate-700 transition flex items-center gap-1.5"
            >
              <StepForward className="w-4 h-4" /> STEP (1s ODE)
            </button>

            <button
              onClick={() => resetSim(resetDepth)}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-mono text-xs rounded border border-slate-700 transition flex items-center gap-1.5"
            >
              <RotateCcw className="w-4 h-4" /> RESET
            </button>
          </div>

          {/* Speed & Severity Controls */}
          <div className="flex items-center space-x-4 text-xs font-mono">
            {/* Speed Multiplier */}
            <div className="flex items-center space-x-1 bg-slate-900 border border-slate-800 p-1 rounded">
              <span className="text-slate-400 text-[10px] px-1.5">SPEED:</span>
              {[0.5, 1, 2, 5, 10].map((s) => (
                <button
                  key={s}
                  onClick={() => setSimSpeed(s)}
                  className={`px-2 py-0.5 rounded text-[11px] ${
                    simStatus?.speed_multiplier === s
                      ? 'bg-cyan-500 text-slate-950 font-bold'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {s}x
                </button>
              ))}
            </div>

            {/* Severity Slider */}
            <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-2 py-1 rounded">
              <span className="text-slate-400 text-[10px]">SEVERITY:</span>
              <input
                type="range"
                min="0.5"
                max="2.5"
                step="0.1"
                value={severity}
                onChange={(e) => setSeverity(parseFloat(e.target.value))}
                className="w-20 accent-cyan-400 cursor-pointer"
              />
              <span className="text-cyan-400 font-bold">{severity.toFixed(1)}x</span>
            </div>
          </div>
        </div>

        {/* Active Injected Faults Status Bar */}
        <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400">ACTIVE SCENARIOS:</span>
            {activeKeys.length > 0 ? (
              activeKeys.map((k) => (
                <span key={k} className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">
                  {k} (Severity: {activeScenarios[k].severity || severity}x)
                </span>
              ))
            ) : (
              <span className="text-emerald-400 font-bold">NORMAL OPERATIONAL DRILLING</span>
            )}
          </div>

          {activeKeys.length > 0 && (
            <button
              onClick={clearScenarios}
              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-amber-400 rounded text-xs font-bold transition border border-slate-700"
            >
              CLEAR ALL FAULTS (RESTORE NORMAL)
            </button>
          )}
        </div>
      </div>

      {/* Scenario Injection Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {scenarioCards.map((sc) => (
          <div
            key={sc.type}
            className={`scada-panel p-4 border rounded-lg flex flex-col justify-between space-y-3 transition hover:bg-slate-900/60 ${sc.color}`}
          >
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold font-mono text-xs">{sc.title}</span>
                <Zap className="w-4 h-4 shrink-0" />
              </div>
              <div className="text-[11px] text-slate-300 font-sans leading-relaxed">{sc.desc}</div>
            </div>

            <button
              onClick={() => injectScenario(sc.type, severity)}
              className={`w-full py-2 font-mono text-xs font-bold rounded text-slate-950 transition shadow-md ${sc.btnColor}`}
            >
              INJECT {sc.type.replace('_', ' ')}
            </button>
          </div>
        ))}
      </div>

      {/* Internal Physics State Inspector */}
      <div className="scada-panel p-4 space-y-3">
        <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
          <span>INTERNAL COUPLED ODE STATE VARIABLES (NOT DEGRADED)</span>
          <span className="text-[10px] text-cyan-400">Ground Truth Solver</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2 text-xs font-mono">
          <div className="p-2 bg-slate-900/80 border border-slate-800 rounded">
            <div className="text-slate-400 text-[10px]">CURRENT BIT MD</div>
            <div className="text-sm font-bold text-slate-100">{telemetry?.measured_depth_m.toFixed(2)} m</div>
          </div>
          <div className="p-2 bg-slate-900/80 border border-slate-800 rounded">
            <div className="text-slate-400 text-[10px]">HYDROSTATIC HEAD</div>
            <div className="text-sm font-bold text-slate-100">
              {((telemetry?.ecd_gcc || 1.29) * 9.81 * (telemetry?.tvd_m || 2435) / 100).toFixed(1)} bar
            </div>
          </div>
          <div className="p-2 bg-slate-900/80 border border-slate-800 rounded">
            <div className="text-slate-400 text-[10px]">ANNULAR PRESS LOSS</div>
            <div className="text-sm font-bold text-slate-100">
              {((telemetry?.bottomhole_pressure_bar || 242) - (telemetry?.tvd_m || 2435) * 0.0981 * 1.22).toFixed(1)} bar
            </div>
          </div>
          <div className="p-2 bg-slate-900/80 border border-slate-800 rounded">
            <div className="text-slate-400 text-[10px]">CUTTINGS CONCENTRATION</div>
            <div className="text-sm font-bold text-slate-100">{((telemetry?.cuttings_concentration || 0.02) * 100).toFixed(2)}%</div>
          </div>
          <div className="p-2 bg-slate-900/80 border border-slate-800 rounded">
            <div className="text-slate-400 text-[10px]">TEALE MSE RATIO</div>
            <div className="text-sm font-bold text-slate-100">{((telemetry?.mse_mpa || 118) / 45).toFixed(2)}x UCS</div>
          </div>
          <div className="p-2 bg-slate-900/80 border border-slate-800 rounded">
            <div className="text-slate-400 text-[10px]">SENSOR NOISE FILTER</div>
            <div className="text-sm font-bold text-emerald-400">1st-Order Lag (α=0.7)</div>
          </div>
        </div>
      </div>
    </div>
  );
};
