import React, { useState } from 'react';
import { Radar } from 'lucide-react';
import { AheadOfBitCorridor, AheadOfBitCorridorPoint } from '../../types';

// GET /api/v2/ahead_of_bit/{well_id} -- 0-200m projected risk density ahead
// of the bit (engines/risk_corridor_engine.py::compute_ahead_of_bit_corridor),
// a real, working endpoint with no prior frontend consumer. This is the
// literal visualization of PS 26121's proactive-alert requirement: showing
// what's coming before the bit gets there, not just what already happened.

const TIER_STYLE: Record<string, { label: string; border: string }> = {
  IMMEDIATE_0_20M: { label: 'IMMEDIATE', border: 'border-rose-500/50' },
  SHORT_TERM_20_50M: { label: 'SHORT-TERM', border: 'border-amber-500/40' },
  LOOKAHEAD_50_200M: { label: 'LOOKAHEAD', border: 'border-slate-700' },
};

function maxRisk(point: AheadOfBitCorridorPoint): { hazard: string; value: number } {
  let best = { hazard: '', value: 0 };
  for (const [hazard, value] of Object.entries(point.hazard_risk)) {
    if (value > best.value) best = { hazard, value };
  }
  return best;
}

function riskColor(v: number): string {
  if (v >= 0.6) return 'bg-rose-500';
  if (v >= 0.35) return 'bg-amber-500';
  if (v > 0.05) return 'bg-amber-500/40';
  return 'bg-slate-700';
}

export const AheadOfBitStrip: React.FC<{ corridor: AheadOfBitCorridor | null; loading: boolean }> = ({ corridor, loading }) => {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  if (loading) {
    return <div className="scada-panel px-4 py-3 text-[10px] font-mono text-slate-500">Projecting ahead of bit...</div>;
  }
  if (!corridor || corridor.points.length === 0) {
    return <div className="scada-panel px-4 py-3 text-[10px] font-mono text-slate-600">No ahead-of-bit projection available.</div>;
  }

  const hovered = hoverIdx != null ? corridor.points[hoverIdx] : null;
  const hoveredRisk = hovered ? maxRisk(hovered) : null;

  return (
    <div className="scada-panel px-3 py-2.5 shrink-0">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-slate-200 uppercase">
          <Radar className="w-3.5 h-3.5 text-cyan-400" /> Ahead-of-Bit Risk Projection
        </div>
        <span className="text-[9px] font-mono text-slate-500">
          Bit {corridor.current_md_m.toFixed(0)}m &middot; {corridor.current_formation ?? 'Unknown formation'}
        </span>
      </div>

      <div className="flex items-end gap-px h-10">
        {corridor.points.map((p, i) => {
          const r = maxRisk(p);
          return (
            <div
              key={i}
              className="flex-1 h-full flex flex-col justify-end cursor-default group"
              onMouseEnter={() => setHoverIdx(i)}
              onMouseLeave={() => setHoverIdx(null)}
            >
              <div
                className={`w-full ${riskColor(r.value)} rounded-t-sm transition-all ${hoverIdx === i ? 'ring-1 ring-cyan-400' : ''}`}
                style={{ height: `${Math.max(r.value * 100, 6)}%` }}
              />
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between mt-1 text-[8px] font-mono text-slate-600">
        <span>+0m</span>
        <span>+{(corridor.points[corridor.points.length - 1]?.depth_ahead_m ?? 0).toFixed(0)}m ahead</span>
      </div>

      <div className="flex items-center gap-3 mt-1.5 pt-1.5 border-t border-slate-800/60 text-[9px] font-mono min-h-[14px]">
        {hovered && hoveredRisk ? (
          <>
            <span className={`px-1.5 py-0.5 rounded border ${TIER_STYLE[hovered.window_tier]?.border ?? 'border-slate-700'} text-slate-300`}>
              {TIER_STYLE[hovered.window_tier]?.label ?? hovered.window_tier}
            </span>
            <span className="text-slate-400">
              +{hovered.depth_ahead_m.toFixed(0)}m ({hovered.md_m.toFixed(0)}m MD)
            </span>
            {hoveredRisk.value > 0.05 ? (
              <span className="text-slate-300">
                {hoveredRisk.hazard.replace(/_/g, ' ')} risk: <span className="font-bold">{(hoveredRisk.value * 100).toFixed(0)}%</span>
              </span>
            ) : (
              <span className="text-slate-600">No elevated hazard density</span>
            )}
            {hovered.evidence_count > 0 && (
              <span className="text-slate-600">&middot; {hovered.evidence_count} evidence event(s)</span>
            )}
          </>
        ) : (
          <span className="text-slate-600">Hover a bar to inspect that depth-ahead step</span>
        )}
      </div>
    </div>
  );
};
