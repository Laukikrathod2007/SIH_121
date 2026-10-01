import React from 'react';
import { Well, OffsetWellRanking } from '../../types';

const RADIUS_OPTIONS = [1, 3, 5, 10, 25];

interface WellListPanelProps {
  wells: Well[];
  activeWellId: string;
  onSelectWell: (id: string) => void;
  offsetWell: OffsetWellRanking | null;
  radiusKm: number;
  onRadiusChange: (r: number) => void;
  depth: number;
  minDepth: number;
  maxDepth: number;
  onDepthChange: (d: number) => void;
}

// Real wells only, with real-trajectory wells (the 2 fully-real Volve
// wells) visually distinguished from the synthetic Assam-Arakan set --
// per the competitor audit's own recommendation (repo02/repo03 both label
// synthetic data explicitly rather than blending it in unlabeled).
const REAL_TRAJECTORY_WELLS = new Set(['15/9-F-12', '15/9-F-1']);

export const WellListPanel: React.FC<WellListPanelProps> = ({
  wells, activeWellId, onSelectWell, offsetWell, radiusKm, onRadiusChange,
  depth, minDepth, maxDepth, onDepthChange,
}) => {
  return (
    <div className="scada-panel h-full flex flex-col overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-800 shrink-0">
        <span className="text-xs font-mono font-bold text-slate-200 uppercase">Well / Offset</span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {wells.map((w) => {
          const isActive = w.well_id === activeWellId;
          const isOffset = w.well_id === offsetWell?.well_id;
          const isReal = REAL_TRAJECTORY_WELLS.has(w.well_id);
          return (
            <button
              key={w.well_id}
              onClick={() => onSelectWell(w.well_id)}
              className={`w-full text-left px-2.5 py-1.5 rounded text-[11px] font-mono flex items-center justify-between gap-2 transition-colors ${
                isActive ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40'
                : isOffset ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                : 'text-slate-400 hover:bg-slate-800/50 border border-transparent'
              }`}
            >
              <span className="flex items-center gap-1.5 truncate">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isActive ? 'bg-cyan-400' : isOffset ? 'bg-amber-400' : 'bg-slate-600'}`} />
                {w.well_name}
              </span>
              {!isReal && <span className="text-[9px] text-slate-600 shrink-0">SYNTH</span>}
            </button>
          );
        })}
      </div>

      <div className="p-2.5 border-t border-slate-800 space-y-2.5 shrink-0">
        <div>
          <div className="text-[10px] font-mono text-slate-500 uppercase mb-1">Radius (km)</div>
          <div className="flex gap-1">
            {RADIUS_OPTIONS.map((r) => (
              <button
                key={r}
                onClick={() => onRadiusChange(r)}
                className={`flex-1 py-1 rounded text-[10px] font-mono ${
                  radiusKm === r ? 'bg-cyan-500 text-slate-950 font-bold' : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 uppercase mb-1">
            <span>Depth</span>
            <span className="text-cyan-400">{depth.toFixed(0)}m</span>
          </div>
          <input
            type="range"
            min={minDepth}
            max={maxDepth}
            step={5}
            value={depth}
            onChange={(e) => onDepthChange(Number(e.target.value))}
            className="w-full accent-cyan-500"
          />
        </div>
      </div>
    </div>
  );
};
