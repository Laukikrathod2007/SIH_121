import React, { useState } from 'react';
import { Radar, Download, Box, Map as MapIcon, ChevronDown, ChevronUp } from 'lucide-react';
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
import { BackendStatusStrip } from '../components/commandcenter/BackendStatusStrip';
import { DorsBreakdownCard } from '../components/commandcenter/DorsBreakdownCard';
import { ConfidencePillars } from '../components/commandcenter/ConfidencePillars';
import { CasingProgramPanel } from '../components/commandcenter/CasingProgramPanel';
import { AheadOfBitStrip } from '../components/commandcenter/AheadOfBitStrip';
import { BasinMap } from '../components/BasinMap';
import { downloadCSV } from '../lib/csvExport';
import { DrillingEvent } from '../types';

type ViewMode = '3D' | 'MAP';

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
  const [viewMode, setViewMode] = useState<ViewMode>('3D');
  const [bottomExpanded, setBottomExpanded] = useState(true);

  const {
    trajectory, formations, events, depth, setDepth, minDepth, maxDepth,
    analysis, analysisLoading, telemetry, offsetWell, offsetTrajectory, offsetEvents,
    casing, aheadOfBit, aheadOfBitLoading,
  } = useCommandCenterData(activeWellId, radiusKm);

  const activeWell = wells.find((w) => w.well_id === activeWellId);
  const corridors = analysis?.active_risk_corridors ?? [];
  const topHazard = analysis && analysis.hazard_assessments.length > 0
    ? [...analysis.hazard_assessments].sort((a, b) => b.composite_score - a.composite_score)[0]
    : null;

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

      {/* Live backend status -- genuinely health-checked, not hardcoded */}
      <div className="shrink-0">
        <BackendStatusStrip />
      </div>

      {/* Alert-first ordering (mission-control convention): the single
          highest-severity directive and its confidence decomposition sit
          above the glanceable KPI row, not below it. */}
      <div className="shrink-0 space-y-2">
        <OperationalDirective analysis={analysis} />
        {topHazard && <ConfidencePillars hazard={topHazard} />}
        <KPIStrip analysis={analysis} eventCount={events.length} />
      </div>

      {/* Main 3-column layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[260px_1fr_320px] gap-3 min-h-0">
        <div className="min-h-[300px] lg:min-h-0 flex flex-col gap-3">
          <div className="flex-1 min-h-[200px]">
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
          <div className="h-[220px] shrink-0">
            <CasingProgramPanel casing={casing} wellName={activeWell?.well_name ?? activeWellId} />
          </div>
        </div>

        <div className="scada-panel overflow-hidden min-h-[360px] lg:min-h-0 flex flex-col">
          {/* 3D / Map view toggle -- the "different maps" integration,
              sharing the same well-list/look-ahead side panels rather
              than duplicating them on a separate page. */}
          <div className="flex items-center gap-1 p-1.5 border-b border-slate-800 shrink-0">
            <button
              onClick={() => setViewMode('3D')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono ${
                viewMode === '3D' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Box className="w-3.5 h-3.5" /> 3D Subsurface
            </button>
            <button
              onClick={() => setViewMode('MAP')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono ${
                viewMode === 'MAP' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MapIcon className="w-3.5 h-3.5" /> Field Map
            </button>
          </div>
          <div className="flex-1 min-h-0">
            {viewMode === '3D' ? (
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
            ) : (
              <BasinMap
                wells={wells}
                activeWellId={activeWellId}
                selectedWellId={offsetWell?.well_id ?? activeWellId}
                onSelectWell={setActiveWellId}
                radiusKm={radiusKm}
              />
            )}
          </div>
        </div>

        <div className="min-h-[300px] lg:min-h-0 flex flex-col gap-2">
          <DorsBreakdownCard offsetWell={offsetWell} />
          <div className="flex-1 min-h-[200px]">
            <LookAheadPanel analysis={analysis} loading={analysisLoading} />
          </div>
        </div>
      </div>

      {/* Forward-looking risk projection -- real ahead_of_bit endpoint,
          literally PS 26121's "proactive alert" requirement visualized. */}
      <div className="shrink-0">
        <AheadOfBitStrip corridor={aheadOfBit} loading={aheadOfBitLoading} />
      </div>

      {/* Bottom: depth correlation + telemetry HUD -- collapsible to
          reduce on-screen density when not needed. */}
      <div className="shrink-0 space-y-2">
        <button
          onClick={() => setBottomExpanded(!bottomExpanded)}
          className="w-full flex items-center justify-center gap-1.5 text-[10px] font-mono text-slate-500 hover:text-slate-300 py-0.5"
        >
          {bottomExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
          {bottomExpanded ? 'Hide' : 'Show'} Depth Correlation & Telemetry
        </button>
        {bottomExpanded && (
          <>
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
          </>
        )}
      </div>

      <EventDeepDive event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </div>
  );
};
