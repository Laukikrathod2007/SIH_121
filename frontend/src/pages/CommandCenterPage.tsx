import React, { useState } from 'react';
import { Radar } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useCommandCenterData } from '../hooks/useCommandCenterData';
import { CommandScene3D } from '../components/commandcenter/CommandScene3D';
import { LookAheadPanel } from '../components/commandcenter/LookAheadPanel';
import { DepthCorrelationStrip } from '../components/commandcenter/DepthCorrelationStrip';
import { TelemetryHUD } from '../components/commandcenter/TelemetryHUD';
import { WellListPanel } from '../components/commandcenter/WellListPanel';

// The IVAAP/DrillPlan/Tela-inspired command center, built directly against
// real Module 02 endpoints from the start (trajectory, analyzeWell, real
// depth-indexed telemetry) rather than AppContext's Module-03-bound
// placeholder state. Deliberately its own page/route -- see the
// visualization audit for why LiveDrillingPage's existing 3D work
// (functionally solid, wired to routes that didn't exist) wasn't a safe
// place to retrofit this without risking what already works there.
export const CommandCenterPage: React.FC = () => {
  const { wells, activeWellId, setActiveWellId } = useApp();
  const [radiusKm, setRadiusKm] = useState(25);

  const {
    trajectory, formations, events, depth, setDepth, minDepth, maxDepth,
    analysis, analysisLoading, telemetry, offsetWell, offsetTrajectory, offsetEvents,
  } = useCommandCenterData(activeWellId, radiusKm);

  const activeWell = wells.find((w) => w.well_id === activeWellId);
  const corridors = analysis?.active_risk_corridors ?? [];

  return (
    <div className="p-4 space-y-3 h-full flex flex-col">
      {/* Header */}
      <div className="scada-panel px-4 py-2.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <Radar className="w-4 h-4 text-cyan-400" />
          <span className="text-sm font-mono font-bold text-slate-100">NWIS COMMAND CENTER</span>
          <span className="text-xs font-mono text-slate-400">{activeWell?.well_name ?? activeWellId}</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <span className="flex items-center gap-1 px-2 py-0.5 rounded border border-cyan-500/40 bg-cyan-500/10 text-cyan-300">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" /> REPLAY
          </span>
          <span className="text-slate-400">MD {depth.toFixed(0)}m</span>
        </div>
      </div>

      {/* Main 3-column layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[240px_1fr_300px] gap-3 min-h-0">
        <div className="min-h-[300px] lg:min-h-0">
          <WellListPanel
            wells={wells}
            activeWellId={activeWellId}
            onSelectWell={setActiveWellId}
            offsetWell={offsetWell}
            radiusKm={radiusKm}
            onRadiusChange={setRadiusKm}
            depth={depth}
            minDepth={minDepth}
            maxDepth={maxDepth}
            onDepthChange={setDepth}
          />
        </div>

        <div className="scada-panel overflow-hidden min-h-[360px] lg:min-h-0">
          <CommandScene3D
            activeTrajectory={trajectory}
            offsetTrajectory={offsetTrajectory}
            formations={formations}
            events={events}
            corridors={corridors}
            depth={depth}
            offsetWellName={offsetWell?.well_name}
          />
        </div>

        <div className="min-h-[300px] lg:min-h-0">
          <LookAheadPanel analysis={analysis} loading={analysisLoading} />
        </div>
      </div>

      {/* Bottom: depth correlation + telemetry HUD */}
      <div className="shrink-0 space-y-2">
        <DepthCorrelationStrip
          activeLabel={activeWell?.well_name ?? activeWellId}
          activeEvents={events}
          offsetLabel={offsetWell?.well_name}
          offsetEvents={offsetEvents}
          currentDepth={depth}
          minDepth={minDepth}
          maxDepth={maxDepth}
        />
        <TelemetryHUD telemetry={telemetry} depth={depth} />
      </div>
    </div>
  );
};
