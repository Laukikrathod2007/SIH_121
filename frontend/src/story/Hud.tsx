import React from 'react';
import { LOOKAHEAD, PILLARS, RANKING, type PhaseId } from './phases';

// Product-UI overlays: what the engineer actually sees in DrillWise at
// each phase, drawn as crisp HTML over the 3D world (right-hand side).
// p = progress through the phase (0..1).

const clamp = (x: number) => Math.min(1, Math.max(0, x));
const seg = (p: number, a: number, b: number) => {
  const t = clamp((p - a) / (b - a));
  return t * t * (3 - 2 * t);
};

function Panel({ title, tag, children, o, className = '' }: { title: string; tag?: string; children: React.ReactNode; o: number; className?: string }) {
  if (o < 0.01) return null;
  return (
    <div className={`hud-panel ${className}`} style={{ opacity: o, transform: `translateY(${(1 - o) * 10}px)` }}>
      <div className="hud-head">
        <span>{title}</span>
        {tag && <em>{tag}</em>}
      </div>
      {children}
    </div>
  );
}

/** Live drilling readout: the eRTMAC view she has today. */
function Telemetry({ p }: { p: number }) {
  const md = 2850 - (1 - seg(p, 0, 0.8)) * 12;
  const rows: [string, string][] = [
    ['Bit depth', `${md.toFixed(1)} m MD`],
    ['ROP', '11.8 m/h'],
    ['WOB', '14.6 t'],
    ['RPM', '92'],
    ['Mud weight', '10.4 ppg'],
    ['Pit volume', '412 bbl'],
  ];
  return (
    <Panel title="eRTMAC · live" tag="NHK-002" o={seg(p, 0.25, 0.45)}>
      <dl className="hud-kv">
        {rows.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
      <div className="hud-missing" style={{ opacity: seg(p, 0.6, 0.8) }}>
        Offset-well history <b>· not available</b>
      </div>
    </Panel>
  );
}

/** Manual search: opening reports one by one. */
function ManualSearch({ p }: { p: number }) {
  const opened = Math.floor(seg(p, 0.15, 0.95) * 39);
  return (
    <Panel title="Search · by hand" tag="kick · Kopili" o={seg(p, 0.2, 0.35)}>
      <div className="hud-big">
        {opened}
        <span> / 39 reports opened</span>
      </div>
      <div className="hud-bar">
        <i style={{ width: `${(opened / 39) * 100}%` }} />
      </div>
      <div className="hud-note">Match found · {opened > 34 ? '1' : '0'}</div>
    </Panel>
  );
}

/** Extraction result for the key report. */
function Extracted({ p }: { p: number }) {
  const rows: [string, string, boolean?][] = [
    ['Well', 'BGJ-007'],
    ['Event', 'KICK', true],
    ['Depth', '2,905.3 m MD'],
    ['Formation', 'Kopili'],
    ['Severity', 'HIGH', true],
    ['Mitigation', 'Shut in · Driller’s Method'],
    ['NPT', '2.7 h'],
  ];
  return (
    <Panel title="Structured event" tag="EVT-AB0C8C22" o={seg(p, 0.55, 0.7)}>
      <dl className="hud-kv">
        {rows.map(([k, v, hot], i) => (
          <div key={k} style={{ opacity: seg(p, 0.6 + i * 0.035, 0.66 + i * 0.035) }}>
            <dt>{k}</dt>
            <dd className={hot ? 'is-hot' : ''}>
              {v} <span className="hud-ok">✓</span>
            </dd>
          </div>
        ))}
      </dl>
      <div className="hud-note">Source · DDR_WELL-BGJ-007_2905m.pdf · page 2</div>
    </Panel>
  );
}

function Radius({ p }: { p: number }) {
  const km = Math.round(60 * seg(p, 0.1, 0.75));
  const inside = [12.3, 16.4, 26.9, 31.4, 35.8, 37.7, 38.5, 39.4, 53.9, 54.8, 56.3].filter((d) => d <= km).length;
  return (
    <Panel title="Nearby wells" tag="radius" o={seg(p, 0.1, 0.25)}>
      <div className="hud-big">
        {km}
        <span> km</span>
      </div>
      <div className="hud-bar">
        <i style={{ width: `${(km / 60) * 100}%` }} />
      </div>
      <div className="hud-note">{inside} offset wells inside the radius</div>
    </Panel>
  );
}

function Ranking({ p }: { p: number }) {
  const show = seg(p, 0.15, 0.35);
  return (
    <Panel title="Offset relevance · DORS" tag="5 factors" o={show}>
      <ol className="hud-rank">
        {RANKING.slice(0, 10).map((r, i) => {
          const hot = i < 2;
          const closest = r.id === 'NHK-001';
          return (
            <li key={r.id} className={hot ? 'is-top' : closest ? 'is-closest' : ''} style={{ opacity: seg(p, 0.2 + i * 0.03, 0.3 + i * 0.03) }}>
              <span className="hud-rank-n">{i + 1}</span>
              <span className="hud-rank-id">{r.id}</span>
              <span className="hud-rank-bar">
                <i style={{ width: `${r.score * 100 * show}%` }} />
              </span>
              <span className="hud-rank-v">{r.score.toFixed(2)}</span>
              <span className="hud-rank-km">{r.km} km</span>
            </li>
          );
        })}
      </ol>
      <div className="hud-note" style={{ opacity: seg(p, 0.6, 0.75) }}>
        Closest well <b>NHK-001</b> ranks 9th · stops at 2,820 m
      </div>
    </Panel>
  );
}

function Correlation({ p }: { p: number }) {
  return (
    <Panel title="Knowledge search" tag="Kopili · kick" o={seg(p, 0.45, 0.6)}>
      {[
        ['NHK-003', 'Kick · 2,663.9 m', 'Pit gain; shut in; killed'],
        ['BGJ-007', 'Kick · 2,905.3 m', 'Shut in BOP; Driller’s Method; 2.7 h NPT'],
      ].map(([w, e, m], i) => (
        <div key={w} className="hud-hit" style={{ opacity: seg(p, 0.55 + i * 0.08, 0.65 + i * 0.08) }}>
          <div>
            <b>{w}</b> {e}
          </div>
          <span>{m}</span>
        </div>
      ))}
      <div className="hud-note" style={{ opacity: seg(p, 0.75, 0.9) }}>
        Same formation · correlated across 3 wells
      </div>
    </Panel>
  );
}

function Lookahead({ p }: { p: number }) {
  const W = 300;
  const Hh = 110;
  const X = (md: number) => ((md - 2850) / 200) * W;
  const Y = (v: number) => Hh - v * Hh;
  const path = (k: 'kick' | 'op') => LOOKAHEAD.map((d, i) => `${i ? 'L' : 'M'}${X(d.md).toFixed(1)} ${Y(d[k]).toFixed(1)}`).join(' ');
  const draw = seg(p, 0.15, 0.8);
  return (
    <Panel title="Ahead of bit · 200 m" tag="from offset wells" o={seg(p, 0.1, 0.25)}>
      <svg viewBox={`-6 -8 ${W + 12} ${Hh + 30}`} className="hud-chart">
        <defs>
          <clipPath id="hud-reveal">
            <rect x={-6} y={-8} width={W * draw + 6} height={Hh + 30} />
          </clipPath>
        </defs>
        {[0, 0.5, 1].map((v) => (
          <line key={v} x1={0} x2={W} y1={Y(v)} y2={Y(v)} className="hud-grid" />
        ))}
        <g clipPath="url(#hud-reveal)">
          <path d={path('op')} className="hud-line-op" />
          <path d={path('kick')} className="hud-line-kick" />
        </g>
        {[2850, 2950, 3050].map((m) => (
          <text key={m} x={X(m)} y={Hh + 18} textAnchor="middle" className="hud-axis">
            {m.toLocaleString('en-IN')}
          </text>
        ))}
      </svg>
      <div className="hud-legend">
        <span className="op">Overpressure · peak 0.70 @ 2,870 m</span>
        <span className="kick">Kick · peak 0.97 @ 3,030 m</span>
      </div>
    </Panel>
  );
}

function Alert({ p }: { p: number }) {
  return (
    <>
      <Panel title="Alert · kick risk HIGH" tag="Kopili · ahead of bit" o={seg(p, 0.05, 0.2)} className="hud-alert">
        <div className="hud-sub">Recommended action</div>
        <ul className="hud-actions">
          {['Verify kill mud on standby', 'Slow ROP through high-pressure zones', 'Monitor flow and pit volume'].map((s, i) => (
            <li key={s} style={{ opacity: seg(p, 0.15 + i * 0.06, 0.25 + i * 0.06) }}>
              {s}
            </li>
          ))}
        </ul>
        <div className="hud-sub">Evidence · offset wells</div>
        <div className="hud-ev" style={{ opacity: seg(p, 0.35, 0.45) }}>
          NHK-003 · kick 2,663.9 m <span>open ↗</span>
        </div>
        <div className="hud-ev" style={{ opacity: seg(p, 0.4, 0.5) }}>
          BGJ-007 · kick 2,905.3 m · DDR p.2 <span>open ↗</span>
        </div>
      </Panel>
      <Panel title="Confidence · four pillars" o={seg(p, 0.45, 0.6)}>
        {PILLARS.map((pl, i) => (
          <div key={pl.label} className="hud-pillar">
            <span>{pl.label}</span>
            <i>
              <b style={{ width: `${pl.score * 100 * seg(p, 0.5 + i * 0.05, 0.65 + i * 0.05)}%` }} />
            </i>
            <em>{pl.value}</em>
          </div>
        ))}
      </Panel>
    </>
  );
}

export function Hud({ id, p }: { id: PhaseId; p: number }) {
  return (
    <div className="hud">
      {id === 'well' && <Telemetry p={p} />}
      {id === 'buried' && <ManualSearch p={p} />}
      {id === 'extract' && <Extracted p={p} />}
      {id === 'nearby' && <Radius p={p} />}
      {id === 'relevant' && <Ranking p={p} />}
      {id === 'correlate' && <Correlation p={p} />}
      {id === 'ahead' && <Lookahead p={p} />}
      {id === 'decide' && <Alert p={p} />}
    </div>
  );
}
