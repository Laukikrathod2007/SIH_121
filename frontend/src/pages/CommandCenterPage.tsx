import React, { useState } from 'react';
import { Radar, Download } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { useCommandCenterData } from '../hooks/useCommandCenterData';
import { CommandScene3D } from '../components/commandcenter/CommandScene3D';
import { LookAheadPanel } from '../components/commandcenter/LookAheadPanel';
import { DepthCorrelationStrip } from '../components/commandcenter/DepthCorrelationStrip';
import { TelemetryHUD } from '../components/commandcenter/TelemetryHUD';
import { WellListPanel } from '../components/commandcenter/WellListPanel';
import { KPIStrip } from '../components/commandcenter/KPIStrip';
import { OperationalDirective } from '../components/commandcenter/OperationalDirective';
import { EventDeepDive } from '../components/commandcenter/EventDeepDive';
import { downloadCSV } from '../lib/csvExport';
import { DrillingEvent } from '../types';

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
  const [selectedEvent, setSelectedEvent] = useState<DrillingEvent | null>(null);

  const {
    trajectory, formations, events, depth, setDepth, minDepth, maxDepth,
    analysis, analysisLoading, telemetry, offsetWell, offsetTrajectory, offsetEvents,
  } = useCommandCenterData(activeWellId, radiusKm);

  const activeWell = wells.find((w) => w.well_id === activeWellId);
  const corridors = analysis?.active_risk_corridors ?? [];

  const handleExportOffsets = () => {
    if (!analysis || analysis.offset_rankings.length === 0) return;
    downloadCSV(
      `offset_wells_${activeWellId.replace(/\//g, '-')}_${depth.toFixed(0)}m.csv`,
      analysis.offset_rankings.map((r) => ({
        rank: r.rank, well_id: r.well_id, well_name: r.well_name, field: r.field,
        well_type: r.well_type, dors_score: r.dors_score, distance_km: r.distance_km,
        formation_match: r.formation_match, events_in_lookahead: r.events_in_lookahead,
      })),
    );
  };

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
          <button
            onClick={handleExportOffsets}
            disabled={!analysis || analysis.offset_rankings.length === 0}
            className="flex items-center gap-1 px-2 py-0.5 rounded border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-3 h-3" /> Export Offsets CSV
          </button>
        </div>
      </div>

      {/* KPI strip + operational directive */}
      <div className="shrink-0 space-y-2">
        <KPIStrip analysis={analysis} eventCount={events.length} />
        <OperationalDirective analysis={analysis} />
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
            onEventClick={setSelectedEvent}
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
          onEventClick={setSelectedEvent}
        />
        <TelemetryHUD telemetry={telemetry} depth={depth} />
      </div>

      <EventDeepDive event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
};
