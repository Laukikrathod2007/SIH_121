import React, { useState, useEffect } from 'react';
import {
  BookOpen,
  Search,
  Database,
  Sparkles,
  FileText,
} from 'lucide-react';
import { api } from '../services/api';
import { DrillingEvent, EventFacets } from '../types';
import { PdfEvidenceViewer } from '../components/PdfEvidenceViewer';

// Uses GET /api/v2/events/search (modules/02_nwis_backend/server.py) — a real
// free-text/semantic search over event narratives, with `search_mode` telling
// us honestly whether ranking was genuinely semantic (sentence-transformers
// loaded) or a keyword-match fallback. There is no LLM/RAG generation
// endpoint on our backend, so the "synthesized answer" panel below is
// explicitly labeled as a template built from the real top-ranked result,
// not an AI-generated summary — see the "Illustrative" badge.

export const HistoricalIntelligencePage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState<string>('Lost circulation in Barail Sandstone');
  const [selectedHazard, setSelectedHazard] = useState<string>('');
  const [selectedFormation, setSelectedFormation] = useState<string>('');
  const [minSeverity, setMinSeverity] = useState<string>('MEDIUM');
  const [results, setResults] = useState<{ relevance_score: number; event: DrillingEvent }[]>([]);
  const [facets, setFacets] = useState<EventFacets | null>(null);
  const [searchMode, setSearchMode] = useState<string>('');
  const [totalIndexed, setTotalIndexed] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [evidenceEvent, setEvidenceEvent] = useState<DrillingEvent | null>(null);

  const executeSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchEventsSemantic({
        query: searchQuery || '*',
        hazard_type: selectedHazard || undefined,
        formation: selectedFormation || undefined,
        min_severity: minSeverity || undefined,
        top_n: 20,
      });
      setResults(data.results);
      setFacets(data.facets);
      setSearchMode(data.search_mode);
      setTotalIndexed(data.total_candidates);
    } catch (err) {
      console.error('Failed to search events', err);
      setError('Could not reach the drilling knowledge search service. Contact your system administrator if this persists.');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    executeSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHazard, selectedFormation, minSeverity]);

  const topResult = results[0]?.event;

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              HISTORICAL DRILLING KNOWLEDGE SEARCH
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                LIVE
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Free-text / semantic search over drilling event narratives, mitigation &amp; outcome text
            </div>
          </div>
        </div>

        <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-cyan-400" />
          <span>{totalIndexed != null ? `${totalIndexed} Candidate Events Indexed` : 'Loading…'}</span>
        </div>
      </div>

      {error && (
        <div className="scada-panel p-3 border-l-4 border-l-rose-500 text-xs font-mono text-rose-300">{error}</div>
      )}

      {/* Natural Language Search Bar & Filters */}
      <div className="scada-panel p-4 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && executeSearch()}
              placeholder="Ask drilling knowledge base (e.g. 'lost circulation in Barail Sandstone')..."
              className="w-full bg-slate-900 border border-slate-700 pl-9 pr-4 py-2 rounded text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
          <button
            onClick={executeSearch}
            disabled={loading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-bold text-xs font-mono rounded transition flex items-center gap-1.5 shadow-md shadow-cyan-600/30"
          >
            {loading ? 'SEARCHING…' : 'SEARCH'}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs font-mono pt-1">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Hazard:</span>
            <select
              value={selectedHazard}
              onChange={(e) => setSelectedHazard(e.target.value)}
              className="bg-slate-900 border border-slate-700 px-2 py-1 rounded text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Hazards</option>
              <option value="MUD_LOSS">Mud Loss</option>
              <option value="KICK">Kick</option>
              <option value="STUCK_PIPE">Stuck Pipe</option>
              <option value="WELLBORE_INSTABILITY">Wellbore Instability</option>
              <option value="TORQUE_SPIKE">Torque Spike</option>
              <option value="CEMENTING_FAILURE">Cementing Failure</option>
              <option value="OVERPRESSURE_ZONE">Overpressure Zone</option>
              {/* Taxonomy support added per PS 26121 item (ix); the live
                  dataset has zero fishing-operation events (none in the
                  Equinor Volve pull this project's data is built from), so
                  selecting this honestly returns an empty result rather
                  than a fabricated example -- see AUDIT/11_REMEDIATION_REPORT.md
                  Priority 5. */}
              <option value="FISHING_OPERATION">Fishing Operation</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Formation:</span>
            <input
              type="text"
              value={selectedFormation}
              onChange={(e) => setSelectedFormation(e.target.value)}
              placeholder="Any"
              className="bg-slate-900 border border-slate-700 px-2 py-1 rounded text-slate-200 w-32 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Min Severity:</span>
            <select
              value={minSeverity}
              onChange={(e) => setMinSeverity(e.target.value)}
              className="bg-slate-900 border border-slate-700 px-2 py-1 rounded text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </div>

          {searchMode && (
            <span className="ml-auto text-[10px] text-slate-500">
              search_mode: <span className={searchMode === 'semantic' ? 'text-emerald-400' : 'text-amber-400'}>{searchMode}</span>
            </span>
          )}
        </div>
      </div>

      {/* Top-Result Summary — explicitly labeled, NOT an AI-generated synthesis */}
      {topResult && (
        <div className="scada-panel p-4 border-l-4 border-l-cyan-400 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-wider">
                Top-Ranked Match
              </span>
            </div>
            <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded">
              Illustrative summary — not an AI-generated synthesis
            </span>
          </div>

          <div className="text-sm text-slate-200 leading-relaxed font-sans bg-slate-900/60 p-3 rounded border border-slate-800">
            Highest-relevance match ({(results[0].relevance_score * 100).toFixed(1)}% score) for "{searchQuery}":{' '}
            <strong>{topResult.event_type}</strong> at {topResult.depth_start_md_m}m MD in{' '}
            <strong>{topResult.formation ?? 'an unrecorded formation'}</strong> on well {topResult.well_id}, logging{' '}
            {topResult.npt_hours.toFixed(1)}h NPT. {topResult.mitigation_description
              ? `Mitigation on record: ${topResult.mitigation_description}`
              : 'No mitigation description on record for this event.'}
          </div>

          {facets && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <div className="p-2 bg-slate-900/90 border border-slate-800 rounded text-xs font-mono text-cyan-200">
                Hazard breakdown: {Object.entries(facets.hazard_type).map(([k, v]) => `${k} (${v})`).join(', ') || 'none'}
              </div>
              <div className="p-2 bg-slate-900/90 border border-slate-800 rounded text-xs font-mono text-cyan-200">
                Formations: {Object.entries(facets.formation).map(([k, v]) => `${k} (${v})`).join(', ') || 'none'}
              </div>
              <div className="p-2 bg-slate-900/90 border border-slate-800 rounded text-xs font-mono text-cyan-200">
                Severity: {Object.entries(facets.severity).map(([k, v]) => `${k} (${v})`).join(', ') || 'none'}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Supporting Evidence Records */}
      <div className="scada-panel p-4 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
            SEARCH RESULTS
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            {results.length} Events Returned
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {results.map(({ event: evt, relevance_score }) => (
            <div
              key={evt.event_id}
              className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-2 hover:border-slate-700 transition font-mono text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="text-rose-400 font-bold">{evt.event_type}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                    evt.severity === 'CRITICAL'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : evt.severity === 'HIGH'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'bg-slate-800 text-slate-300'
                  }`}
                >
                  {evt.severity}
                </span>
              </div>

              <div className="text-slate-200 text-xs font-sans leading-relaxed">{evt.raw_narrative || evt.outcome || 'No narrative recorded'}</div>

              <div className="grid grid-cols-2 gap-1 text-[11px] text-slate-400 pt-1 border-t border-slate-800/80">
                <div>Well: <span className="text-slate-200 font-semibold">{evt.well_id}</span></div>
                <div>Formation: <span className="text-amber-300">{evt.formation ?? '—'}</span></div>
                <div>Depth: <span className="text-slate-200">{evt.depth_start_md_m}m MD</span></div>
                <div>IADC Code: <span className="text-cyan-400 font-bold">{evt.iadc_npt_code || 'n/a'}</span></div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                <span>Relevance: <strong className="text-emerald-400">{(relevance_score * 100).toFixed(1)}%</strong></span>
                {evt.source_document ? (
                  <button
                    onClick={() => setEvidenceEvent(evt)}
                    className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 hover:underline"
                  >
                    <FileText className="w-3 h-3" /> View Source: {evt.source_document}
                  </button>
                ) : (
                  <span className="text-slate-400">No source document on record</span>
                )}
              </div>
            </div>
          ))}
          {results.length === 0 && !loading && (
            <div className="col-span-2 p-4 text-center text-slate-400 text-xs font-mono bg-slate-900/50 rounded">
              No events matched this query/filter combination.
            </div>
          )}
        </div>
      </div>

      {evidenceEvent && (
        <PdfEvidenceViewer
          onClose={() => setEvidenceEvent(null)}
          sourceFilename={evidenceEvent.source_document || undefined}
          page={evidenceEvent.source_page ?? 1}
          contextLabel={`${evidenceEvent.event_type} — ${evidenceEvent.well_id} — event ${evidenceEvent.event_id}`}
        />
      )}
    </div>
  );
};
