import React, { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Activity, Bell, BookOpenText, ChevronDown, FileStack, FlaskConical, Gauge, Layers3, Map, Radio, X } from 'lucide-react';
import { useNwis } from '../state/nwis';
import { cx } from './primitives';
import { m, sevOf, shortWell } from '../lib/format';
import { EvidenceViewer } from './EvidenceViewer';

const NAV = [
  { to: '/', label: 'Live well', icon: Gauge, hint: 'What is ahead of the bit' },
  { to: '/map', label: 'Nearby wells', icon: Map, hint: 'Offset wells on the map' },
  { to: '/correlation', label: 'Depth correlation', icon: Layers3, hint: 'Same rock, across wells' },
  { to: '/ask', label: 'Ask the archive', icon: BookOpenText, hint: 'Search past events' },
  { to: '/alerts', label: 'Alerts', icon: Bell, hint: 'Warnings with evidence' },
  { to: '/documents', label: 'Documents', icon: FileStack, hint: 'Reports in, events out' },
  { to: '/sensors', label: 'Rig sensors', icon: Activity, hint: 'Physics twin + risk model' },
  { to: '/models', label: 'Models & benchmarks', icon: FlaskConical, hint: 'Measured accuracy' },
];

const Logo = () => (
  <svg viewBox="0 0 32 32" className="w-7 h-7" aria-hidden>
    <rect width="32" height="32" rx="8" fill="var(--ink)" />
    <circle cx="16" cy="16" r="3.2" fill="#fff" />
    <circle cx="16" cy="16" r="8" fill="none" stroke="#fff" strokeOpacity="0.45" strokeWidth="1.4" />
    <circle cx="16" cy="16" r="12.5" fill="none" stroke="#fff" strokeOpacity="0.18" strokeWidth="1.4" />
    <circle cx="23.2" cy="10.4" r="1.8" fill="#e8a25c" />
    <circle cx="9.5" cy="21.5" r="1.5" fill="#fff" fillOpacity="0.7" />
  </svg>
);

const WellSelect: React.FC = () => {
  const { wells, activeWellId, setActiveWellId, activeWell } = useNwis();
  return (
    <label className="relative flex items-center gap-2 h-9 pl-3 pr-8 rounded-lg border border-line bg-surface hover:border-line-strong cursor-pointer">
      <span className="text-2xs uppercase tracking-[0.08em] text-ink-3">Active well</span>
      <span className="num text-[13px] font-medium text-ink">{activeWell ? activeWell.well_name : '—'}</span>
      <span className="text-xs text-ink-3 hidden md:inline">{activeWell?.field}</span>
      <ChevronDown className="w-4 h-4 text-ink-3 absolute right-2 pointer-events-none" />
      <select
        aria-label="Active well"
        className="absolute inset-0 opacity-0 cursor-pointer"
        value={activeWellId}
        onChange={(e) => setActiveWellId(e.target.value)}
      >
        {wells.map((w) => (
          <option key={w.well_id} value={w.well_id}>
            {w.well_name} — {w.field} ({w.status.toLowerCase()})
          </option>
        ))}
      </select>
    </label>
  );
};

const LivePill: React.FC = () => {
  const { replay, bitDepth } = useNwis();
  if (replay.status !== 'running') return null;
  const level = replay.tick?.overall_risk_level;
  return (
    <NavLink to="/" className="flex items-center gap-2 h-9 px-3 rounded-lg bg-surface border border-line hover:border-line-strong">
      <span className="relative flex w-2 h-2">
        <span className="absolute inset-0 rounded-full animate-pulse-ring" style={{ background: 'var(--accent)' }} />
        <span className="relative w-2 h-2 rounded-full bg-accent" />
      </span>
      <span className="text-xs text-ink-2">Bit</span>
      <span className="num text-[13px] font-medium">{m(bitDepth, 0)}</span>
      {level && <span className="text-[11px] font-semibold" style={{ color: sevOf(level).color }}>{sevOf(level).label}</span>}
    </NavLink>
  );
};

const Toasts: React.FC = () => {
  const { toasts, dismissToast } = useNwis();
  return (
    <div className="fixed bottom-5 right-5 z-[1200] flex flex-col gap-2 w-[360px]">
      {toasts.map((t) => (
        <div key={t.id} className="animate-slide-in bg-surface border border-line rounded-xl shadow-pop p-3.5 pl-4 relative overflow-hidden">
          <span className="absolute left-0 top-0 bottom-0 w-1" style={{ background: sevOf(t.severity).color }} />
          <div className="flex items-start gap-2">
            <div className="flex-1 min-w-0">
              <div className="text-[11px] font-semibold uppercase tracking-[0.06em]" style={{ color: sevOf(t.severity).color }}>New alert · {sevOf(t.severity).label}</div>
              <div className="text-[13px] font-medium text-ink mt-0.5">{t.title}</div>
              <div className="text-xs text-ink-2 mt-0.5 leading-snug">{t.body}</div>
              <NavLink to="/alerts" onClick={() => dismissToast(t.id)} className="inline-block text-xs text-accent font-medium mt-2 hover:underline">See evidence →</NavLink>
            </div>
            <button aria-label="Dismiss" onClick={() => dismissToast(t.id)} className="text-ink-3 hover:text-ink"><X className="w-4 h-4" /></button>
          </div>
        </div>
      ))}
    </div>
  );
};

export const Shell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { online, activeAlerts } = useNwis();
  const loc = useLocation();
  const [now, setNow] = useState(new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 30000); return () => clearInterval(t); }, []);
  const current = loc.pathname.startsWith('/wells/')
    ? { label: 'Well file', hint: loc.pathname.split('/').pop()?.replace(/^WELL-/, '') }
    : NAV.find((n) => (n.to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(n.to)));

  return (
    <div className="h-full flex bg-paper">
      <aside className="w-[232px] shrink-0 border-r border-line bg-paper flex flex-col">
        <div className="h-16 px-4 flex items-center gap-3">
          <Logo />
          <div className="leading-tight">
            <div className="text-[15px] font-semibold tracking-[-0.01em]">NWIS</div>
            <div className="text-[11px] text-ink-3">Nearby Wells Intelligence</div>
          </div>
        </div>
        <nav className="px-2.5 pt-2 flex-1 overflow-y-auto">
          {NAV.map(({ to, label, icon: Icon, hint }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cx('group flex items-center gap-3 px-2.5 py-2 rounded-lg mb-0.5 transition-colors', isActive ? 'bg-surface border border-line shadow-card' : 'border border-transparent hover:bg-sunken')
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={cx('w-[18px] h-[18px] shrink-0', isActive ? 'text-accent' : 'text-ink-3 group-hover:text-ink-2')} strokeWidth={1.8} />
                  <span className="flex-1 min-w-0">
                    <span className={cx('block text-[13px] leading-5', isActive ? 'text-ink font-medium' : 'text-ink-2')}>{label}</span>
                    <span className="block text-[11px] leading-4 text-ink-3 truncate">{hint}</span>
                  </span>
                  {to === '/alerts' && activeAlerts > 0 && (
                    <span className="num text-[11px] min-w-5 h-5 px-1.5 rounded-full text-white flex items-center justify-center" style={{ background: 'var(--sev-high)' }}>{activeAlerts}</span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-line text-[11px] text-ink-3 leading-relaxed">
          <div className="flex items-center gap-1.5">
            <span className={cx('w-1.5 h-1.5 rounded-full', online ? 'bg-sev-low' : online === false ? 'bg-sev-critical' : 'bg-line-strong')} />
            {online ? 'Backend connected' : online === false ? 'Backend offline — retrying' : 'Connecting…'}
          </div>
          <div className="mt-1">Demo data · Upper Assam testbed</div>
          <div className="mt-0.5">Oil India Limited · PS 26121</div>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-16 shrink-0 px-6 flex items-center gap-3 border-b border-line bg-paper/90 backdrop-blur">
          <div className="min-w-0 flex-1">
            <div className="text-[13px] text-ink-3 truncate">
              {current?.label}
              <span className="mx-2 text-line-strong">/</span>
              <span className="text-ink-2">{current?.hint}</span>
            </div>
          </div>
          <LivePill />
          <WellSelect />
          <div className="hidden lg:flex items-center gap-1.5 text-xs text-ink-3 pl-1">
            <Radio className="w-3.5 h-3.5" />
            <span className="num">{now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })} IST</span>
          </div>
        </header>
        <main className="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden">
          {online === false ? (
            <div className="p-10 max-w-xl">
              <h1 className="text-lg font-semibold">The NWIS backend is not reachable</h1>
              <p className="text-ink-2 mt-2 text-[13.5px] leading-relaxed">
                Start it with <code className="num text-xs px-1.5 py-0.5 bg-sunken rounded">python backend/run.py</code> (port 8008). This page reconnects automatically.
              </p>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
      <EvidenceViewer />
      <Toasts />
    </div>
  );
};
