import React from 'react';
import { Layers } from 'lucide-react';
import { CasingRecord } from '../../types';

// Real casing data for 2 real Volve wells (GET /api/v2/casing/{well_id} --
// an endpoint that didn't exist until it was added directly in this
// session: data_store.py already loaded it from real_data/, nothing served
// it). Every synthetic well has none -- shown honestly, not hidden.

export const CasingProgramPanel: React.FC<{ casing: CasingRecord[]; wellName: string }> = ({ casing, wellName }) => {
  if (casing.length === 0) {
    return (
      <div className="scada-panel h-full flex flex-col overflow-hidden">
        <div className="px-3 py-2 border-b border-slate-800 flex items-center gap-2 shrink-0">
          <Layers className="w-4 h-4 text-slate-500" />
          <span className="text-xs font-mono font-bold text-slate-400 uppercase">Casing Program</span>
        </div>
        <div className="flex-1 flex items-center justify-center p-3 text-center">
          <div className="text-[10px] font-mono text-slate-600 leading-relaxed">
            No casing data for {wellName}.<br />
            Real casing records currently exist for 2 real Volve wells only (15/9-F-12, 15/9-F-1).
          </div>
        </div>
      </div>
    );
  }

  const sorted = [...casing].sort((a, b) => a.shoe_depth_md_m - b.shoe_depth_md_m);
  const maxDepth = sorted[sorted.length - 1].shoe_depth_md_m;
  const maxSize = Math.max(...sorted.map((c) => c.casing_size_inches ?? 0), 1);

  return (
    <div className="scada-panel h-full flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono font-bold text-slate-200 uppercase">Casing Program</span>
        </div>
        <span className="text-[9px] font-mono text-emerald-400 border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 rounded">
          REAL DATA
        </span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {sorted.map((c, i) => {
          const widthPct = ((c.casing_size_inches ?? maxSize * 0.3) / maxSize) * 100;
          const depthPct = (c.shoe_depth_md_m / maxDepth) * 100;
          return (
            <div key={`${c.well_id}-${i}`} className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-mono">
                <span className="text-slate-300 font-bold">
                  {c.casing_size_inches != null ? `${c.casing_size_inches}"` : 'Unknown size'} casing
                </span>
                <span className="text-slate-500">Shoe @ {c.shoe_depth_md_m.toFixed(0)}m</span>
              </div>
              <div className="relative h-2.5 bg-slate-900 rounded-sm border border-slate-800">
                <div
                  className="absolute left-0 top-0 h-full bg-gradient-to-r from-cyan-600/70 to-cyan-500/40 rounded-sm"
                  style={{ width: `${Math.max(depthPct, 4)}%`, maxWidth: `${widthPct > 0 ? 100 : 100}%` }}
                />
              </div>
              {c.top_of_cement_md_m != null && (
                <div className="text-[9px] font-mono text-slate-600">
                  TOC: {c.top_of_cement_md_m.toFixed(0)}m
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="px-3 py-1.5 border-t border-slate-800/60 text-[9px] font-mono text-slate-600 shrink-0">
        {sorted.length} string(s) &middot; deepest shoe {maxDepth.toFixed(0)}m
      </div>
    </div>
  );
};
