import React from 'react';
import { Target, AlertTriangle, ShieldCheck } from 'lucide-react';
import { OffsetWellRanking } from '../../types';

// Visualizes WHY the top offset well ranked where it did -- the real
// 5-factor DORS math (engines/dors_engine.py), not just a final score.
// Every competitor demo shown in this engagement's research stops at "best
// match: X" with no explanation; this is the data analyzeWell() already
// returns (OffsetWellRanking.component_scores) with no UI surfacing it
// before now.

const FACTORS: { key: keyof OffsetWellRanking['component_scores']; label: string; weight: string }[] = [
  { key: 'spatial', label: 'Spatial Proximity', weight: '20%' },
  { key: 'formation', label: 'Formation Match', weight: '30%' },
  { key: 'depth', label: 'Depth Overlap', weight: '20%' },
  { key: 'trajectory', label: 'Trajectory Shape', weight: '15%' },
  { key: 'hazard', label: 'Hazard Proximity', weight: '15%' },
];

function Bar({ label, weight, value }: { label: string; weight: string; value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-slate-600';
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-[9px] font-mono text-slate-400">
        <span>{label} <span className="text-slate-600">({weight})</span></span>
        <span className="text-slate-300">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export const DorsBreakdownCard: React.FC<{ offsetWell: OffsetWellRanking | null }> = ({ offsetWell }) => {
  if (!offsetWell) {
    return (
      <div className="scada-panel p-2.5 text-[10px] font-mono text-slate-500">
        No offset well ranked yet.
      </div>
    );
  }

  const cs = offsetWell.component_scores;
  const faultBreach = cs.structural_fault_status === 'POSSIBLE_FAULT_BOUNDARY';

  return (
    <div className="scada-panel p-2.5 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-slate-200 uppercase">
          <Target className="w-3.5 h-3.5 text-cyan-400" /> Why {offsetWell.well_name}?
        </div>
        <span className={`text-xs font-mono font-bold ${faultBreach ? 'text-rose-400' : 'text-cyan-300'}`}>
          {(cs.total * 100).toFixed(0)}% DORS
        </span>
      </div>

      {cs.structural_fault_status && (
        <div className={`flex items-center gap-1.5 text-[9px] font-mono px-2 py-1 rounded border ${
          faultBreach ? 'border-rose-500/40 bg-rose-500/5 text-rose-300' : 'border-slate-800 bg-slate-900/40 text-slate-500'
        }`}>
          {faultBreach ? <AlertTriangle className="w-3 h-3 shrink-0" /> : <ShieldCheck className="w-3 h-3 shrink-0" />}
          {faultBreach
            ? 'Possible fault boundary — score cut to 20% of pre-penalty value (regional dip + throw heuristic)'
            : 'Same fault block — no structural penalty applied'}
        </div>
      )}

      <div className="space-y-1.5">
        {FACTORS.map((f) => (
          <Bar key={f.key} label={f.label} weight={f.weight} value={cs[f.key] as number} />
        ))}
      </div>
      <div className="text-[9px] font-mono text-slate-600 pt-1 border-t border-slate-800/60">
        {offsetWell.distance_km.toFixed(1)}km away &middot; {offsetWell.formation_match} &middot; {offsetWell.events_in_lookahead} event(s) in lookahead
      </div>
    </div>
  );
};
