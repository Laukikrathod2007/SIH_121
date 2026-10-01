import React, { useState } from 'react';
import { Bot, Search, ShieldCheck, AlertTriangle, Loader2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { DrillingEvent, FormationTop, OffsetWellRanking, RiskCorridor } from '../types';

// A GROUNDED RETRIEVAL ASSISTANT, not a chatbot. There is no LLM API
// configured anywhere in this project (a deliberate choice — see
// modules/02_nwis_backend/search/knowledge_search.py and
// HistoricalIntelligencePage.tsx's "Illustrative summary — not an
// AI-generated synthesis" labeling). This page does simple keyword/entity
// matching against REAL known wells/hazards/formations, then calls the same
// real module 02 endpoints every other page uses
// (searchEventsSemantic / getOffsetRank / getRiskCorridors). The "summary"
// text below is a template filled from actual returned fields — every
// number and name in it traces to a real record shown underneath it. No
// answer is ever generated from a model; if nothing matches, it says so.

const HAZARD_KEYWORDS: Record<string, string> = {
  'lost circulation': 'MUD_LOSS',
  'mud loss': 'MUD_LOSS',
  'fluid loss': 'MUD_LOSS',
  'stuck pipe': 'STUCK_PIPE',
  'differential sticking': 'STUCK_PIPE',
  kick: 'KICK',
  overpressure: 'KICK',
  influx: 'KICK',
  'wellbore instability': 'WELLBORE_INSTABILITY',
  'hole collapse': 'WELLBORE_INSTABILITY',
  torque: 'TORQUE_SPIKE',
  'stick-slip': 'TORQUE_SPIKE',
  cementing: 'CEMENTING_FAILURE',
  cement: 'CEMENTING_FAILURE',
};

interface CopilotResult {
  summary: string;
  events: { relevance_score: number; event: DrillingEvent }[];
  searchMode: string;
  matchedWellId: string | null;
  offsetRankings: OffsetWellRanking[] | null;
  corridors: RiskCorridor[] | null;
  noMatch: boolean;
}

export const CopilotPage: React.FC = () => {
  const { wells, activeDepth } = useApp();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CopilotResult | null>(null);
  const [formationsCache, setFormationsCache] = useState<FormationTop[] | null>(null);

  const runQuery = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const qLower = q.toLowerCase();
      const qUpper = q.toUpperCase();

      let hazardType: string | undefined;
      for (const [phrase, code] of Object.entries(HAZARD_KEYWORDS)) {
        if (qLower.includes(phrase)) { hazardType = code; break; }
      }

      const matchedWell = wells.find(
        (w) => qUpper.includes(w.well_id) || qLower.includes(w.well_name.toLowerCase())
      );

      let formations = formationsCache;
      if (!formations) {
        try {
          formations = await api.getAllFormations();
          setFormationsCache(formations);
        } catch {
          formations = [];
        }
      }
      const matchedFormation = formations?.find((f) =>
        qLower.includes(f.formation_name.toLowerCase())
      );

      const depthMatch = q.match(/(\d{3,5})\s*m\b/);
      const depth = depthMatch ? Number(depthMatch[1]) : (matchedWell ? activeDepth : undefined);

      const searchRes = await api.searchEventsSemantic({
        query: q,
        hazard_type: hazardType,
        formation: matchedFormation?.formation_name,
        top_n: 8,
      });

      let offsetRankings: OffsetWellRanking[] | null = null;
      let corridors: RiskCorridor[] | null = null;
      if (matchedWell) {
        const [rankRes, corrRes] = await Promise.allSettled([
          api.getOffsetRank(matchedWell.well_id, depth ?? 2450),
          api.getRiskCorridors(matchedWell.well_id, depth ?? 2450, hazardType),
        ]);
        if (rankRes.status === 'fulfilled') offsetRankings = rankRes.value.rankings;
        if (corrRes.status === 'fulfilled') corridors = corrRes.value.corridors;
      }

      const top = searchRes.results[0];
      const parts: string[] = [];
      if (searchRes.total_returned > 0) {
        parts.push(
          `Found ${searchRes.total_returned} historical event(s) matching "${q}" ` +
          `(${searchRes.search_mode === 'semantic' ? 'semantic search' : 'keyword fallback'} over ${searchRes.total_candidates} candidates).`
        );
        if (top) {
          parts.push(
            `Top match: ${top.event.event_type.replace(/_/g, ' ')} at ${top.event.well_id}, ` +
            `${top.event.depth_start_md_m}m MD in ${top.event.formation ?? 'an unrecorded formation'} — ` +
            `${top.event.npt_hours.toFixed(1)}h NPT. ` +
            (top.event.mitigation_description
              ? `Mitigation on record: ${top.event.mitigation_description}`
              : 'No mitigation description on record for this event.')
          );
        }
      }
      if (matchedWell && offsetRankings && offsetRankings.length > 0) {
        const r0 = offsetRankings[0];
        parts.push(
          `For ${matchedWell.well_id}: highest-ranked offset well is ${r0.well_id} ` +
          `(DORS ${(r0.dors_score * 100).toFixed(1)}%, ${r0.distance_km.toFixed(1)}km away, formation match: ${r0.formation_match}).`
        );
      }
      if (corridors && corridors.length > 0) {
        const worst = [...corridors].sort((a, b) => {
          const rank = { LOW: 0, MODERATE: 1, HIGH: 2, CRITICAL: 3 } as const;
          return (rank[b.risk_level] ?? 0) - (rank[a.risk_level] ?? 0);
        })[0];
        parts.push(
          `${corridors.length} historical risk corridor(s) ahead of the current bit depth for ${matchedWell?.well_id} — ` +
          `highest proximity risk: ${worst.risk_level} (${worst.hazard_type.replace(/_/g, ' ')}, ${worst.event_count} historical event(s)).`
        );
      }

      const noMatch = searchRes.total_returned === 0 && !offsetRankings && !corridors;
      setResult({
        summary: noMatch ? '' : parts.join(' '),
        events: searchRes.results,
        searchMode: searchRes.search_mode,
        matchedWellId: matchedWell?.well_id ?? null,
        offsetRankings,
        corridors,
        noMatch,
      });
    } catch (err) {
      console.error('Copilot query failed', err);
      setError('Failed to reach the NWIS backend (module 02) to answer this query.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-[1200px] mx-auto">
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100">DRILLING KNOWLEDGE COPILOT</div>
            <div className="text-xs text-slate-400 font-mono">
              Ask about offset wells, formations, hazard types, or past incidents in plain language
            </div>
          </div>
        </div>
        <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-1 rounded flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5" /> Grounded retrieval — every result links to a real record, not AI-generated
        </span>
      </div>

      <div className="scada-panel p-4 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && runQuery()}
              placeholder='e.g. "lost circulation near WELL-NHK-001 below 2500m" or "stuck pipe in Barail Sandstone"'
              className="w-full bg-slate-900 border border-slate-700 pl-9 pr-4 py-2 rounded text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
          <button
            onClick={runQuery}
            disabled={loading || !query.trim()}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-bold text-xs font-mono rounded transition flex items-center gap-1.5"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
            {loading ? 'SEARCHING…' : 'ASK'}
          </button>
        </div>
      </div>

      {error && (
        <div className="scada-panel p-3 border-l-4 border-l-rose-500 text-xs font-mono text-rose-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {result?.noMatch && (
        <div className="scada-panel p-4 text-xs font-mono text-slate-400 text-center">
          No matching records found for this query — nothing fabricated in its place.
        </div>
      )}

      {result && !result.noMatch && (
        <>
          <div className="scada-panel p-4 border-l-4 border-l-cyan-400">
            <div className="text-sm text-slate-200 leading-relaxed font-sans">{result.summary}</div>
          </div>

          {result.events.length > 0 && (
            <div className="scada-panel p-4 space-y-3">
              <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800">
                SUPPORTING EVIDENCE ({result.events.length} record{result.events.length === 1 ? '' : 's'})
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.events.map(({ event: evt, relevance_score }) => (
                  <div key={evt.event_id} className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1.5 font-mono text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-rose-400 font-bold">{evt.event_type.replace(/_/g, ' ')}</span>
                      <span className="text-emerald-400">{(relevance_score * 100).toFixed(1)}% relevance</span>
                    </div>
                    <div className="text-slate-200 text-[11px] font-sans">{evt.raw_narrative || evt.outcome || 'No narrative recorded'}</div>
                    <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-400 pt-1 border-t border-slate-800/80">
                      <div>Well: <span className="text-slate-200">{evt.well_id}</span></div>
                      <div>Depth: <span className="text-slate-200">{evt.depth_start_md_m}m MD</span></div>
                      <div>Source: <span className="text-slate-300">{evt.source_document || 'n/a'}</span></div>
                      <div>event_id: <span className="text-slate-300">{evt.event_id}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
