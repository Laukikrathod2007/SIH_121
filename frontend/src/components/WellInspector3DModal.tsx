import React, { useEffect, useState } from 'react';
import { X, Box, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { WellTrajectory, FormationTop, DrillingEvent } from '../types';
import { WellTrajectory3D } from './WellTrajectory3D';

interface WellInspector3DModalProps {
  wellId: string;
  wellName: string;
  offsetWellId?: string | null;
  offsetWellName?: string | null;
  onClose: () => void;
}

export const WellInspector3DModal: React.FC<WellInspector3DModalProps> = ({
  wellId,
  wellName,
  offsetWellId,
  offsetWellName,
  onClose,
}) => {
  const [trajectory, setTrajectory] = useState<WellTrajectory | null>(null);
  const [offsetTrajectory, setOffsetTrajectory] = useState<WellTrajectory | null>(null);
  const [formations, setFormations] = useState<FormationTop[]>([]);
  const [events, setEvents] = useState<DrillingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [traj, forms, evts, offsetTraj] = await Promise.all([
          api.getTrajectory(wellId),
          api.getFormations(wellId),
          api.getWellEvents(wellId),
          offsetWellId ? api.getTrajectory(offsetWellId).catch(() => null) : Promise.resolve(null),
        ]);
        if (cancelled) return;
        setTrajectory(traj);
        setFormations(forms);
        setEvents(evts);
        setOffsetTrajectory(offsetTraj);
      } catch (err) {
        if (!cancelled) setError('No real trajectory data available for this well.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [wellId, offsetWellId]);

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-6" onClick={onClose}>
      <div
        className="scada-panel w-full max-w-6xl h-[85vh] flex flex-col border-l-4 border-l-cyan-500"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-3 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
              <Box className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-100">3D WELLBORE TRAJECTORY: {wellName}</div>
              <div className="text-[11px] font-mono text-slate-400">
                Real minimum-curvature survey path
                {offsetWellName && <> · offset comparison: <span className="text-amber-400">{offsetWellName}</span></>}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-100 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 relative bg-[#090c12]">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center text-slate-400 font-mono text-xs gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading real survey data...
            </div>
          )}
          {!loading && error && (
            <div className="absolute inset-0 flex items-center justify-center text-rose-400 font-mono text-xs">
              {error}
            </div>
          )}
          {!loading && !error && trajectory && (
            <WellTrajectory3D
              activeTrajectory={trajectory}
              offsetTrajectory={offsetTrajectory}
              formations={formations}
              events={events}
            />
          )}
        </div>

        <div className="p-2 border-t border-slate-800 text-[10px] font-mono text-slate-500 shrink-0 flex items-center justify-between">
          <span>Drag to orbit · scroll to zoom · hover a marker for the real hazard narrative</span>
          <span>Source: GET /api/v2/trajectory/{'{well_id}'}</span>
        </div>
      </div>
    </div>
  );
};
