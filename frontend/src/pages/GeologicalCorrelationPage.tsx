import React, { useState, useEffect, useMemo } from 'react';
import {
  Layers,
  TrendingDown,
  CheckCircle,
  Loader2,
  Pin,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { HorizonAlignmentEntry, FormationTop, RiskCorridor, DrillingEvent, OffsetWellRanking } from '../types';

// This page uses ONLY real modules/02_nwis_backend endpoints:
//   GET /api/v2/offset_rank/{well_id}                (DORS 5-factor ranking -> top-3 most
//                                                       geologically relevant offset wells)
//   GET /api/v2/stratigraphic_depth_track/{well_id}  (horizon alignment across offset wells)
//   GET /api/v2/formations/{well_id}                 (top/base/thickness for the xi gauge)
//   GET /api/v2/events/{well_id}                     (historical events at the offset well)
//   GET /api/v2/corridors/{well_id}                  (the "ahead-of-bit" lookahead section)
//
// Per PS 26121, this page shows the active well's stratigraphic column
// side-by-side with the top 3 most geologically relevant historical offset
// wells SIMULTANEOUSLY (not one at a time via a dropdown).
//
// stratigraphic_depth_track internally calls the SAME DORS ranking function
// as /offset_rank (see modules/02_nwis_backend/server.py's
// stratigraphic_depth_track() -> engines/dors_engine.py's rank_offset_wells())
// to decide which offset wells to align, then returns a dict keyed by
// well_id for ALL of them in one call. So requesting it once with
// top_n=10 (as this page already did) already carries real alignment data
// for far more than just 3 wells -- we do NOT fire 3 extra
// stratigraphic_depth_track calls to build the 3 columns, we just render
// more of what a single call already returns. We DO fire one extra call to
// /offset_rank (the same call DashboardPage.tsx already makes) purely to
// get the real DORS rank/score/component-score labels for those wells --
// the alignment endpoint's response dict has no explicit rank ordering
// field of its own.
//
// Our backend has no per-formation xi in [0,1] field and no xi_correlate
// endpoint (Prasad's backend did) -- xi below is computed client-side from
// two real numbers: d_strat_m (TVD penetration into the formation, from the
// alignment endpoint) / the formation's real thickness_m (from
// /formations/{well_id}). That's a genuine derived ratio, not a fabricated
// one.

interface OffsetDetail {
  formations: FormationTop[];
  events: DrillingEvent[];
}

export const GeologicalCorrelationPage: React.FC = () => {
  const { activeWellId, telemetry, wells } = useApp();

  const offsetCandidates = wells.filter((w) => w.well_id !== activeWellId);
  const [pinnedOffsetId, setPinnedOffsetId] = useState<string>('');
  const [alignment, setAlignment] = useState<Record<string, HorizonAlignmentEntry>>({});
  const [activeFormations, setActiveFormations] = useState<FormationTop[]>([]);
  const [offsetRankings, setOffsetRankings] = useState<OffsetWellRanking[]>([]);
  const [offsetDetails, setOffsetDetails] = useState<Record<string, OffsetDetail>>({});
  const [corridors, setCorridors] = useState<RiskCorridor[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [detailsLoading, setDetailsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const depth = telemetry?.measured_depth_m || 2450.0;

  // Fetch: DORS ranking, stratigraphic alignment (all offset wells in one
  // call), active well formations, and lookahead corridors.
  useEffect(() => {
    if (!activeWellId) return;
    let cancelled = false;
    const fetchCorrelation = async () => {
      setLoading(true);
      setError(null);
      try {
        const [rankRes, alignRes, activeForms, corridorRes] = await Promise.all([
          api.getOffsetRank(activeWellId, depth, 25.0, 10),
          api.getStratigraphicDepthTrack(activeWellId, depth, 10),
          api.getFormations(activeWellId),
          api.getRiskCorridors(activeWellId, depth),
        ]);
        if (cancelled) return;
        setOffsetRankings(rankRes.rankings || []);
        setAlignment(alignRes.alignment || {});
        setActiveFormations(activeForms);
        setCorridors(corridorRes.corridors || []);
      } catch (err) {
        if (!cancelled) setError('Could not load stratigraphic correlation data. Contact your system administrator if this persists.');
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchCorrelation();
    return () => { cancelled = true; };
  }, [activeWellId, Math.floor(depth / 20)]);

  // Top 3 most geologically relevant offset wells, per real DORS ranking.
  const topOffsetIds = useMemo(
    () => offsetRankings.slice(0, 3).map((r) => r.well_id),
    [offsetRankings],
  );

  // Optional user override: pin one specific well as an extra column (kept
  // from the old single-well dropdown) if it isn't already one of the auto
  // top-3 wells.
  const pinnedExtraId = pinnedOffsetId && !topOffsetIds.includes(pinnedOffsetId) ? pinnedOffsetId : null;

  const columnIds = useMemo(
    () => (pinnedExtraId ? [...topOffsetIds, pinnedExtraId] : topOffsetIds),
    [topOffsetIds, pinnedExtraId],
  );

  // Per-column detail fetch: formations + events for each offset well
  // actually being displayed (top-3, plus the pinned override if distinct).
  useEffect(() => {
    if (columnIds.length === 0) {
      setOffsetDetails({});
      setDetailsLoading(false);
      return;
    }
    let cancelled = false;
    setDetailsLoading(true);
    (async () => {
      const entries = await Promise.all(
        columnIds.map(async (id) => {
          try {
            const [forms, evts] = await Promise.all([
              api.getFormations(id),
              api.getWellEvents(id),
            ]);
            return [id, { formations: forms, events: evts }] as const;
          } catch (err) {
            console.error('Failed to load offset well detail', id, err);
            return [id, { formations: [], events: [] }] as const;
          }
        }),
      );
      if (cancelled) return;
      setOffsetDetails(Object.fromEntries(entries));
      setDetailsLoading(false);
    })();
    return () => { cancelled = true; };
  }, [columnIds.join(',')]);

  const activeAlign = alignment[activeWellId];

  const activeFormation = useMemo(
    () => activeFormations.find((f) => f.formation_name === activeAlign?.formation) || activeFormations[0],
    [activeFormations, activeAlign],
  );

  // xi in [0,1]: real d_strat_m (TVD penetration into formation) / real thickness_m.
  const activeXi = activeFormation && activeFormation.thickness_m > 0 && activeAlign?.d_strat_m != null
    ? Math.min(1, Math.max(0, activeAlign.d_strat_m / activeFormation.thickness_m))
    : null;

  const gridColsClass =
    columnIds.length >= 4 ? 'xl:grid-cols-5' : 'xl:grid-cols-4';

  return (
    <div className="p-4 space-y-4 max-w-[1900px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between flex-wrap gap-3 border-l-4 border-l-amber-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded text-amber-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              STRATIGRAPHIC CORRELATION & LOOKAHEAD CORRIDOR
              <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded">
                LIVE
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Eliminating the "Trajectory Trap" | Formation-relative TVD penetration (d_strat) | Top 3 DORS-ranked offset wells
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <Pin className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">PIN ADDITIONAL WELL:</span>
          <select
            value={pinnedOffsetId}
            onChange={(e) => setPinnedOffsetId(e.target.value)}
            className="bg-slate-900 border border-slate-700 px-2 py-1 rounded text-violet-300 font-bold focus:outline-none focus:border-violet-500"
          >
            <option value="">— none (auto top-3) —</option>
            {offsetCandidates.map((w) => (
              <option key={w.well_id} value={w.well_id}>
                {w.well_id}{topOffsetIds.includes(w.well_id) ? ' (already in top-3)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="scada-panel p-3 border-l-4 border-l-rose-500 text-xs font-mono text-rose-300">{error}</div>
      )}

      {/* Main Structural Cross-Section: Active Well vs Top-3 Offset Wells */}
      <div className="scada-panel p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="text-xs font-mono font-bold text-slate-200">
            STRATIGRAPHIC NORMALIZATION & HORIZON MAPPING
          </div>
          <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle className="w-3.5 h-3.5" />}
            {loading ? 'Loading…' : `${Object.keys(alignment).length} wells aligned (top ${topOffsetIds.length} shown by DORS rank${pinnedExtraId ? ' + 1 pinned' : ''})`}
          </div>
        </div>

        <div className={`grid grid-cols-1 md:grid-cols-2 ${gridColsClass} gap-4 items-stretch`}>
          {/* Active Well Column */}
          <div className="bg-slate-900/80 border border-cyan-500/30 p-4 rounded-lg space-y-3 relative flex flex-col">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-cyan-400 font-bold">ACTIVE WELL: {activeWellId}</span>
            </div>
            <div className="text-[11px] font-mono text-slate-300">Measured Depth: {depth.toFixed(1)} m</div>

            <div className="p-3 bg-slate-950/80 border border-slate-800 rounded space-y-1.5 font-mono text-xs">
              <div className="text-amber-400 font-bold text-sm">
                {activeFormation?.formation_name ?? activeAlign?.formation ?? '—'}
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Top Horizon (TVD):</span>
                <span className="text-slate-200 font-semibold">
                  {activeFormation ? activeFormation.top_tvd_m.toFixed(1) : '—'} m
                </span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Formation Thickness:</span>
                <span className="text-slate-200 font-semibold">
                  {activeFormation ? activeFormation.thickness_m.toFixed(1) : '—'} m
                </span>
              </div>
              <div className="flex justify-between text-slate-400 pt-1 border-t border-slate-800">
                <span>Bit TVDSS:</span>
                <span className="text-cyan-400 font-bold">
                  {activeAlign?.tvdss_m != null ? activeAlign.tvdss_m.toFixed(1) : '—'} m TVDSS
                </span>
              </div>
            </div>

            <div className="space-y-1 font-mono text-xs">
              <div className="flex justify-between text-slate-400 text-[10px]">
                <span>TOP (ξ = 0.0)</span>
                <span className="text-emerald-400 font-bold">
                  BIT POSITION: ξ = {activeXi != null ? activeXi.toFixed(3) : 'n/a'}
                </span>
                <span>BASE (ξ = 1.0)</span>
              </div>
              <div className="w-full bg-slate-950 h-8 rounded border border-slate-800 relative overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-600 via-yellow-500 to-amber-400"
                  style={{ width: `${activeXi != null ? Math.min(100, Math.max(0, activeXi * 100)) : 0}%` }}
                ></div>
                {activeXi != null && (
                  <div
                    className="absolute top-0 bottom-0 w-1 bg-cyan-400 shadow-md shadow-cyan-400"
                    style={{ left: `${Math.min(100, Math.max(0, activeXi * 100))}%` }}
                  ></div>
                )}
              </div>
              <div className="text-[10px] text-slate-500">
                ξ = d_strat_m (TVD penetration into formation) ÷ formation thickness_m — both measured values, not estimates.
              </div>
            </div>

            <div className="mt-auto pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-500">
              TRAJECTORY TRAP ELIMINATED: raw MD comparisons between wells of different trajectories would
              misrepresent true stratigraphic position. d_strat_m anchors every well below to the same geological bed.
            </div>
          </div>

          {/* Top-3 (+ optional pinned) Offset Well Columns */}
          {columnIds.length === 0 && !loading && (
            <div className="md:col-span-2 xl:col-span-3 flex items-center justify-center p-6 text-center text-slate-400 text-xs font-mono bg-slate-900/50 rounded border border-slate-800">
              No ranked offset wells available for this well.
            </div>
          )}
          {columnIds.map((wellId, idx) => {
            const isPinned = pinnedExtraId === wellId;
            const rankInfo = offsetRankings.find((r) => r.well_id === wellId);
            const align = alignment[wellId];
            const detail = offsetDetails[wellId];
            const offsetFormation = detail
              ? detail.formations.find((f) => f.formation_name === align?.formation) || detail.formations[0]
              : undefined;
            const correlatedEvents = (detail?.events ?? []).filter(
              (e) => !offsetFormation || e.formation === offsetFormation.formation_name,
            );
            const borderClass = isPinned ? 'border-violet-500/30' : 'border-amber-500/30';
            const labelClass = isPinned ? 'text-violet-300' : 'text-amber-400';

            return (
              <div key={wellId} className={`bg-slate-900/80 border ${borderClass} p-4 rounded-lg space-y-3 relative flex flex-col`}>
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-mono font-bold ${labelClass}`}>
                    {isPinned ? 'PINNED: ' : `#${rankInfo?.rank ?? idx + 1} OFFSET: `}{wellId}
                  </span>
                  {rankInfo && (
                    <span className="text-[10px] font-mono bg-slate-950 border border-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                      DORS {rankInfo.dors_score.toFixed(2)}
                    </span>
                  )}
                </div>
                {rankInfo && (
                  <div className="text-[10px] font-mono text-slate-500">
                    {rankInfo.distance_km.toFixed(1)} km offset · {rankInfo.events_in_lookahead} lookahead event(s)
                  </div>
                )}
                {!rankInfo && isPinned && (
                  <div className="text-[10px] font-mono text-slate-500">Outside DORS top-10 ranking for this depth/radius.</div>
                )}

                <div className="p-3 bg-slate-950/80 border border-slate-800 rounded space-y-1.5 font-mono text-xs">
                  <div className="text-amber-400 font-bold text-sm">
                    {align?.formation ?? offsetFormation?.formation_name ?? 'No matching formation'}
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Equivalent MD:</span>
                    <span className="text-slate-200 font-semibold">
                      {align?.md_m != null ? align.md_m.toFixed(1) : '—'} m
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Equivalent TVD:</span>
                    <span className="text-slate-200 font-semibold">
                      {align?.tvd_m != null ? align.tvd_m.toFixed(1) : '—'} m
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400 pt-1 border-t border-slate-800">
                    <span>Equivalent TVDSS:</span>
                    <span className="text-amber-400 font-bold">
                      {align?.tvdss_m != null ? align.tvdss_m.toFixed(1) : '—'} m TVDSS
                    </span>
                  </div>
                </div>

                <div className="flex-1 min-h-0">
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 mb-1">
                    <span>EVENTS AT THIS FORMATION</span>
                    <span className="text-rose-400">
                      {detailsLoading && !detail ? '…' : `${correlatedEvents.length} found`}
                    </span>
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                    {correlatedEvents.length > 0 ? (
                      correlatedEvents.map((evt) => (
                        <div key={evt.event_id} className="p-2 bg-slate-900 border border-slate-800 rounded text-[11px] font-mono space-y-0.5">
                          <div className="flex items-center justify-between">
                            <span className="text-rose-400 font-bold">{evt.event_type}</span>
                            <span className="text-[9px] bg-rose-500/20 text-rose-300 px-1 py-0.5 rounded">
                              {evt.severity}
                            </span>
                          </div>
                          <div className="text-slate-300 truncate" title={evt.raw_narrative || evt.outcome || ''}>
                            {evt.raw_narrative || evt.outcome || 'No narrative recorded'}
                          </div>
                          <div className="flex items-center justify-between text-[9px] text-slate-500">
                            <span>{evt.depth_start_md_m}m MD</span>
                            <span className="text-cyan-400">IADC {evt.iadc_npt_code || 'n/a'}</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="p-3 text-center text-slate-500 text-[10px] font-mono bg-slate-900/50 rounded">
                        {detailsLoading && !detail ? 'Loading events…' : 'No historical events logged at this formation.'}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Ahead-of-Bit Lookahead Risk Corridor — real data from /api/v2/corridors/{well_id} */}
      <div className="scada-panel p-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-cyan-400" />
            AHEAD-OF-BIT LOOKAHEAD RISK CORRIDORS ({activeWellId})
          </div>
          <div className="text-[11px] font-mono text-cyan-400">
            {corridors.length} corridor{corridors.length === 1 ? '' : 's'} ahead of {depth.toFixed(0)}m MD
          </div>
        </div>

        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
          {corridors.length === 0 && !loading && (
            <div className="md:col-span-3 p-4 text-center text-slate-400 text-xs font-mono bg-slate-900/50 rounded">
              No historical risk corridors identified ahead of the current bit depth for this well.
            </div>
          )}
          {corridors.map((c) => {
            const riskColor =
              c.risk_level === 'CRITICAL' ? 'border-rose-500/30 text-rose-400' :
              c.risk_level === 'HIGH' ? 'border-amber-500/30 text-amber-400' :
              c.risk_level === 'MODERATE' ? 'border-amber-500/20 text-amber-300' :
              'border-slate-800 text-emerald-400';
            return (
              <div key={c.corridor_id} className={`bg-slate-900/80 border p-3 rounded space-y-2 ${riskColor}`}>
                <div className="flex items-center justify-between text-xs font-mono font-bold">
                  <span>{c.hazard_type.replace(/_/g, ' ')}</span>
                  <span className="text-slate-400 text-[10px]">{c.depth_start_m.toFixed(0)}m - {c.depth_end_m.toFixed(0)}m</span>
                </div>
                <div className="text-[11px] font-mono text-slate-300">
                  Formation: <span className="text-amber-300 font-semibold">{c.formation ?? 'Unknown'}</span>
                </div>
                <div className="text-[11px] font-mono text-slate-400">
                  Proximity Risk: <span className="font-semibold">{c.risk_level}</span> · {c.event_count} historical event(s) · avg {c.avg_npt_hours.toFixed(1)}h NPT
                </div>
                {c.recommended_action && (
                  <div className="text-[11px] font-mono">{c.recommended_action}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
