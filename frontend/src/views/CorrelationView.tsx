import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { API, api, type Station, type WellProfile } from '../lib/api';
import { hazardOf, m, sevOf } from '../lib/format';
import { useLoad, useNwis } from '../state/nwis';
import { ErrorNote, HazardChip, Loading, PageHeader, Panel, PanelHead, Segmented, SourceLink, cx } from '../ui/primitives';

type Mode = 'md' | 'tvd' | 'flat';
type Align = Record<string, { well_name: string; md_m: number; tvd_m: number; tvdss_m: number; formation: string | null; d_strat_m: number | null; is_active: boolean }>;
type Column = { id: string; name: string; profile: WellProfile; stations: Station[]; equiv?: Align[string] };

const FM_COLORS: Record<string, string> = {
  Alluvium: '#f1ead8', Dihing: '#ece3cb', 'Tipam Sandstone': '#f4e1b8', 'Girujan Clay': '#dfe6d2', 'Barail Sandstone': '#efd9bf',
  'Barail Coal-Shale': '#d9d6d0', Kopili: '#dde3ea', 'Sylhet Limestone': '#e3eef0', Langpar: '#eadcdc', Basement: '#e2dcd6',
};
const fmColor = (f: string) => FM_COLORS[f] ?? '#ebe8e1';

function tvdAt(stations: Station[], md: number) {
  if (!stations.length) return md;
  if (md <= stations[0].md_m) return (md / Math.max(stations[0].md_m, 1)) * stations[0].tvd_m;
  for (let i = 1; i < stations.length; i++) {
    const a = stations[i - 1], b = stations[i];
    if (b.md_m >= md) return a.tvd_m + ((md - a.md_m) / Math.max(b.md_m - a.md_m, 0.001)) * (b.tvd_m - a.tvd_m);
  }
  const last = stations[stations.length - 1];
  return last.tvd_m + (md - last.md_m) * Math.cos((last.inclination_deg * Math.PI) / 180);
}

export const CorrelationView: React.FC = () => {
  const { activeWellId, activeWell, bitDepth } = useNwis();
  const [params] = useSearchParams();
  const pinned = params.get('offset');
  const [mode, setMode] = useState<Mode>('flat');
  const td = activeWell?.total_depth_md_m ?? 3000;
  const [depth, setDepth] = useState<number>(Math.round(td * 0.9));
  useEffect(() => { setDepth(Math.round((bitDepth ?? td * 0.9))); }, [activeWellId]); // eslint-disable-line react-hooks/exhaustive-deps
  const [hover, setHover] = useState<string | null>(null);

  const track = useLoad(() => (activeWellId ? api.depthTrack(activeWellId, depth, 4) : Promise.resolve(null)), [activeWellId, depth]);
  const align = (track.data?.alignment ?? {}) as unknown as Align;
  const ids = useMemo(() => {
    const base = Object.keys(align);
    if (pinned && !base.includes(pinned)) base.splice(1, 0, pinned);
    return base.slice(0, 5);
  }, [track.data, pinned]); // eslint-disable-line react-hooks/exhaustive-deps

  const cols = useLoad<Column[]>(async () => {
    if (!ids.length) return [];
    return Promise.all(ids.map(async (id) => {
      const [profile, t] = await Promise.all([api.profile(id), api.trajectory(id).catch(() => ({ stations: [] as Station[] }))]);
      return { id, name: profile.well.well_name, profile, stations: t.stations, equiv: align[id] };
    }));
  }, [ids.join('|')]);

  const bitFm = track.data?.formation_at_bit ?? null;

  // Depth transform per column
  const toY = (c: Column, md: number) => {
    const tvd = tvdAt(c.stations, md);
    if (mode === 'md') return md;
    if (mode === 'tvd') return tvd;
    const ref = c.profile.formations.find((f) => f.formation_name === bitFm);
    return ref ? tvd - ref.top_tvd_m : tvd;
  };

  const data = cols.data ?? [];
  const range = useMemo(() => {
    let lo = Infinity, hi = -Infinity;
    data.forEach((c) => {
      const window = 450;
      const center = c.equiv ? c.equiv.md_m : depth;
      [center - window, center + window].forEach((md) => {
        const v = toY(c, Math.max(0, Math.min(md, c.profile.well.total_depth_md_m)));
        lo = Math.min(lo, v); hi = Math.max(hi, v);
      });
    });
    return Number.isFinite(lo) ? [lo, hi] : [0, 1];
  }, [data, mode, depth, bitFm]); // eslint-disable-line react-hooks/exhaustive-deps

  const H = 620, top = 28, colW = 116, gap = 46, left = 50;
  const W = left + data.length * colW + Math.max(0, data.length - 1) * gap + 20;
  const y = (v: number) => top + ((v - range[0]) / (range[1] - range[0] || 1)) * (H - top - 20);
  const colX = (i: number) => left + i * (colW + gap);

  return (
    <div className="px-6 py-6 max-w-[1500px]">
      <PageHeader
        eyebrow="Correlation by depth and formation"
        title="Is the same rock trouble in every well?"
        lead={<>Wells are drilled at different angles and start from different elevations, so the same formation sits at different measured depths. Line them up on the formation at the bit to compare like with like. The dashed marker shows where the active bit depth falls in each offset well.</>}
      />

      <Panel className="mb-5">
        <div className="flex flex-wrap items-center gap-5 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-2">Align wells by</span>
            <Segmented<Mode> value={mode} onChange={setMode} options={[
              { value: 'flat', label: `Formation (${bitFm ?? '…'})` },
              { value: 'tvd', label: 'True vertical depth' },
              { value: 'md', label: 'Measured depth' },
            ]} />
          </div>
          <div className="flex items-center gap-3 flex-1 min-w-[280px]">
            <span className="text-xs text-ink-2 whitespace-nowrap">Active bit depth</span>
            <input type="range" min={Math.round(td * 0.2)} max={td} step={5} value={depth} onChange={(e) => setDepth(Number(e.target.value))} className="flex-1" aria-label="Active bit depth" />
            <span className="num text-[13px] w-20 text-right">{m(depth)}</span>
          </div>
        </div>
      </Panel>

      {(track.error || cols.error) && <ErrorNote message={(track.error || cols.error)!} onRetry={() => { track.reload(); cols.reload(); }} />}

      <div className="grid grid-cols-1 2xl:grid-cols-[1fr_380px] gap-5">
        <Panel className="overflow-x-auto">
          <PanelHead title="Correlation panel" hint={mode === 'flat' ? `Depths shown relative to the top of the ${bitFm} in each well (0 = formation top).` : mode === 'tvd' ? 'True vertical depth from rotary table.' : 'Measured depth along hole — misleading for deviated wells.'} />
          {cols.loading || track.loading ? <Loading label="Aligning wells" /> : (
            <svg viewBox={`0 0 ${W} ${H}`} style={{ minWidth: W }} className="w-full">
              {/* axis */}
              {Array.from({ length: 7 }, (_, i) => range[0] + ((range[1] - range[0]) * i) / 6).map((v) => (
                <g key={v}>
                  <line x1={left - 6} x2={W - 10} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeWidth={0.5} />
                  <text x={left - 10} y={y(v) + 3} textAnchor="end" fontSize={9.5} className="num" fill="var(--ink-3)">{Math.round(v)}</text>
                </g>
              ))}
              {/* correlation lines between same formation tops */}
              {data.slice(0, -1).map((c, i) => {
                const nxt = data[i + 1];
                return c.profile.formations.map((f) => {
                  const g = nxt.profile.formations.find((x) => x.formation_name === f.formation_name);
                  if (!g) return null;
                  const y1 = y(toY(c, f.top_md_m)), y2 = y(toY(nxt, g.top_md_m));
                  if (y1 < top - 2 && y2 < top - 2) return null;
                  if (y1 > H && y2 > H) return null;
                  const isBit = f.formation_name === bitFm;
                  return <line key={`${c.id}-${f.formation_name}`} x1={colX(i) + colW} x2={colX(i + 1)} y1={y1} y2={y2}
                    stroke={isBit ? 'var(--accent)' : 'var(--ink-3)'} strokeWidth={isBit ? 1.6 : 0.7} strokeDasharray={isBit ? '' : '3 3'} opacity={isBit ? 0.9 : 0.6} />;
                });
              })}
              {data.map((c, i) => {
                const x0 = colX(i);
                const fms = c.profile.formations.slice().sort((a, b) => a.top_md_m - b.top_md_m);
                return (
                  <g key={c.id}>
                    <clipPath id={`clip-${i}`}><rect x={x0} y={top} width={colW} height={H - top - 20} /></clipPath>
                    <g clipPath={`url(#clip-${i})`}>
                      {fms.map((f, k) => {
                        const endMd = k < fms.length - 1 ? fms[k + 1].top_md_m : f.base_md_m ?? c.profile.well.total_depth_md_m;
                        const y0 = y(toY(c, f.top_md_m)), y1 = y(toY(c, endMd));
                        return (
                          <g key={f.formation_name}>
                            <rect x={x0} y={y0} width={colW} height={Math.max(0.5, y1 - y0)} fill={fmColor(f.formation_name)} stroke="#fff" strokeWidth={1} />
                            {y1 - y0 > 16 && <text x={x0 + 6} y={y0 + 12} fontSize={9.5} fill="var(--ink-2)">{f.formation_name}</text>}
                          </g>
                        );
                      })}
                      {c.profile.events.map((e) => {
                        const ey = y(toY(c, e.depth_start_md_m));
                        const hz = hazardOf(e.event_type);
                        const on = hover === e.event_id;
                        return (
                          <g key={e.event_id} onMouseEnter={() => setHover(e.event_id)} onMouseLeave={() => setHover(null)} style={{ cursor: 'pointer' }}>
                            <rect x={x0 + colW - 40} y={ey - 7} width={36} height={14} rx={7} fill={on ? hz.color : hz.soft} stroke={hz.color} />
                            <text x={x0 + colW - 22} y={ey + 3.5} textAnchor="middle" fontSize={9} fontWeight={600} fill={on ? '#fff' : hz.color}>{hz.short}</text>
                          </g>
                        );
                      })}
                      {/* equivalent-depth marker */}
                      {c.equiv && (() => {
                        const ey = y(toY(c, c.equiv.md_m));
                        return (
                          <g>
                            <line x1={x0} x2={x0 + colW} y1={ey} y2={ey} stroke="var(--accent)" strokeWidth={c.equiv.is_active ? 2.2 : 1.6} strokeDasharray={c.equiv.is_active ? '' : '5 3'} />
                            <rect x={x0 + 2} y={ey - 16} width={62} height={13} rx={3} fill="var(--accent)" />
                            <text x={x0 + 33} y={ey - 6.5} textAnchor="middle" fontSize={9} className="num" fill="#fff">{Math.round(c.equiv.md_m)} m MD</text>
                          </g>
                        );
                      })()}
                    </g>
                    <rect x={x0} y={top} width={colW} height={H - top - 20} fill="none" stroke="var(--line-strong)" />
                    <text x={x0} y={16} fontSize={12} fontWeight={600} className="num" fill={i === 0 ? 'var(--accent)' : 'var(--ink)'}>{c.name}</text>
                    <text x={x0 + colW} y={16} textAnchor="end" fontSize={9.5} fill="var(--ink-3)">{i === 0 ? 'active' : c.profile.well.well_type}</text>
                  </g>
                );
              })}
            </svg>
          )}
        </Panel>

        <Panel>
          <PanelHead title="Same depth, other wells" hint="What each offset well met at the equivalent position (±150 m)." />
          <div className="divide-y divide-line">
            {data.map((c, i) => {
              const eq = c.equiv?.md_m;
              const near = eq === undefined ? [] : c.profile.events.filter((e) => Math.abs(e.depth_start_md_m - eq) <= 150);
              return (
                <div key={c.id} className="px-4 py-3">
                  <div className="flex items-baseline justify-between">
                    <Link to={`/wells/${c.id}`} className={cx('num text-[13px] font-medium hover:underline', i === 0 && 'text-accent')}>{c.name}</Link>
                    <span className="num text-xs text-ink-3">{eq !== undefined ? `${m(eq)} MD · ${c.equiv?.formation ?? '—'}` : 'no equivalent'}</span>
                  </div>
                  {i === 0 ? (
                    <div className="text-xs text-ink-3 mt-1">Active well — bit reference</div>
                  ) : near.length === 0 ? (
                    <div className="text-xs text-ink-3 mt-1">No incidents near the equivalent depth.</div>
                  ) : near.map((e) => (
                    <div key={e.event_id} className={cx('mt-2 rounded-lg p-2 -mx-2 transition-colors', hover === e.event_id && 'bg-sunken')} onMouseEnter={() => setHover(e.event_id)} onMouseLeave={() => setHover(null)}>
                      <div className="flex items-center gap-2"><HazardChip hazard={e.event_type} /><span className="num text-[11px] text-ink-3">{m(e.depth_start_md_m)}</span><span className="text-[11px] font-semibold" style={{ color: sevOf(e.severity).color }}>{sevOf(e.severity).label}</span></div>
                      <p className="text-xs text-ink-2 mt-1 leading-snug">{e.mitigation_description ? `Action: ${e.mitigation_description}` : e.raw_narrative}</p>
                      <div className="mt-1"><SourceLink doc={e.source_document} page={e.source_page} /></div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </Panel>
      </div>
    </div>
  );
};

export default CorrelationView;

