import React from 'react';
import { Layers3 } from 'lucide-react';
import { HazardRiskAssessment } from '../../types';

// The 4-Pillar Decoupled Confidence Matrix -- this engagement's own
// explicit differentiator (logger/06's Innovation #4): separates Evidence
// Strength, Sensor Anomaly, Data Quality, and Audit Status instead of one
// opaque percentage. analyzeWell() already computes all 4 pillars per
// hazard; nothing in the UI broke them out individually before now --
// LookAheadPanel only showed the single composite m_ml value.

const STRENGTH_STYLE: Record<string, string> = {
  HIGH: 'text-emerald-400',
  MODERATE: 'text-amber-300',
  LOW: 'text-amber-400',
  INSUFFICIENT: 'text-rose-400',
};

export const ConfidencePillars: React.FC<{ hazard: HazardRiskAssessment | null }> = ({ hazard }) => {
  if (!hazard) {
    return (
      <div className="text-[10px] font-mono text-slate-600 p-2">No hazard assessment to decompose yet.</div>
    );
  }

  const c = hazard.confidence;
  const strengthColor = STRENGTH_STYLE[c.evidence_strength] || 'text-slate-400';

  return (
    <div className="border border-slate-800 rounded p-2.5 space-y-2 bg-slate-900/30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-slate-300 uppercase">
          <Layers3 className="w-3.5 h-3.5 text-cyan-400" /> 4-Pillar Confidence
        </div>
        <span className="text-[10px] font-mono text-slate-400">{hazard.hazard_type.replace(/_/g, ' ')}</span>
      </div>

      <div className="grid grid-cols-2 gap-1.5 text-[9px] font-mono">
        <div className="border border-slate-800 rounded px-2 py-1.5">
          <div className="text-slate-500 uppercase">Evidence Strength</div>
          <div className={`font-bold ${strengthColor}`}>
            {c.evidence_strength} <span className="text-slate-600 font-normal">(N={c.evidence_count})</span>
          </div>
          {c.evidence_strength === 'INSUFFICIENT' && (
            <div className="text-rose-400/80 mt-0.5 leading-snug">Insufficient historical analogs — treat as wildcat, prioritize live sensor monitoring.</div>
          )}
        </div>
        <div className="border border-slate-800 rounded px-2 py-1.5">
          <div className="text-slate-500 uppercase">Sensor Anomaly</div>
          <div className="font-bold text-slate-200">{(c.sensor_anomaly_score * 100).toFixed(0)}%</div>
        </div>
        <div className="border border-slate-800 rounded px-2 py-1.5">
          <div className="text-slate-500 uppercase">Data Quality</div>
          <div className="font-bold text-slate-200">{(c.data_quality_index * 100).toFixed(0)}%</div>
        </div>
        <div className="border border-slate-800 rounded px-2 py-1.5">
          <div className="text-slate-500 uppercase">Audit Status</div>
          <div className="font-bold text-slate-200 truncate" title={c.audit_status}>{c.audit_status}</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-[9px] font-mono pt-1 border-t border-slate-800/60">
        <span className="text-slate-500">Overall Confidence</span>
        <span className="text-slate-200 font-bold">{(c.overall_confidence * 100).toFixed(0)}%</span>
      </div>
      <div className="flex items-center justify-between text-[9px] font-mono text-slate-600">
        <span>P_hist {(hazard.p_history * 100).toFixed(0)}%</span>
        <span>A_sensor {(hazard.a_sensor * 100).toFixed(0)}%</span>
        <span>M_ML {(hazard.m_ml * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
};
