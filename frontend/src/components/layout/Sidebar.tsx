import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Gauge,
  Compass,
  Layers,
  ShieldAlert,
  BellRing,
  BookOpen,
  FileUp,
  Cpu,
  FileSpreadsheet,
  Radio,
  Bot,
  Radar,
  Sun,
  Moon,
  MapPin,
  Globe2,
  PanelLeftOpen,
  PanelLeftClose,
  BookMarked,
  Activity,
  HardHat,
  Briefcase,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useTheme } from '../../hooks/useTheme';

export const Sidebar: React.FC = () => {
  const { alerts, simStatus, isWsConnected, userRole } = useApp();
  const { theme, setTheme } = useTheme();

  // Collapsed (icon-only) by default, giving the dashboards the full width
  // they were being squeezed out of by a permanently-open 256px rail. The
  // choice is per-viewer UI state, so localStorage is the right home for
  // it -- wrapped because it throws in private windows and can come back
  // empty, in which case the default below simply applies.
  const [expanded, setExpanded] = useState<boolean>(() => {
    try {
      return localStorage.getItem('nwis.sidebar.expanded') === 'true';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('nwis.sidebar.expanded', String(expanded));
    } catch {
      /* non-fatal: the sidebar still works, it just won't remember */
    }
  }, [expanded]);

  const activeAlertsCount = alerts.filter(a => a.severity === 'CRITICAL' || a.severity === 'WARNING').length;

  const navItems = [
    { to: '/app', label: 'Dashboard', icon: LayoutDashboard, role: 'all' },
    { to: '/app/command-center', label: 'Command Center', icon: Radar, badge: 'LIVE 3D', role: 'field' },
    { to: '/app/drilling', label: 'Live Drilling', icon: Gauge, badge: isWsConnected ? 'LIVE' : undefined, role: 'field' },
    { to: '/app/wells', label: 'Nearby Wells', icon: Compass, role: 'office' },
    { to: '/app/offset-map', label: 'Offset Map', icon: MapPin, role: 'office' },
    { to: '/app/globe', label: '3D Offset Globe', icon: Globe2, role: 'office' },
    { to: '/app/correlation', label: 'Geological Correlation', icon: Layers, badge: 'CASING', role: 'office' },
    { to: '/app/risk', label: 'Risk & Prediction', icon: ShieldAlert, badge: '7 MODELS', role: 'all' },
    { to: '/app/alerts', label: 'Alerts & Advisory', icon: BellRing, alertCount: activeAlertsCount, role: 'field' },
    { to: '/app/knowledge', label: 'Historical Search', icon: BookOpen, role: 'office' },
    { to: '/app/copilot', label: 'Knowledge Copilot', icon: Bot, badge: 'AGENT', role: 'office' },
    { to: '/app/documents', label: 'Document Ingestion', icon: FileUp, role: 'office' },
    { to: '/app/simulator', label: 'Scenario Simulator', icon: Cpu, isSimActive: simStatus?.is_running, role: 'field' },
    { to: '/app/reports', label: 'Reports & Analytics', icon: FileSpreadsheet, role: 'office' },
    { to: '/app/status', label: 'System & Model Cards', icon: Activity, badge: 'AI CARDS', role: 'all' },
    { to: '/docs', label: 'Documentation', icon: BookMarked, badge: '24 SPECS', role: 'all' },
  ];

  return (
    <aside
      className={`${expanded ? 'w-64' : 'w-16'} bg-[var(--bg-card)] border-r border-slate-800/80 flex flex-col h-screen select-none z-20 shrink-0 transition-[width] duration-200 ease-out`}
    >
      {/* Brand Header -- collapses to the mark + the toggle. The toggle is
          the only control that can re-open the rail, so it stays visible
          in both states. */}
      <div className="border-b border-slate-800/80 bg-[var(--bg-elevated)]">
        {expanded ? (
          <div className="p-4 flex items-start gap-2">
            <div className="flex-1 min-w-0">
              {/* Dark theme: the variant with a light wordmark, so "DRILL" doesn't
                  vanish into the dark sidebar. */}
              <img
                src={theme === 'dark' ? '/brand/drillwise-logo-horizontal-dark.png' : '/brand/drillwise-logo-horizontal.png'}
                alt="DrillWise — Powered by eWIS"
                className="w-full h-auto max-h-9 object-contain object-left"
              />
              <div className="text-[11px] text-slate-400 font-mono tracking-tight mt-1.5">OIL INDIA LIMITED</div>
              <div className="flex items-center gap-1.5 mt-2">
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border flex items-center gap-1 font-semibold ${
                  userRole === 'field'
                    ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                }`}>
                  {userRole === 'field' ? <HardHat className="w-3 h-3" /> : <Briefcase className="w-3 h-3" />}
                  {userRole === 'field' ? 'RIG SITE VIEW' : 'ASSET TEAM VIEW'}
                </span>
              </div>
            </div>
            <button
              onClick={() => setExpanded(false)}
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
              aria-expanded={true}
              className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800/60 transition shrink-0"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="p-3 flex justify-center">
            <button
              onClick={() => setExpanded(true)}
              title="Expand sidebar"
              aria-label="Expand sidebar"
              aria-expanded={false}
              className="p-2 rounded text-slate-300 hover:text-slate-100 hover:bg-slate-800/60 transition"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>

      {/* Navigation List */}
      <nav className={`flex-1 overflow-y-auto overflow-x-hidden space-y-1 ${expanded ? 'p-3' : 'p-2'}`}>
        {expanded && (
          <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest px-3 py-1">
            OPERATIONAL MODULES
          </div>
        )}
        {navItems.map((item) => {
          const Icon = item.icon;
          // Collapsed, the icon is the only label, so the name moves to a
          // title tooltip and aria-label -- otherwise the rail would be
          // unusable to anyone who doesn't already know the icon set, and
          // unreadable to a screen reader.
          const hasDot =
            !!item.badge || !!item.isSimActive || (item.alertCount !== undefined && item.alertCount > 0);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/app'}
              title={expanded ? undefined : item.label}
              aria-label={item.label}
              className={({ isActive }) =>
                `relative flex items-center rounded text-xs font-medium transition-all ${
                  expanded ? 'justify-between px-3 py-2' : 'justify-center px-2 py-2.5'
                } ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                    : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/40'
                }`
              }
            >
              <div className={`flex items-center ${expanded ? 'space-x-2.5' : ''}`}>
                <Icon className="w-4 h-4 shrink-0" />
                {expanded && <span className="truncate">{item.label}</span>}
              </div>

              {expanded ? (
                <div className="flex items-center space-x-1">
                  {item.badge && (
                    <span className="text-[9px] font-mono px-1 py-0.2 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-green"></span>
                      {item.badge}
                    </span>
                  )}
                  {item.alertCount !== undefined && item.alertCount > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 bg-rose-500/30 text-rose-300 border border-rose-500/40 rounded-full font-bold">
                      {item.alertCount}
                    </span>
                  )}
                  {item.isSimActive && <span className="w-2 h-2 rounded-full bg-amber-400 pulse-green"></span>}
                </div>
              ) : (
                // Collapsed there is no room for a badge, but losing the
                // alert count entirely would hide a live CRITICAL/WARNING
                // state, so it degrades to a corner dot rather than vanishing.
                hasDot && (
                  <span
                    className={`absolute top-1 right-1 rounded-full ${
                      item.alertCount !== undefined && item.alertCount > 0
                        ? 'w-1.5 h-1.5 bg-rose-400'
                        : item.isSimActive
                          ? 'w-1.5 h-1.5 bg-amber-400 pulse-green'
                          : 'w-1.5 h-1.5 bg-emerald-400'
                    }`}
                  />
                )
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Rig Status Footnote -- the label/value rows and the
          two-button theme switch need the full rail, so collapsed they
          reduce to a status dot and a single toggle button rather than
          overflowing a 64px column. */}
      {expanded ? (
      <div className="p-3 border-t border-slate-800/80 bg-[var(--bg-elevated)] text-[11px] font-mono space-y-1.5">
        <div className="flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            TELEMETRY BUS
          </span>
          <span className={isWsConnected ? 'text-emerald-400' : 'text-slate-400'}>
            {isWsConnected ? 'STREAMING' : 'POLLING'}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>SIMULATOR</span>
          <span className={simStatus?.is_running ? 'text-amber-400' : 'text-slate-400'}>
            {simStatus?.is_running ? `RUNNING (${simStatus.speed_multiplier}x)` : 'PAUSED'}
          </span>
        </div>
      </div>
      ) : (
        <div className="p-2 border-t border-slate-800/80 bg-[var(--bg-elevated)] flex flex-col items-center gap-2">
          <div
            title={`Telemetry bus: ${isWsConnected ? 'STREAMING' : 'POLLING'}${
              simStatus?.is_running ? ` · simulator RUNNING (${simStatus.speed_multiplier}x)` : ' · simulator PAUSED'
            }`}
            className="p-1.5"
          >
            <Radio className={`w-4 h-4 ${isWsConnected ? 'text-emerald-400' : 'text-slate-400'}`} />
          </div>
        </div>
      )}
    </aside>
  );
};
