import React, { useEffect, useRef, useState } from 'react';
import { ArrowUp, Search } from 'lucide-react';
import { api, type AskResponse, type AskSource } from '../lib/api';
import { hazardOf, m, n, shortWell } from '../lib/format';
import { useNwis } from '../state/nwis';
import { ErrorNote, HazardChip, Loading, PageHeader, Panel, PanelHead, SeverityTag, SourceLink, cx } from '../ui/primitives';

const EXAMPLES = [
  'How were mud losses handled in nearby wells?',
  'What happened in the Kopili in offset wells?',
  'Stuck pipe in Girujan Clay — what worked?',
  'Show kicks near 2800 m',
  'Torque spikes in Barail coal',
  'Cementing problems and the remedial jobs',
];

type Turn = { q: string; r?: AskResponse; error?: string };

export const AskView: React.FC = () => {
  const { activeWellId, activeWell, bitDepth } = useNwis();
  const [q, setQ] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [focusRef, setFocusRef] = useState<{ turn: number; ref: number } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [turns]);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || busy) return;
    setQ('');
    setBusy(true);
    setTurns((t) => [...t, { q: text }]);
    try {
      const r = await api.ask({ question: text, well_id: activeWellId, depth_m: bitDepth ?? undefined, radius_km: 25 });
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, r } : x)));
    } catch (e: any) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: e.message } : x)));
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="px-6 py-6 max-w-[1180px]">
      <PageHeader
        eyebrow="Knowledge repository"
        title="Ask the archive"
        lead={<>Ask in plain words. NWIS searches every recorded incident, mitigation and outcome from past reports, and answers <b className="font-medium text-ink">only</b> from those records. Every sentence points to the report it came from. “Nearby” means within 25 km of {activeWell?.well_name ?? 'the active well'}.</>}
      />

      {turns.length === 0 && (
        <Panel className="mb-5">
          <div className="p-4">
            <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2.5">Try one of these</div>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => ask(e)} className="text-[13px] px-3 py-1.5 rounded-full border border-line bg-surface hover:border-accent hover:text-accent transition-colors">{e}</button>
              ))}
            </div>
          </div>
        </Panel>
      )}

      <div className="space-y-6 pb-40">
        {turns.map((t, ti) => (
          <div key={ti} className="animate-fade-up">
            <div className="flex justify-end mb-3">
              <div className="max-w-[70%] bg-ink text-white text-[13.5px] rounded-2xl rounded-br-md px-4 py-2.5">{t.q}</div>
            </div>
            {!t.r && !t.error && <Loading label="Searching the archive" />}
            {t.error && <ErrorNote message={t.error} />}
            {t.r && <Answer r={t.r} focus={focusRef?.turn === ti ? focusRef.ref : null} onFocus={(ref) => setFocusRef(ref === null ? null : { turn: ti, ref })} />}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <div className="fixed bottom-0 left-[232px] right-0 bg-gradient-to-t from-paper via-paper to-transparent pt-8 pb-5 px-6">
        <form className="max-w-[1180px]" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
          <div className="flex items-end gap-2 bg-surface border border-line-strong rounded-2xl shadow-pop p-2 pl-4 focus-within:border-accent">
            <Search className="w-4 h-4 text-ink-3 mb-2.5" />
            <textarea
              ref={inputRef}
              rows={1}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(q); } }}
              placeholder="e.g. What did nearby wells do about losses in the Sylhet Limestone?"
              className="flex-1 resize-none outline-none focus-visible:outline-none text-[14px] py-2 bg-transparent placeholder:text-ink-3"
              aria-label="Question"
            />
            <button type="submit" disabled={!q.trim() || busy} aria-label="Ask" className="w-9 h-9 rounded-xl bg-accent text-white flex items-center justify-center disabled:opacity-40">
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const CONF: Record<string, { label: string; color: string }> = {
  HIGH: { label: 'Well supported', color: 'var(--sev-low)' },
  MEDIUM: { label: 'Partly supported', color: 'var(--sev-medium)' },
  LOW: { label: 'Weak support', color: 'var(--sev-high)' },
  NONE: { label: 'No records found', color: 'var(--ink-3)' },
};

const Answer: React.FC<{ r: AskResponse; focus: number | null; onFocus: (ref: number | null) => void }> = ({ r, focus, onFocus }) => {
  const it = r.interpreted;
  const chips = [
    ...it.hazards.map((h) => hazardOf(h).label),
    it.formation && `in ${it.formation}`,
    it.depth_m !== null && `around ${m(it.depth_m)}`,
    it.well_id && `well ${shortWell(it.well_id)}`,
    it.nearby_of && `within 25 km of ${shortWell(it.nearby_of)}`,
  ].filter(Boolean) as string[];
  const conf = CONF[r.confidence.level];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
      <Panel>
        <div className="px-4 pt-3.5 pb-2 flex flex-wrap items-center gap-2 border-b border-line">
          <span className="text-2xs uppercase tracking-[0.08em] text-ink-3">Understood as</span>
          {chips.length ? chips.map((c) => <span key={c} className="text-[11px] px-2 py-0.5 rounded-full bg-sunken text-ink-2">{c}</span>) : <span className="text-[11px] text-ink-3">free-text search over all records</span>}
          <span className="ml-auto text-[11px] font-medium" style={{ color: conf.color }} title={r.confidence.reason}>{conf.label}</span>
        </div>
        <div className="p-4 space-y-2.5">
          {r.statements.length === 0 && <p className="text-[14px] text-ink-2">{r.answer}</p>}
          {r.statements.map((s, i) => (
            <p key={i} className={cx('text-[14px] leading-relaxed', i === 0 ? 'text-ink' : 'text-ink-2')}>
              {s.text}{' '}
              {s.refs.slice(0, 6).map((ref) => (
                <button key={ref} onMouseEnter={() => onFocus(ref)} onMouseLeave={() => onFocus(null)} onClick={() => document.getElementById(`src-${r.question}-${ref}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })}
                  className={cx('num text-[10.5px] align-super px-1 mx-0.5 rounded border', focus === ref ? 'bg-accent text-white border-accent' : 'border-line text-accent hover:border-accent')}>
                  {ref}
                </button>
              ))}
            </p>
          ))}
          <p className="text-[11px] text-ink-3 pt-1">{r.confidence.reason}. Ranking: {r.search_mode === 'semantic' ? 'meaning-based (sentence embeddings)' : 'keyword match'}.</p>
        </div>
      </Panel>
      <Panel className="self-start">
        <PanelHead title={`Sources (${r.sources.length})`} hint="Hover a number in the answer to find its record." />
        <ul className="divide-y divide-line max-h-[520px] overflow-y-auto">
          {r.sources.map((s) => <SourceCard key={s.ref} s={s} active={focus === s.ref} id={`src-${r.question}-${s.ref}`} onHover={onFocus} />)}
        </ul>
      </Panel>
    </div>
  );
};

const SourceCard: React.FC<{ s: AskSource; active: boolean; id: string; onHover: (ref: number | null) => void }> = ({ s, active, id, onHover }) => (
  <li id={id} onMouseEnter={() => onHover(s.ref)} onMouseLeave={() => onHover(null)} className={cx('px-4 py-3 transition-colors', active && 'bg-accent-soft')}>
    <div className="flex items-center gap-2">
      <span className="num text-[11px] w-5 h-5 rounded border border-line flex items-center justify-center text-accent">{s.ref}</span>
      <span className="num text-[13px] font-medium">{s.well_name}</span>
      <span className="num text-[11px] text-ink-3">{s.depth_m !== null ? m(s.depth_m) : 'depth not stated'}</span>
      <span className="ml-auto"><SeverityTag severity={s.severity} /></span>
    </div>
    <div className="flex items-center gap-2 mt-1.5"><HazardChip hazard={s.event_type} />{s.formation && <span className="text-[11px] text-ink-3">{s.formation}</span>}</div>
    <p className="text-xs text-ink-2 mt-1.5 leading-snug line-clamp-3">{s.narrative}</p>
    {s.npt_hours ? <p className="text-[11px] text-ink-3 mt-1">{n(s.npt_hours, 1)} h lost</p> : null}
    <div className="mt-1.5"><SourceLink doc={s.source_document} page={s.source_page} /></div>
  </li>
);
