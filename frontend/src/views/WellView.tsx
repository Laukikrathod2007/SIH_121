import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Crosshair } from 'lucide-react';
import { api, type Station, type WellProfile } from '../lib/api';
import { docLabel, hazardOf, m, n } from '../lib/format';
import { useLoad, useNwis } from '../state/nwis';
import { Button, Empty, ErrorNote, HazardChip, Loading, PageHeader, Panel, PanelHead, SeverityTag, SourceLink, Segmented, cx } from '../ui/primitives';

type Tab = 'events' | 'program' | 'formations' | 'documents';

export const WellView: React.FC = () => {
  const { wellId = '' } = useParams();
  const { activeWellId, setActiveWellId } = useNwis();
  const p = useLoad<WellProfile>(() => api.profile(wellId), [wellId]);
  const traj = useLoad(() => api.trajectory(wellId), [wellId]);
  const [tab, setTab] = useState<Tab>('events');

  if (p.loading) return <Loading label="Loading well file" />;
  if (p.error || !p.data) return <ErrorNote message={p.error || 'Well not found'} onRetry={p.reload} />;
  const { well, events, casing_program, mud_program, formations, lessons, documents, trajectory_summary: ts } = p.data;

  return (
    <div className="px-6 py-6 max-w-[1440px]">
      <Link to="/map" className="inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink mb-3"><ArrowLeft className="w-3.5 h-3.5" /> Nearby wells</Link>
      <PageHeader
        eyebrow={`${well.field} field · ${well.well_type} · ${well.status.toLowerCase()}`}
        title={`Well file · ${well.well_name}`}
        lead={`Everything NWIS knows about ${well.well_name}: how it was drilled, what went wrong, what fixed it, and the reports it came from.`}
        right={well.well_id === activeWellId ? (
          <span className="text-xs text-accent font-medium px-2.5 py-1 rounded-full bg-accent-soft">Active well</span>
        ) : (
          <Button onClick={() => setActiveWellId(well.well_id)} icon={<Crosshair className="w-4 h-4" />}>Set as active well</Button>
        )}
      />

      <Panel className="mb-5">
        <div className="grid grid-cols-2 md:grid-cols-6 divide-x divide-line">
          {[
            ['Total depth (MD)', m(well.total_depth_md_m)],
            ['Total depth (TVD)', m(ts.td_tvd_m)],
            ['Max inclination', `${n(ts.max_inclination_deg, 1)}°`],
            ['Incidents', String(events.length)],
            ['Lost time', `${n(p.data.total_npt_hours, 1)} h`],
            ['Spud', well.spud_date ?? '—'],
          ].map(([k, v]) => (
            <div key={k} className="px-4 py-3">
              <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">{k}</div>
              <div className="num text-[15px] font-medium mt-0.5">{v}</div>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-5">
        <div className="flex flex-col gap-5">
          <Panel>
            <PanelHead title="Well path" hint="Side view (vertical section) from the survey stations." />
            {traj.data ? <TrajectoryPlot stations={traj.data.stations} events={events} td={well.total_depth_md_m} /> : <Loading />}
          </Panel>
          <Panel>
            <PanelHead title="Lessons learned" hint="What was done about each incident, as written in the reports." />
            {lessons.length === 0 ? <Empty title="No recorded mitigations" /> : (
              <ul className="divide-y divide-line">
                {lessons.map((l) => (
                  <li key={l.event_id} className="px-4 py-3">
                    <div className="flex items-center gap-2"><HazardChip hazard={l.event_type} /><span className="num text-xs text-ink-3">{m(l.depth_m)}</span></div>
                    <p className="text-[13px] mt-1.5 leading-snug">{l.mitigation}</p>
                    {l.outcome && <p className="text-xs text-ink-3 mt-1">Result: {l.outcome}</p>}
                    <div className="mt-1.5"><SourceLink doc={l.source_document} page={l.source_page} /></div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <Panel className="min-w-0">
          <PanelHead
            title="Well record"
            right={<Segmented<Tab> value={tab} onChange={setTab} options={[
              { value: 'events', label: `Incidents (${events.length})` },
              { value: 'program', label: 'Casing & mud' },
              { value: 'formations', label: `Formations (${formations.length})` },
              { value: 'documents', label: `Documents (${documents.length})` },
            ]} />}
          />
          {tab === 'events' && (
            events.length === 0 ? <Empty title="No incidents on record" /> : (
              <table className="w-full text-[13px]">
                <thead><tr className="text-left text-2xs uppercase tracking-[0.08em] text-ink-3 border-b border-line">
                  <th className="px-4 py-2 font-medium">Depth</th><th className="py-2 font-medium">What happened</th><th className="py-2 font-medium">Severity</th><th className="py-2 font-medium text-right">Lost time</th><th className="px-4 py-2 font-medium">Source</th>
                </tr></thead>
                <tbody>
                  {events.map((e) => (
                    <tr key={e.event_id} className="border-b border-line align-top hover:bg-sunken/40">
                      <td className="px-4 py-3 num whitespace-nowrap">{m(e.depth_start_md_m)}<div className="text-[11px] text-ink-3 font-sans">{e.formation}</div></td>
                      <td className="py-3 pr-4 max-w-[520px]">
                        <HazardChip hazard={e.event_type} />
                        <p className="text-ink-2 mt-1.5 leading-snug">{e.raw_narrative}</p>
                        {e.mitigation_description && <p className="mt-1 leading-snug"><span className="font-medium">Action: </span><span className="text-ink-2">{e.mitigation_description}</span></p>}
                      </td>
                      <td className="py-3"><SeverityTag severity={e.severity} /></td>
                      <td className="py-3 num text-right">{n(e.npt_hours, 1)} h</td>
                      <td className="px-4 py-3"><SourceLink doc={e.source_document} page={e.source_page} compact /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
          {tab === 'program' && (
            <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div>
                <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2">Casing program</div>
                {casing_program.length === 0 ? <div className="text-[13px] text-ink-3">Not on record.</div> : (
                  <table className="w-full text-[13px]"><tbody>
                    {casing_program.map((c) => (
                      <tr key={c.casing_size} className="border-b border-line">
                        <td className="py-2 num font-medium">{c.casing_size}</td>
                        <td className="py-2 text-ink-2">in {c.hole_size} hole</td>
                        <td className="py-2 num text-right">{m(c.shoe_md_m)}</td>
                        <td className="py-2 pl-3 text-xs text-ink-3">{c.set_in_formation}</td>
                      </tr>
                    ))}
                  </tbody></table>
                )}
                {casing_program[0] && <div className="mt-2"><SourceLink doc={casing_program[0].source_document} page={1} /></div>}
              </div>
              <div>
                <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2">Mud program</div>
                <table className="w-full text-[13px]"><tbody>
                  {mud_program.map((mu) => (
                    <tr key={mu.formation + mu.from_md_m} className="border-b border-line">
                      <td className="py-2 num whitespace-nowrap">{n(mu.from_md_m)}–{n(mu.to_md_m)} m</td>
                      <td className="py-2 text-ink-2 pl-2">{mu.mud_type}</td>
                      <td className="py-2 num text-right">{mu.mud_weight_ppg.toFixed(1)} ppg</td>
                    </tr>
                  ))}
                </tbody></table>
                <p className="text-[11px] text-ink-3 mt-2">Mud weight = formation pore pressure + planned overbalance.</p>
              </div>
            </div>
          )}
          {tab === 'formations' && (
            <table className="w-full text-[13px]">
              <thead><tr className="text-left text-2xs uppercase tracking-[0.08em] text-ink-3 border-b border-line">
                <th className="px-4 py-2 font-medium">Formation</th><th className="py-2 font-medium text-right">Top MD</th><th className="py-2 font-medium text-right">Top TVD</th><th className="py-2 font-medium text-right">Thickness</th><th className="py-2 font-medium text-right">Pore pressure</th><th className="px-4 py-2 font-medium">Lithology</th>
              </tr></thead>
              <tbody>
                {formations.map((f) => (
                  <tr key={f.formation_name} className="border-b border-line">
                    <td className="px-4 py-2.5 font-medium">{f.formation_name}</td>
                    <td className="py-2.5 num text-right">{m(f.top_md_m)}</td>
                    <td className="py-2.5 num text-right">{m(f.top_tvd_m)}</td>
                    <td className="py-2.5 num text-right">{m(f.thickness_m)}</td>
                    <td className="py-2.5 num text-right">{f.pore_pressure_gradient_ppg ? `${f.pore_pressure_gradient_ppg.toFixed(2)} ppg` : '—'}</td>
                    <td className="px-4 py-2.5 text-ink-2">{f.lithology}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {tab === 'documents' && (
            <ul className="divide-y divide-line">
              {documents.map((d) => (
                <li key={d} className="px-4 py-3 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[13px] font-medium">{docLabel(d)}</div>
                    <div className="num text-[11px] text-ink-3">{d}</div>
                  </div>
                  <SourceLink doc={d} page={1} compact />
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
};

/** Vertical section: horizontal displacement vs TVD, incidents marked at their depth. */
const TrajectoryPlot: React.FC<{ stations: Station[]; events: WellProfile['events']; td: number }> = ({ stations, events, td }) => {
  if (!stations.length) return <Empty title="No survey data" />;
  const W = 320, H = 360, pad = 34;
  const disp = stations.map((s) => Math.hypot(s.ns_m, s.ew_m));
  const maxD = Math.max(200, ...disp);
  const maxT = Math.max(...stations.map((s) => s.tvd_m));
  const x = (d: number) => pad + (d / maxD) * (W - pad - 12);
  const y = (t: number) => 12 + (t / maxT) * (H - 12 - 24);
  const path = stations.map((s, i) => `${i ? 'L' : 'M'}${x(disp[i]).toFixed(1)} ${y(s.tvd_m).toFixed(1)}`).join(' ');
  const atMd = (md: number) => {
    const i = stations.findIndex((s) => s.md_m >= md);
    const k = i < 0 ? stations.length - 1 : i;
    return { d: disp[k], t: stations[k].tvd_m };
  };
  return (
    <div className="p-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line x1={pad} x2={W - 12} y1={y(maxT * f)} y2={y(maxT * f)} stroke="var(--line)" strokeWidth={0.6} />
            <text x={pad - 4} y={y(maxT * f) + 3} textAnchor="end" fontSize={9} className="num" fill="var(--ink-3)">{Math.round(maxT * f)}</text>
          </g>
        ))}
        <text x={W - 12} y={H - 6} textAnchor="end" fontSize={9} fill="var(--ink-3)">horizontal displacement → {Math.round(maxD)} m</text>
        <path d={path} fill="none" stroke="var(--ink)" strokeWidth={2} strokeLinecap="round" />
        {events.map((e) => {
          const p = atMd(e.depth_start_md_m);
          return <circle key={e.event_id} cx={x(p.d)} cy={y(p.t)} r={5} fill={hazardOf(e.event_type).color} stroke="#fff" strokeWidth={1.5}><title>{`${hazardOf(e.event_type).label} at ${Math.round(e.depth_start_md_m)} m MD`}</title></circle>;
        })}
      </svg>
      <div className="text-[11px] text-ink-3 px-1">TVD in metres (down). Dots are incidents at their depth. TD {Math.round(td)} m MD.</div>
    </div>
  );
};
