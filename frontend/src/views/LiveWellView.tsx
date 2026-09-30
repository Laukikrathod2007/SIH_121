import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Pause, Play, RotateCcw } from 'lucide-react';
import { api, type Alert, type WellProfile } from '../lib/api';
import { hazardOf, km, m, n, sevOf, shortWell } from '../lib/format';
import { useLoad, useNwis } from '../state/nwis';
import { Button, Empty, ErrorNote, HazardChip, Loading, PageHeader, Panel, PanelHead, SeverityTag, SourceLink, cx } from '../ui/primitives';

type Corridor = {
  corridor_id: string;
  hazard_type: string;
  depth_start_m: number;
  depth_end_m: number;
  contributing_wells: string[];
  event_count: number;
  avg_npt_hours: number;
  max_severity: string;
  lead_distance_m: number | null;
};
type Assessment = {
  hazard_type: string;
  risk_level: string;
  composite_score: number;
  p_history: number;
  a_sensor: number;
  m_ml: number;
  m_ml_source: string;
  lead_time_meters: number | null;
  recommended_action: string;
  active_corridor: Corridor | null;
};
type Analysis = {
  current_depth_m: number;
  formation_at_bit: string | null;
  overall_risk_level: string;
  alert_message: string | null;
  hazard_assessments: Assessment[];
  active_risk_corridors: Corridor[];
  offset_rankings: { well_id: string; well_name: string; distance_km: number; dors_score: number; formation_match: string; events_in_lookahead: number; structural_status: string }[];
};

const FORMATION_TONES = ['#efe9dc', '#e6ecde', '#e9e3ee', '#dfe8ec', '#f1e6dd', '#e3e9e4', '#ece6e0', '#e1e6ef', '#efe4e4'];

export const LiveWellView: React.FC = () => {
  const { activeWell, activeWellId, replay, startReplay, stopReplay, alerts } = useNwis();
  const profile = useLoad<WellProfile | null>(() => (activeWellId ? api.profile(activeWellId) : Promise.resolve(null)), [activeWellId]);
  const td = activeWell?.total_depth_md_m ?? 3000;
  const [scrub, setScrub] = useState<number>(0);
  useEffect(() => { if (activeWell) setScrub(Math.round(activeWell.total_depth_md_m * 0.85)); }, [activeWell?.well_id]);

  const live = replay.status === 'running' || replay.status === 'finished';
  const depth = live && replay.tick ? replay.tick.depth_m : scrub;
  const analysisDepth = useThrottled(depth, live ? 900 : 250);
  const analysis = useLoad<Analysis | null>(() => (activeWellId && analysisDepth ? api.analyze(activeWellId, analysisDepth) : Promise.resolve(null)), [activeWellId, analysisDepth]);
  const a = analysis.data;

  const wellAlerts = alerts.filter((x) => x.well_id === activeWellId && x.status === 'ACTIVE');
  const ahead = useMemo(
    () => (a?.active_risk_corridors ?? []).filter((c) => c.lead_distance_m !== null && c.depth_end_m >= depth).sort((x, y) => (x.lead_distance_m ?? 0) - (y.lead_distance_m ?? 0)),
    [a, depth],
  );
  const next = ahead[0];

  if (!activeWell) return <Loading label="Loading active well" />;

  return (
    <div className="px-6 py-6 max-w-[1440px]">
      <PageHeader
        eyebrow={`${activeWell.field} field · ${activeWell.well_type} · ${activeWell.status.toLowerCase()}`}
        title={`${activeWell.well_name}: what is ahead of the bit`}
        lead={
          <>NWIS compares the active well with offset wells drilled through the same formations, and warns before the bit reaches a depth where they had trouble. The live stream replays this well as eRTMAC would feed it.</>
        }
        right={
          replay.status === 'running' ? (
            <Button onClick={stopReplay} icon={<Pause className="w-4 h-4" />}>Pause stream</Button>
          ) : (
            <>
              {replay.status === 'finished' && <Button variant="ghost" onClick={() => startReplay()} icon={<RotateCcw className="w-4 h-4" />}>Replay again</Button>}
              <Button variant="primary" onClick={() => startReplay({ start: Math.round(depth), end: td })} icon={<Play className="w-4 h-4" />}>
                {replay.status === 'idle' ? `Start live stream from ${m(depth)}` : 'Resume stream'}
              </Button>
            </>
          )
        }
      />

      {/* Headline sentence: the one thing an engineer needs */}
      <Panel className="mb-5 overflow-hidden">
        <div className="grid grid-cols-[1fr_auto] gap-6 p-5 items-center">
          <div>
            <div className="text-2xs uppercase tracking-[0.1em] text-ink-3 mb-1.5">{live ? 'Live' : 'Planning view'} · bit at {m(depth)} in {a?.formation_at_bit ?? '…'}</div>
            {next ? (
              <p className="text-[19px] leading-7 text-ink max-w-3xl">
                {next.lead_distance_m! > 0 ? (
                  <><span className="num font-medium" style={{ color: sevOf(next.max_severity).color }}>{m(next.lead_distance_m)}</span> to a{' '}</>
                ) : (
                  <>The bit is inside a{' '}</>
                )}
                <span className="font-medium" style={{ color: hazardOf(next.hazard_type).color }}>{hazardOf(next.hazard_type).label.toLowerCase()}</span> zone
                ({m(next.depth_start_m)}–{m(next.depth_end_m)}) seen in{' '}
                <span className="font-medium">{next.contributing_wells.map(shortWell).join(', ')}</span>, costing on average{' '}
                <span className="num">{n(next.avg_npt_hours, 0)} h</span> of lost time.
              </p>
            ) : (
              <p className="text-[19px] leading-7 text-ink">No historical trouble zone from nearby wells lies ahead within the look-ahead window.</p>
            )}
            {a?.alert_message && <p className="text-[13px] text-ink-2 mt-2">{a.alert_message}</p>}
          </div>
          <div className="text-right">
            <div className="text-2xs uppercase tracking-[0.1em] text-ink-3">Overall risk</div>
            <div className="text-[28px] font-semibold tracking-tight" style={{ color: sevOf(a?.overall_risk_level).color }}>{a ? sevOf(a.overall_risk_level).label : '—'}</div>
          </div>
        </div>
        {!live && (
          <div className="border-t border-line px-5 py-3 flex items-center gap-4 bg-sunken/50">
            <span className="text-xs text-ink-2 whitespace-nowrap">Explore a bit depth</span>
            <input type="range" min={Math.round(td * 0.3)} max={td} step={5} value={scrub} onChange={(e) => setScrub(Number(e.target.value))} className="flex-1" aria-label="Bit depth" />
            <span className="num text-[13px] w-20 text-right">{m(scrub)}</span>
          </div>
        )}
        {live && (
          <div className="h-1 bg-sunken">
            <div className="h-full bg-accent transition-all duration-700" style={{ width: `${Math.min(100, ((depth - replay.startDepth) / Math.max(1, replay.endDepth - replay.startDepth)) * 100)}%` }} />
          </div>
        )}
      </Panel>

      {analysis.error && <ErrorNote message={analysis.error} onRetry={analysis.reload} />}

      <div className="grid grid-cols-1 xl:grid-cols-[440px_1fr] gap-5">
        <Panel>
          <PanelHead title="Depth column" hint="Formations of this well, its casing shoes, and trouble zones from nearby wells." />
          {profile.data ? (
            <DepthColumn profile={profile.data} corridors={a?.active_risk_corridors ?? []} depth={depth} td={td} />
          ) : profile.error ? <ErrorNote message={profile.error} /> : <Loading />}
        </Panel>

        <div className="flex flex-col gap-5 min-w-0">
          <Panel>
            <PanelHead
              title="Risk by hazard at this depth"
              hint="Each score blends three signals: what nearby wells experienced here, live sensor behaviour, and the hazard model."
              right={<span className="text-[11px] text-ink-3">hover a row for the breakdown</span>}
            />
            <div className="p-4 space-y-2.5">
              {!a && <Loading />}
              {a?.hazard_assessments
                .slice()
                .sort((x, y) => y.composite_score - x.composite_score)
                .map((h) => <RiskRow key={h.hazard_type} h={h} />)}
            </div>
          </Panel>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Panel>
              <PanelHead title="Active alerts for this well" right={<Link to="/alerts" className="text-xs text-accent hover:underline">All alerts →</Link>} />
              {wellAlerts.length === 0 ? (
                <Empty title="No active alerts" body={live ? 'Alerts appear here as the bit approaches a historical trouble zone.' : 'Start the live stream to let NWIS raise alerts as the bit advances.'} />
              ) : (
                <ul className="divide-y divide-line">
                  {wellAlerts.slice(0, 4).map((al) => <AlertLine key={al.alert_id} a={al} />)}
                </ul>
              )}
            </Panel>
            <Panel>
              <PanelHead title="Most relevant offset wells" hint="Ranked by distance, same formation, depth reached, well path shape and incident history." />
              <ul className="divide-y divide-line">
                {(a?.offset_rankings ?? []).slice(0, 5).map((r) => (
                  <li key={r.well_id}>
                    <Link to={`/wells/${r.well_id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-sunken/60">
                      <span className="num text-[13px] font-medium w-20">{r.well_name}</span>
                      <span className="flex-1 min-w-0">
                        <span className="block h-1.5 rounded-full bg-sunken overflow-hidden"><span className="block h-full bg-accent" style={{ width: `${Math.round(r.dors_score * 100)}%` }} /></span>
                        <span className="block text-[11px] text-ink-3 mt-1 truncate">
                          {km(r.distance_km)} · {r.formation_match !== 'N/A' ? `has ${r.formation_match}` : 'formation not matched'}
                          {r.structural_status === 'POSSIBLE_FAULT_BOUNDARY' ? ' · possible fault between wells' : ''}
                        </span>
                      </span>
                      <span className="num text-xs text-ink-2 w-10 text-right">{Math.round(r.dors_score * 100)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
};

const RiskRow: React.FC<{ h: Assessment }> = ({ h }) => {
  const hz = hazardOf(h.hazard_type);
  const s = sevOf(h.risk_level);
  return (
    <div className="group relative grid grid-cols-[170px_1fr_64px] items-center gap-3">
      <span className="text-[13px] text-ink flex items-center gap-2"><span className="w-2 h-2 rounded-full" style={{ background: hz.color }} />{hz.label}</span>
      <span className="h-2 rounded-full bg-sunken overflow-hidden"><span className="block h-full rounded-full transition-all duration-500" style={{ width: `${Math.round(h.composite_score * 100)}%`, background: s.color }} /></span>
      <span className="text-[11px] font-semibold uppercase tracking-[0.05em] text-right" style={{ color: s.color }}>{s.label}</span>
      <div className="pointer-events-none absolute z-10 left-[180px] top-6 hidden group-hover:block w-[320px] bg-ink text-white text-xs rounded-lg p-3 shadow-pop">
        <div className="font-medium mb-1.5">{hz.label}: score {h.composite_score.toFixed(2)}</div>
        <Breakdown label="Nearby-well history" v={h.p_history} />
        <Breakdown label="Live sensor anomaly" v={h.a_sensor} />
        <Breakdown label={h.m_ml_source === 'trained_model' ? 'Trained hazard model' : 'Rule-based estimate (too few examples to train)'} v={h.m_ml} />
        {h.recommended_action && <div className="mt-2 text-white/80 leading-snug">{h.recommended_action}</div>}
      </div>
    </div>
  );
};

const Breakdown: React.FC<{ label: string; v: number }> = ({ label, v }) => (
  <div className="flex items-center gap-2 mt-1">
    <span className="flex-1 text-white/75">{label}</span>
    <span className="w-20 h-1 rounded bg-white/20 overflow-hidden"><span className="block h-full bg-white" style={{ width: `${Math.round(v * 100)}%` }} /></span>
    <span className="num w-8 text-right">{v.toFixed(2)}</span>
  </div>
);

const AlertLine: React.FC<{ a: Alert }> = ({ a }) => (
  <li className="px-4 py-3">
    <div className="flex items-center justify-between gap-2">
      <SeverityTag severity={a.severity} />
      <span className="num text-[11px] text-ink-3">at {m(a.depth_m)}</span>
    </div>
    <div className="text-[13px] font-medium mt-1">{a.title}</div>
    <div className="text-xs text-ink-2 mt-0.5 leading-snug">{a.message}</div>
    {a.evidence[0] && <div className="mt-1.5"><SourceLink doc={a.evidence[0].source_document} page={a.evidence[0].source_page} /></div>}
  </li>
);

/** Vertical depth column: formations (left), casing shoes, offset-well trouble zones (right), and the bit. */
const DepthColumn: React.FC<{ profile: WellProfile; corridors: Corridor[]; depth: number; td: number }> = ({ profile, corridors, depth, td }) => {
  const H = 640, top = 16, bottom = 16, W = 406;
  const y = (d: number) => top + (d / td) * (H - top - bottom);
  const fms = profile.formations.slice().sort((a, b) => a.top_md_m - b.top_md_m);
  const [hover, setHover] = useState<Corridor | null>(null);

  // Lay corridors into lanes so overlapping zones don't hide each other.
  const lanes: Corridor[][] = [];
  corridors.slice().sort((a, b) => a.depth_start_m - b.depth_start_m).forEach((c) => {
    const lane = lanes.find((l) => l[l.length - 1].depth_end_m < c.depth_start_m - 5);
    lane ? lane.push(c) : lanes.push([c]);
  });

  return (
    <div className="relative px-3 py-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Depth column">
        {/* depth ticks */}
        {Array.from({ length: Math.floor(td / 250) + 1 }, (_, i) => i * 250).map((d) => (
          <g key={d}>
            <line x1={44} x2={W} y1={y(d)} y2={y(d)} stroke="var(--line)" strokeWidth={d % 1000 === 0 ? 1 : 0.5} />
            <text x={38} y={y(d) + 3.5} textAnchor="end" className="num" fontSize={10} fill="var(--ink-3)">{d}</text>
          </g>
        ))}
        {/* formations */}
        {fms.map((f, i) => {
          const y0 = y(f.top_md_m);
          const y1 = y(i < fms.length - 1 ? Math.min(fms[i + 1].top_md_m, f.base_md_m ?? td) : f.base_md_m ?? td);
          return (
            <g key={f.formation_name}>
              <rect x={48} y={y0} width={132} height={Math.max(1, y1 - y0)} fill={FORMATION_TONES[i % FORMATION_TONES.length]} stroke="#fff" />
              {y1 - y0 > 13 && <text x={56} y={y0 + 13} fontSize={10.5} fill="var(--ink-2)">{f.formation_name}</text>}
            </g>
          );
        })}
        {/* casing shoes */}
        {profile.casing_program.map((c) => (
          <g key={c.casing_size}>
            <path d={`M180 ${y(c.shoe_md_m) - 6} L188 ${y(c.shoe_md_m)} L180 ${y(c.shoe_md_m)} Z`} fill="var(--ink)" />
            <text x={192} y={y(c.shoe_md_m) + 3.5} fontSize={9.5} className="num" fill="var(--ink-2)">{c.casing_size}</text>
          </g>
        ))}
        {/* corridor lanes */}
        {lanes.map((lane, li) =>
          lane.map((c) => {
            const hz = hazardOf(c.hazard_type);
            const x = 232 + li * 44;
            return (
              <g key={c.corridor_id} onMouseEnter={() => setHover(c)} onMouseLeave={() => setHover(null)} style={{ cursor: 'pointer' }}>
                <rect x={x} y={y(c.depth_start_m)} width={36} height={Math.max(4, y(c.depth_end_m) - y(c.depth_start_m))} rx={4}
                  fill={hz.soft} stroke={hz.color} strokeWidth={hover?.corridor_id === c.corridor_id ? 2 : 1} />
                <text x={x + 18} y={y(c.depth_start_m) + 12} textAnchor="middle" fontSize={9.5} fontWeight={600} fill={hz.color}>{hz.short}</text>
                <text x={x + 18} y={y(c.depth_start_m) + 23} textAnchor="middle" fontSize={9} className="num" fill={hz.color}>{c.contributing_wells.length}w</text>
              </g>
            );
          }),
        )}
        {/* bit */}
        <g style={{ transition: 'transform .7s ease' }} transform={`translate(0 ${y(depth)})`}>
          <line x1={44} x2={W} y1={0} y2={0} stroke="var(--accent)" strokeWidth={1.6} />
          <rect x={W - 78} y={-11} width={76} height={20} rx={10} fill="var(--accent)" />
          <text x={W - 40} y={3.5} textAnchor="middle" fontSize={10.5} fill="#fff" className="num">{Math.round(depth)} m</text>
          <path d="M40 -6 L48 0 L40 6 Z" fill="var(--accent)" />
        </g>
      </svg>
      <div className="flex flex-wrap gap-x-3 gap-y-1 px-2 text-[11px] text-ink-3">
        <span>Left: formations · ▶ casing shoe · right: trouble zones from offset wells (letters = hazard, “w” = wells)</span>
      </div>
      {hover && (
        <div className="absolute right-4 top-4 w-60 bg-surface border border-line rounded-lg shadow-pop p-3 text-xs pointer-events-none">
          <HazardChip hazard={hover.hazard_type} />
          <div className="num font-medium mt-1.5">{m(hover.depth_start_m)} – {m(hover.depth_end_m)}</div>
          <div className="text-ink-2 mt-1">{hover.event_count} event(s) in {hover.contributing_wells.map(shortWell).join(', ')}</div>
          <div className="text-ink-2">Avg lost time {n(hover.avg_npt_hours, 1)} h · worst {sevOf(hover.max_severity).label.toLowerCase()}</div>
          {hover.lead_distance_m !== null && <div className={cx('mt-1 font-medium')}>{hover.lead_distance_m > 0 ? `${m(hover.lead_distance_m)} below the bit` : 'Bit is in or below this zone'}</div>}
        </div>
      )}
    </div>
  );
};

function useThrottled<T>(value: T, ms: number) {
  const [v, setV] = useState(value);
  const last = useRef(0);
  const t = useRef<number>();
  useEffect(() => {
    const now = Date.now();
    const wait = Math.max(0, ms - (now - last.current));
    window.clearTimeout(t.current);
    t.current = window.setTimeout(() => { last.current = Date.now(); setV(value); }, wait);
    return () => window.clearTimeout(t.current);
  }, [value, ms]);
  return v;
}
