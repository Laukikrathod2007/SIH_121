import React from 'react';
import { DrillingEvent } from '../../types';

// DrillingMetrics-style depth-aligned track comparison: active well vs.
// offset well, events plotted as ticks along a shared depth axis, current
// bit depth as a vertical marker. Real data only -- no synthetic filler
// tracks. Deliberately 2 tracks (active + top real offset), not 4, since
// that's what real trajectory-and-event data currently supports; adding
// more tracks would mean either fabricating offset wells or silently
// mixing in synthetic ones unlabeled.

const SEVERITY_COLOR: Record<string, string> = { CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#f59e0b', LOW: '#eab308' };

function Track({ label, currentPct, events, minMd, maxMd }: {
  label: string; currentPct: number; events: DrillingEvent[]; minMd: number; maxMd: number;
}) {
  const span = Math.max(maxMd - minMd, 1);
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 shrink-0 text-[10px] font-mono text-slate-400 truncate">{label}</div>
      <div className="relative flex-1 h-5 bg-slate-900/60 rounded border border-slate-800">
        {events.map((e) => {
          const pct = Math.min(100, Math.max(0, ((e.depth_start_md_m - minMd) / span) * 100));
          const c = SEVERITY_COLOR[e.severity] || '#94a3b8';
          return (
            <div
              key={e.event_id}
              title={`${e.event_type} @ ${e.depth_start_md_m.toFixed(0)}m (${e.severity})`}
              className="absolute top-0.5 bottom-0.5 w-1 rounded-full"
              style={{ left: `${pct}%`, backgroundColor: c }}
            />
          );
        })}
        <div className="absolute inset-y-0 w-px bg-cyan-400" style={{ left: `${currentPct}%` }} />
      </div>
    </div>
  );
}

interface DepthCorrelationStripProps {
  activeLabel: string;
  activeEvents: DrillingEvent[];
  offsetLabel?: string;
  offsetEvents: DrillingEvent[];
  currentDepth: number;
  minDepth: number;
  maxDepth: number;
}

export const DepthCorrelationStrip: React.FC<DepthCorrelationStripProps> = ({
  activeLabel, activeEvents, offsetLabel, offsetEvents, currentDepth, minDepth, maxDepth,
}) => {
  const span = Math.max(maxDepth - minDepth, 1);
  const currentPct = Math.min(100, Math.max(0, ((currentDepth - minDepth) / span) * 100));

  return (
    <div className="scada-panel px-3 py-2.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-mono font-bold text-slate-300 uppercase">Depth / Event Correlation</span>
        <span className="text-[10px] font-mono text-cyan-400">{currentDepth.toFixed(0)}m MD</span>
      </div>
      <div className="space-y-1.5">
        <Track label={activeLabel} currentPct={currentPct} events={activeEvents} minMd={minDepth} maxMd={maxDepth} />
        {offsetLabel && (
          <Track label={offsetLabel} currentPct={currentPct} events={offsetEvents} minMd={minDepth} maxMd={maxDepth} />
        )}
      </div>
      <div className="flex justify-between text-[9px] font-mono text-slate-600 mt-1">
        <span>{minDepth.toFixed(0)}m</span>
        <span>{maxDepth.toFixed(0)}m</span>
      </div>
    </div>
  );
};
