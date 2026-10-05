import React from 'react';
import { AlertTriangle, Brain, Sliders, FileText } from 'lucide-react';
import { HazardRiskAssessment, NWISAnalysisResponse } from '../../types';

// "What does it mean" layer (the Tela-inspired panel from the visual
// synthesis) -- built directly from analyzeWell's hazard_assessments,
// which is real backend data (real trained model for STUCK_PIPE, honestly
// disclosed heuristic fallback for the rest via m_ml_source) that was
// called nowhere in the frontend before this component existed.

const RISK_STYLE: Record<string, string> = {
  CRITICAL: 'border-rose-500/40 bg-rose-500/5 text-rose-300',
  HIGH: 'border-amber-500/40 bg-amber-500/5 text-amber-300',
  MODERATE: 'border-amber-500/25 bg-amber-500/5 text-amber-200',
  LOW: 'border-slate-800 bg-slate-900/40 text-emerald-300',
};

function HazardCard({ h }: { h: HazardRiskAssessment }) {
  const style = RISK_STYLE[h.risk_level] || RISK_STYLE.LOW;
  return (
    <div className={`border rounded p-2.5 space-y-1.5 ${style}`}>
      <div className="flex items-center justify-between text-[11px] font-mono font-bold">
        <span>{h.hazard_type.replace(/_/g, ' ')}</span>
        <span>{h.risk_level}</span>
      </div>
      <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400">
        <Sliders className="w-3 h-3" />
        M_ML {(h.m_ml * 100).toFixed(0)}%
        <span className={`px-1 rounded border ${h.m_ml_source === 'trained_model_real' ? 'border-emerald-500/40 text-emerald-300' : h.m_ml_source === 'trained_model' ? 'border-cyan-500/40 text-cyan-300' : 'border-slate-700 text-slate-400'}`}>
          {h.m_ml_source === 'trained_model_real' ? 'REAL-DATA MODEL' : h.m_ml_source === 'trained_model' ? 'TRAINED MODEL' : 'HEURISTIC'}
        </span>
      </div>
      {h.lead_time_meters != null && (
        <div className="text-[10px] font-mono text-slate-400">
          Look-ahead: <span className="text-slate-200">{h.lead_time_meters.toFixed(0)}m</span> to nearest historical corridor
        </div>
      )}
      {h.evidence_events.length > 0 && (
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
          <FileText className="w-3 h-3" /> {h.evidence_events.length} evidence event(s)
        </div>
      )}
      {h.recommended_action && (
        <div className="text-[10px] font-mono text-slate-300 pt-1 border-t border-slate-800/60 leading-snug">
          {h.recommended_action}
        </div>
      )}
    </div>
  );
}

export const LookAheadPanel: React.FC<{ analysis: NWISAnalysisResponse | null; loading: boolean }> = ({ analysis, loading }) => {
  const sorted = analysis
    ? [...analysis.hazard_assessments].sort((a, b) => b.composite_score - a.composite_score)
    : [];

  return (
    <div className="scada-panel h-full flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-800 flex items-center gap-2 shrink-0">
        <Brain className="w-4 h-4 text-cyan-400" />
        <span className="text-xs font-mono font-bold text-slate-200 uppercase">Look-Ahead Intelligence</span>
        <span
          className="ml-auto text-[9px] font-mono text-slate-600 normal-case cursor-help"
          title="Offset-well historical scoring — an independent calculation from the Risk & Prediction page's live sensor-fusion risk score. Different formula, not reconciled by design."
        >
          offset-well scoring
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2">
        {loading && <div className="text-[11px] font-mono text-slate-500 p-2">Analyzing...</div>}
        {!loading && !analysis && (
          <div className="text-[11px] font-mono text-slate-500 p-2">No analysis available for this well/depth.</div>
        )}
        {!loading && analysis && sorted.length === 0 && (
          <div className="text-[11px] font-mono text-slate-500 p-2">No hazard assessments returned.</div>
        )}
        {sorted.map((h) => <HazardCard key={h.hazard_type} h={h} />)}
        {analysis?.alert_message && (
          <div className="border border-rose-500/40 bg-rose-500/10 rounded p-2 flex items-start gap-2 text-[11px] font-mono text-rose-300">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            {analysis.alert_message}
          </div>
        )}
      </div>
    </div>
  );
};
