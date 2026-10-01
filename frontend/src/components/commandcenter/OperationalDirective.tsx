import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { NWISAnalysisResponse } from '../../types';

// The genuinely good part of GeoMine's "Operational Directive" banner --
// turning a raw risk score into a plain-English instruction -- built here
// from the highest-composite-score hazard in analyzeWell's real response,
// with the same m_ml_source disclosure already used elsewhere in this
// app rather than presenting it as an unqualified AI verdict.

const BORDER_COLOR: Record<string, string> = {
  CRITICAL: 'border-l-rose-500 bg-rose-500/5',
  HIGH: 'border-l-amber-500 bg-amber-500/5',
  MODERATE: 'border-l-amber-400/70 bg-amber-500/5',
  LOW: 'border-l-emerald-500 bg-emerald-500/5',
};

export const OperationalDirective: React.FC<{ analysis: NWISAnalysisResponse | null }> = ({ analysis }) => {
  if (!analysis || analysis.hazard_assessments.length === 0) return null;

  const top = [...analysis.hazard_assessments].sort((a, b) => b.composite_score - a.composite_score)[0];
  const style = BORDER_COLOR[top.risk_level] || BORDER_COLOR.LOW;

  return (
    <div className={`border-l-4 rounded px-4 py-2.5 ${style}`}>
      <div className="flex items-center gap-2 text-xs font-mono font-bold text-slate-100">
        <AlertTriangle className="w-4 h-4" />
        OPERATIONAL DIRECTIVE — {top.risk_level} ({top.hazard_type.replace(/_/g, ' ')})
        <span className={`ml-auto text-[9px] px-1.5 py-0.5 rounded border ${top.m_ml_source === 'trained_model' ? 'border-cyan-500/40 text-cyan-300' : 'border-slate-700 text-slate-400'}`}>
          {top.m_ml_source === 'trained_model' ? 'TRAINED MODEL' : 'HEURISTIC ESTIMATE'}
        </span>
      </div>
      <div className="text-[11px] font-mono text-slate-300 mt-1">
        {top.recommended_action || 'No specific recommendation available for this hazard.'}
      </div>
      {top.evidence_events.length > 0 && (
        <div className="text-[10px] font-mono text-slate-500 mt-1">
          Based on {top.evidence_events.length} real evidence event(s) from offset wells.
        </div>
      )}
    </div>
  );
};
