import React from 'react';
import { X, FileText } from 'lucide-react';
import { DrillingEvent } from '../../types';

// Click-to-expand event detail -- the genuinely good part of GeoMine's
// "Offset Well Deep-Dive": turning a table/chart row into real evidence
// (narrative, mitigation, outcome) rather than leaving it as a bare tick
// mark or hover tooltip. Built from DrillingEvent fields that already
// existed in our real data but were previously only shown as a hover
// tooltip in WellTrajectory3D.

const SEVERITY_STYLE: Record<string, string> = {
  CRITICAL: 'text-rose-400 border-rose-500/40',
  HIGH: 'text-amber-400 border-amber-500/40',
  MEDIUM: 'text-amber-300 border-amber-500/25',
  LOW: 'text-slate-300 border-slate-700',
};

export const EventDeepDive: React.FC<{ event: DrillingEvent | null; onClose: () => void }> = ({ event, onClose }) => {
  if (!event) return null;
  const style = SEVERITY_STYLE[event.severity] || SEVERITY_STYLE.LOW;

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-6" onClick={onClose}>
      <div
        className={`scada-panel w-full max-w-md border-l-4 ${style}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-3 border-b border-slate-800">
          <div className="flex items-center gap-2 text-xs font-mono font-bold">
            <FileText className="w-4 h-4" />
            {event.event_type.replace(/_/g, ' ')} · {event.severity}
          </div>
          <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-100">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-3 space-y-2 text-[11px] font-mono">
          <div className="text-slate-400">
            Well: <span className="text-slate-200">{event.well_id}</span> · {event.depth_start_md_m.toFixed(0)}m MD
            {event.formation && <> · {event.formation}</>}
          </div>
          {event.raw_narrative && (
            <div>
              <div className="text-slate-500 uppercase text-[9px] mb-0.5">Narrative</div>
              <div className="text-slate-300 leading-snug">{event.raw_narrative}</div>
            </div>
          )}
          {event.mitigation_description && (
            <div>
              <div className="text-slate-500 uppercase text-[9px] mb-0.5">Historical Mitigation</div>
              <div className="text-slate-300 leading-snug">{event.mitigation_description}</div>
            </div>
          )}
          {event.outcome && (
            <div>
              <div className="text-slate-500 uppercase text-[9px] mb-0.5">Outcome</div>
              <div className="text-slate-300 leading-snug">{event.outcome}</div>
            </div>
          )}
          {event.npt_hours > 0 && (
            <div className="text-slate-400">NPT: <span className="text-slate-200">{event.npt_hours}h</span></div>
          )}
          {event.source_document && (
            <div className="text-slate-600 text-[10px] pt-1 border-t border-slate-800">
              Source: {event.source_document}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
