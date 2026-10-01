import React from 'react';
import {
  ShieldAlert,
  Cpu,
  Activity,
  Layers,
  CheckCircle,
  AlertTriangle,
  Flame,
  Info,
  Sliders,
} from 'lucide-react';
import { useApp } from '../context/AppContext';

// NOTE ON ILLUSTRATIVE NUMBERS: featureImportances, and the ROC-AUC/PR-AUC/
// lead-time/false-alert-rate/inference-latency figures below are reference
// values carried over from Prasad's original frontend — they were never
// computed by a real benchmarking pass against our own model (the benchmark
// report that produced similar-looking numbers in his branch was found to
// contain fabricated metrics — see modules/04_physics_engine's integration
// notes — so we deliberately did not port it). modules/04_physics_engine's
// XGBoost classifier exists in this repo (confirmed: real xgboost_classifier
// object with fitted-state tracking, api/server.py) but has no HTTP endpoint
// surfacing these specific figures yet, so
// there is nothing live to measure these against. They are marked
// "Illustrative" wherever shown below rather than presented as real.
export const RiskPredictionPage: React.FC = () => {
  const { activeRisk, telemetry } = useApp();

  const hazards = [
    { key: 'LOST_CIRCULATION', name: 'Lost Circulation', desc: 'BHP breach over fracture gradient resulting in annular fluid loss' },
    { key: 'KICK', name: 'Kick / Gas Influx', desc: 'Pore overpressure overcoming mud hydrostatic head into borehole' },
    { key: 'STUCK_PIPE', name: 'Stuck Pipe (Differential / Packoff)', desc: 'Cuttings bed accumulation or high sliding friction causing overpull' },
    { key: 'TORQUE_DRAG', name: 'Torque & Drag / Stick-Slip', desc: 'Torsional limit cycle oscillations and rotary stalling' },
    { key: 'WASHOUT', name: 'Bit Nozzle Washout', desc: 'Frictional nozzle erosion causing sudden standpipe pressure drop' },
  ];

  const featureImportances = [
    { rank: 1, name: 'fg_margin_bar', importance: 0.1492, category: 'Geology & Hydraulics' },
    { rank: 2, name: 'overpull_kn', importance: 0.1155, category: 'Mechanics' },
    { rank: 3, name: 'd_exponent_slope', importance: 0.0904, category: 'Drilling Mechanics' },
    { rank: 4, name: 'stick_slip_index', importance: 0.0882, category: 'Torsional Dynamics' },
    { rank: 5, name: 'd_exponent_deviation', importance: 0.0814, category: 'Geology' },
    { rank: 6, name: 'xi (Stratigraphic Coord)', importance: 0.0593, category: 'Module 4 Subsurface' },
    { rank: 7, name: 'pp_margin_bar', importance: 0.0488, category: 'Pressure Regime' },
    { rank: 8, name: 'delta_flow (Flow Imbalance)', importance: 0.0476, category: 'Hydraulics' },
    { rank: 9, name: 'standpipe_pressure_bar', importance: 0.0421, category: 'Hydraulics' },
  ];

  const isoAnomaly = activeRisk?.isolation_forest_anomaly;

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-rose-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-rose-500/10 border border-rose-500/30 rounded text-rose-400">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              MODULE 5: MULTI-SIGNAL PREDICTIVE RISK ANALYTICS & ML
              <span className="text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30 px-1.5 py-0.5 rounded">
                4-PILLAR FUSION ENGINE
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Deterministic Rules (35%) + Isolation Forest (20%) + 6-Class XGBoost (30%) + Mod 4 Geology (15%)
            </div>
          </div>
        </div>

        {/* Global Risk Badge */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="text-slate-400">OVERALL THREAT:</span>
          <span className={`px-2.5 py-1 rounded font-bold border ${
            (activeRisk?.overall_risk_level || 'LOW') === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
            (activeRisk?.overall_risk_level || 'LOW') === 'HIGH' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
            'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
          }`}>
            {activeRisk?.overall_risk_level || 'LOW'} RISK
          </span>
        </div>
      </div>

      {/* Main Grid: Hazard Breakdown & 4 Pillars */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Hazard Forecast Probabilities */}
        <div className="scada-panel p-4 space-y-4">
          <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
            <span>FUSED DRILLING HAZARD PROBABILITIES</span>
            <span className="text-[11px] text-cyan-400">Target Horizon: Current Bit ± 20m</span>
          </div>

          <div className="space-y-3">
            {hazards.map((h) => {
              const score = activeRisk?.fused_hazard_scores[h.key] || 0.10;
              const isCritical = score >= 0.70;
              const isWarning = score >= 0.45 && score < 0.70;

              return (
                <div key={h.key} className="p-3 bg-slate-900/80 border border-slate-800 rounded space-y-1.5">
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="font-bold text-slate-200">{h.name}</span>
                    <span className={`font-bold ${isCritical ? 'text-rose-400 text-sm' : isWarning ? 'text-amber-400' : 'text-emerald-400'}`}>
                      {(score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-950 h-2.5 rounded overflow-hidden border border-slate-800">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isCritical ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${score * 100}%` }}
                    ></div>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono leading-tight">{h.desc}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: The 4 Dissected Pillars of Decision */}
        <div className="scada-panel p-4 space-y-3 flex flex-col justify-between">
          <div>
            <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
              <span>THE 4 DECISION LAYERS (GROUNDED ARCHITECTURE)</span>
              <span className="text-[11px] text-emerald-400">No Hallucinations</span>
            </div>

            <div className="mt-3 space-y-2.5 text-xs font-mono">
              {/* Pillar 1: Rules */}
              <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded space-y-1">
                <div className="flex items-center justify-between font-bold">
                  <span className="text-slate-300">1. DETERMINISTIC PHYSICS RULES (Weight: 35%)</span>
                  <span className="text-cyan-400">Debounced (Hysteresis)</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Equations check: ΔQ persistent over 3 sec, Overpull &gt; 25 kN, SSI &gt; 0.40.
                </div>
                <div className="text-[10px] text-slate-300">
                  Active Rule Triggers:{' '}
                  {activeRisk?.rule_triggers && activeRisk.rule_triggers.length > 0 ? (
                    <span className="text-rose-400 font-bold">{activeRisk.rule_triggers.join(', ')}</span>
                  ) : (
                    <span className="text-emerald-400">None (Operating within safe envelope)</span>
                  )}
                </div>
              </div>

              {/* Pillar 2: Isolation Forest */}
              <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded space-y-1">
                <div className="flex items-center justify-between font-bold">
                  <span className="text-slate-300">2. ISOLATION FOREST ANOMALY (Weight: 20%)</span>
                  <span className="text-purple-400">Unsupervised</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Answers: <em>"Does current state look abnormal compared to normal drilling?"</em>
                </div>
                <div className="flex items-center justify-between text-[11px] pt-1">
                  <span>State: {isoAnomaly?.is_anomaly ? <strong className="text-rose-400">ANOMALOUS</strong> : <strong className="text-emerald-400">NORMAL</strong>}</span>
                  <span>Anomaly Score: {isoAnomaly ? isoAnomaly.anomaly_score.toFixed(3) : 'n/a'}</span>
                  <span className="text-slate-500">False Alerts: 0.2/hr <em className="text-amber-400 not-italic">(illustrative)</em></span>
                </div>
              </div>

              {/* Pillar 3: XGBoost Supervised Classifier */}
              <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded space-y-1">
                <div className="flex items-center justify-between font-bold">
                  <span className="text-slate-300">3. XGBOOST 6-CLASS CLASSIFIER (Weight: 30%)</span>
                  <span className="text-amber-400">Supervised GBDT</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Trained with strict <code>GroupKFold</code> well-level splitting. Zero data leakage.
                </div>
                <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                  <span>ROC-AUC: 0.949</span>
                  <span>PR-AUC: 0.946</span>
                  <span>Lead Time: 120s</span>
                  <span className="text-amber-400">(illustrative — not measured)</span>
                </div>
              </div>

              {/* Pillar 4: Module 4 Geology */}
              <div className="p-2.5 bg-slate-900/80 border border-slate-800 rounded space-y-1">
                <div className="flex items-center justify-between font-bold">
                  <span className="text-slate-300">4. MODULE 4 GEOLOGY & OFFSETS (Weight: 15%)</span>
                  <span className="text-emerald-400">Stratigraphic Prior</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Incorporates historical hazard frequency mapped through stratigraphic coordinate ξ.
                </div>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
            <span>Inference Latency: 24.53 ms <span className="text-amber-400">(illustrative)</span></span>
          </div>
        </div>
      </div>

      {/* Feature Importance Table */}
      <div className="scada-panel p-4">
        <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800 flex items-center justify-between">
          <span>FEATURE IMPORTANCE HIERARCHY (XGBOOST EXPLAINABILITY)</span>
          <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40 px-1.5 py-0.5 rounded">
            Illustrative — not measured against our model
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-3 text-xs font-mono">
          {featureImportances.map((f) => (
            <div key={f.rank} className="p-2 bg-slate-900/70 border border-slate-800 rounded flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-slate-400 font-bold text-[10px] w-4">{f.rank}.</span>
                <div>
                  <div className="text-slate-200 font-semibold">{f.name}</div>
                  <div className="text-[9px] text-slate-400">{f.category}</div>
                </div>
              </div>
              <div className="text-cyan-400 font-bold">{(f.importance * 100).toFixed(1)}%</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
