import React, { useState } from 'react';
import {
  Brain,
  ShieldCheck,
  CheckCircle,
  Database,
  Radio,
  FileText,
  Layers,
  Cpu,
  BarChart3,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface HazardModelInfo {
  hazard: string;
  code: string;
  algorithm: string;
  auc: number;
  positives: number;
  totalSamples: number;
  features: string[];
  status: 'ACTIVE' | 'RETRAINED';
  provenance: string;
}

const HAZARD_MODELS: HazardModelInfo[] = [
  {
    hazard: 'Mud Loss / Lost Circulation',
    code: 'MUD_LOSS',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.808,
    positives: 13,
    totalSamples: 89,
    features: ['depth_diff_m', 'strat_diff_m', 'xi_diff', 'dors_score', 'target_hazard_weight', 'distance_km'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
  {
    hazard: 'Kick / Gas Influx',
    code: 'KICK',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.817,
    positives: 10,
    totalSamples: 89,
    features: ['depth_diff_m', 'strat_diff_m', 'pore_pressure_margin', 'delta_flow', 'dors_score', 'target_hazard_weight'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
  {
    hazard: 'Overpressure Zone',
    code: 'OVERPRESSURE_ZONE',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.796,
    positives: 12,
    totalSamples: 89,
    features: ['depth_diff_m', 'strat_diff_m', 'dc_exponent_deviation', 'mud_weight_ppg', 'dors_score'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
  {
    hazard: 'Torque Spike / Mechanical Drag',
    code: 'TORQUE_SPIKE',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.700,
    positives: 13,
    totalSamples: 89,
    features: ['depth_diff_m', 'strat_diff_m', 'stick_slip_index', 'rpm', 'dors_score', 'target_hazard_weight'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
  {
    hazard: 'Cementing Failure / Channeling',
    code: 'CEMENTING_FAILURE',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.650,
    positives: 12,
    totalSamples: 89,
    features: ['shoe_depth_md_m', 'toc_gap_m', 'slurry_class_code', 'historical_loss_count', 'dors_score'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
  {
    hazard: 'Stuck Pipe / Differential Sticking',
    code: 'STUCK_PIPE',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.582,
    positives: 13,
    totalSamples: 89,
    features: ['depth_diff_m', 'strat_diff_m', 'dogleg_severity', 'overpull_kn', 'dors_score'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
  {
    hazard: 'Wellbore Instability / Breakout',
    code: 'WELLBORE_INSTABILITY',
    algorithm: 'Logistic Regression + StandardScaler',
    auc: 0.519,
    positives: 8,
    totalSamples: 89,
    features: ['depth_diff_m', 'strat_diff_m', 'formation_ucs', 'breakout_angle', 'dors_score'],
    status: 'ACTIVE',
    provenance: 'OIL Assam-Arakan Benchmark (12 wells)',
  },
];

export const ModelCardsRegistry: React.FC = () => {
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  const toggleCard = (code: string) => {
    setExpandedCard(prev => prev === code ? null : code);
  };

  return (
    <div className="space-y-6">
      {/* Transparency & Lineage Header Banner */}
      <div className="p-4 bg-slate-900/90 border border-cyan-500/30 rounded-lg space-y-3 font-mono">
        <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2 text-cyan-300 font-bold text-sm">
            <Brain className="w-5 h-5 text-cyan-400" />
            AI / ML MODEL REGISTRY & DATA PROVENANCE MATRIX
          </div>
          <span className="text-[11px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded font-semibold">
            100% SERIALIZED &amp; ACTIVE
          </span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed font-sans">
          In strict compliance with <strong>SIH Problem Statement 26121 (Oil India Limited)</strong>, DrillWise operates
          a dual-tier AI architecture: <strong>Module 02 Well Intelligence</strong> (7 statistical hazard prediction models
          trained with scikit-learn 1.9.1 on geological offset correlations), and <strong>Module 05 Predictive Analytics</strong>
          (an IsolationForest sensor anomaly detector and a 6-class XGBoost multi-hazard classifier).
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs pt-1">
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded">
            <div className="text-amber-400 font-bold flex items-center gap-1.5 mb-1">
              <Database className="w-3.5 h-3.5" />
              OIL Assam-Arakan Benchmark Dataset
            </div>
            <div className="text-slate-400 text-[11px] space-y-0.5">
              <div>• <strong>12 Wells:</strong> Nahorkatiya (NHK), Moran (MOR), Jorajan (JNB), Kusijan (KPL), Dikom (DIK), Hugrijan (HGJ)</div>
              <div>• <strong>89 Enriched Drilling Events:</strong> Mud loss, kick, stuck pipe, overpressure, torque spikes, cementing failures</div>
              <div>• <strong>64 Casing &amp; Cementing Strings:</strong> 30", 20", 13-3/8", 9-5/8", 7" with TOC and cement slurry recipes</div>
              <div>• <strong>8 Fishing Operations:</strong> Historical IADC remediation records (overshot, spear, jar operations)</div>
            </div>
          </div>
          <div className="p-2.5 bg-slate-950/80 border border-slate-800 rounded">
            <div className="text-emerald-400 font-bold flex items-center gap-1.5 mb-1">
              <Radio className="w-3.5 h-3.5" />
              Equinor Volve Field (Real WITSML Feed)
            </div>
            <div className="text-slate-400 text-[11px] space-y-0.5">
              <div>• <strong>Real WITSML 1.4.1.1:</strong> 438 log stations (15/9-F-12) + 110 trajectory stations (15/9-F-1)</div>
              <div>• <strong>Sensor Channels:</strong> ROP, WOB, RPM, Torque, Flow In/Out, SPP, Mud Weight, ECD</div>
              <div>• <strong>Real Precursor Injections:</strong> Validated on real Volve kick and tight hole intervals</div>
              <div>• <strong>Dynamic Lead Time:</strong> Δt = ΔDepth / ROP (typically 15–45 minutes of actionable lead time)</div>
            </div>
          </div>
        </div>
      </div>

      {/* Module 02: 7 Geological Hazard Prediction Models */}
      <div className="space-y-3">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800">
          <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-amber-400" />
            MODULE 02 — 7 GEOLOGICAL HAZARD PREDICTION MODELS
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Path: modules/02_nwis_backend/data/models/*.joblib
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {HAZARD_MODELS.map((m) => {
            const isExpanded = expandedCard === m.code;
            const aucColor =
              m.auc >= 0.75 ? 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10' :
              m.auc >= 0.60 ? 'text-amber-300 border-amber-500/40 bg-amber-500/10' :
              'text-cyan-300 border-cyan-500/40 bg-cyan-500/10';

            return (
              <div
                key={m.code}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-lg p-3 space-y-2 transition font-mono"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="text-xs font-bold text-slate-100">{m.hazard}</div>
                    <div className="text-[10px] text-slate-500">{m.code}</div>
                  </div>
                  <div className={`px-2 py-0.5 rounded border text-xs font-bold ${aucColor}`}>
                    AUC {m.auc.toFixed(3)}
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 space-y-1 pt-1 border-t border-slate-800/80">
                  <div className="flex justify-between">
                    <span>Algorithm:</span>
                    <span className="text-slate-300 truncate max-w-[170px]" title={m.algorithm}>{m.algorithm}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Training Data:</span>
                    <span className="text-slate-300">{m.positives} pos / {m.totalSamples} total</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Validation:</span>
                    <span className="text-cyan-400">Leave-One-Well-Out CV</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="text-emerald-400 font-bold flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> ACTIVE
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => toggleCard(m.code)}
                  className="w-full text-left text-[10px] text-slate-400 hover:text-cyan-400 flex items-center justify-between pt-1 border-t border-slate-800"
                >
                  <span>Features ({m.features.length})</span>
                  {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                {isExpanded && (
                  <div className="p-2 bg-slate-950 rounded text-[10px] text-slate-300 space-y-0.5">
                    {m.features.map(f => (
                      <div key={f} className="text-cyan-300/80">• {f}</div>
                    ))}
                    <div className="text-[9px] text-slate-500 pt-1">
                      Provenance: {m.provenance}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Operational Remediation Card: Fishing Operations */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 space-y-2 font-mono">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs font-bold text-slate-300">Fishing Operation Archive</div>
                <div className="text-[10px] text-slate-500">FISHING_OPERATION</div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded border border-violet-500/40 bg-violet-500/10 text-violet-300">
                REMEDIATION
              </span>
            </div>
            <div className="text-[11px] text-slate-400 space-y-1 pt-1 border-t border-slate-800/80">
              <div>• <strong>8 Historical Records:</strong> Preserved in drilling event repository for retrospective lookups</div>
              <div>• <strong>Tools Logged:</strong> Overshots, spears, washpipe, bumper jars, hydraulic accelerators</div>
              <div>• <strong>Domain Rule:</strong> Excluded from hazard forward-prediction models (remediation, not geological risk)</div>
            </div>
          </div>
        </div>
      </div>

      {/* Module 05: Real-Time Telemetry & Fusion Models */}
      <div className="space-y-3">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800">
          <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            MODULE 05 — REAL-TIME TELEMETRY &amp; MULTI-CLASS ML FUSION
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Path: modules/05_predictive_analytics/predictive/data/models/*.joblib
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono">
          {/* IsolationForest */}
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-100 flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                TELEMETRY ANOMALY DETECTOR
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded">
                ACTIVE
              </span>
            </div>
            <div className="text-xs text-slate-300">
              <strong>Algorithm:</strong> IsolationForest (n_estimators=100, contamination=0.05)
            </div>
            <div className="text-[11px] text-slate-400 space-y-0.5">
              <div>• <strong>Fitted On:</strong> 3,600 continuous multi-channel drilling telemetry points</div>
              <div>• <strong>Sensors Monitored:</strong> ROP (m/h), WOB (kN), RPM, Torque (kN·m), SPP (bar), Delta Flow (lpm)</div>
              <div>• <strong>Artifact:</strong> <code className="text-cyan-300">anomaly_detector_isolation_forest.joblib</code></div>
            </div>
          </div>

          {/* XGBoost Multi-Class Classifier */}
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-lg space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-100 flex items-center gap-2">
                <Brain className="w-4 h-4 text-violet-400" />
                6-CLASS MULTI-HAZARD CLASSIFIER
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded">
                ACTIVE
              </span>
            </div>
            <div className="text-xs text-slate-300">
              <strong>Algorithm:</strong> XGBoost Multi-Class Classifier (n_estimators=60, max_depth=4)
            </div>
            <div className="text-[11px] text-slate-400 space-y-0.5">
              <div>• <strong>Target Classes:</strong> NORMAL, KICK, STUCK_PIPE, LOST_CIRCULATION, WELLBORE_INSTABILITY, BIT_WASHOUT</div>
              <div>• <strong>Fitted On:</strong> 360 multi-hazard synthetic &amp; Volve sensor signature samples</div>
              <div>• <strong>Artifact:</strong> <code className="text-violet-300">xgboost_hazard_classifier.joblib</code></div>
            </div>
          </div>
        </div>
      </div>

      {/* Volve Real-Data Models */}
      <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-lg space-y-2 font-mono">
        <div className="text-xs font-bold text-slate-200 flex items-center gap-2">
          <Database className="w-4 h-4 text-emerald-400" />
          REAL EQUINOR VOLVE DATASET MODELS (re-trained &amp; serialized with scikit-learn 1.9.1)
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[11px] text-slate-300">
          <div className="p-2 bg-slate-950 rounded border border-slate-800">
            <div className="font-bold text-emerald-400">stuck_pipe_model_REAL.joblib</div>
            <div className="text-slate-500 text-[10px]">Trained on Volve 15/9-F-12 real trajectory &amp; drag logs</div>
          </div>
          <div className="p-2 bg-slate-950 rounded border border-slate-800">
            <div className="font-bold text-emerald-400">wellbore_instability_model_REAL.joblib</div>
            <div className="text-slate-500 text-[10px]">Trained on Volve real caliper &amp; sonic breakout data</div>
          </div>
          <div className="p-2 bg-slate-950 rounded border border-slate-800">
            <div className="font-bold text-emerald-400">kick_model_REAL.joblib</div>
            <div className="text-slate-500 text-[10px]">Trained on Volve real pressure &amp; pit volume deviations</div>
          </div>
        </div>
      </div>
    </div>
  );
};
