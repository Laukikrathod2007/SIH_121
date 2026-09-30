import React from 'react';
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
  Activity,
  Radio,
  Bot,
  Radar,
  Sun,
  Moon,
  MapPin,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useTheme } from '../../hooks/useTheme';

export const Sidebar: React.FC = () => {
  const { alerts, simStatus, isWsConnected } = useApp();
  const { theme, setTheme } = useTheme();

  const activeAlertsCount = alerts.filter(a => a.severity === 'CRITICAL' || a.severity === 'WARNING').length;

  const navItems = [
    { to: '/app', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/app/command-center', label: 'Command Center', icon: Radar, badge: 'NEW' },
    { to: '/app/drilling', label: 'Live Drilling', icon: Gauge, badge: isWsConnected ? 'LIVE' : undefined },
    { to: '/app/wells', label: 'Nearby Wells', icon: Compass },
    { to: '/app/offset-map', label: 'Offset Map', icon: MapPin, badge: 'NEW' },
    { to: '/app/correlation', label: 'Geological Correlation', icon: Layers },
    { to: '/app/risk', label: 'Risk & Prediction', icon: ShieldAlert },
    { to: '/app/alerts', label: 'Alerts & Advisory', icon: BellRing, alertCount: activeAlertsCount },
    { to: '/app/knowledge', label: 'Historical Search', icon: BookOpen },
    { to: '/app/copilot', label: 'Knowledge Copilot', icon: Bot },
    { to: '/app/documents', label: 'Document Ingestion', icon: FileUp },
    { to: '/app/simulator', label: 'Scenario Simulator', icon: Cpu, isSimActive: simStatus?.is_running },
    { to: '/app/reports', label: 'Reports & Analytics', icon: FileSpreadsheet },
    { to: '/app/status', label: 'System Architecture', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-[var(--bg-card)] border-r border-slate-800/80 flex flex-col h-screen select-none z-20 shrink-0">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800/80 bg-[var(--bg-elevated)]">
        <img
          src="/brand/drillwise-logo-horizontal.png"
          alt="DrillWise — Powered by eWIS"
          className="w-full h-auto max-h-9 object-contain object-left"
        />
        <div className="text-[11px] text-slate-400 font-mono tracking-tight mt-1.5">OIL INDIA LIMITED</div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest px-3 py-1">
          OPERATIONAL MODULES
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/app'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2 rounded text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                    : 'text-slate-300 hover:text-slate-100 hover:bg-slate-800/40'
                }`
              }
            >
              <div className="flex items-center space-x-2.5">
                <Icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </div>
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
                {item.isSimActive && (
                  <span className="w-2 h-2 rounded-full bg-amber-400 pulse-green"></span>
                )}
              </div>
            </NavLink>
          );
        })}
      </nav>

      {/* Bottom Rig Status Footnote */}
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

        {/* Theme toggle -- moved here from the top header bar, which was
            already packed enough that this got silently pushed off-screen
            there with no overflow handling. Guaranteed visible here. */}
        <div className="flex items-center bg-slate-900 border border-slate-700 rounded p-0.5 mt-1">
          <button
            onClick={() => setTheme('light')}
            className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded transition ${
              theme === 'light' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sun className="w-3 h-3" /> Light
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={`flex-1 flex items-center justify-center gap-1 px-2 py-1 rounded transition ${
              theme === 'dark' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Moon className="w-3 h-3" /> Dark
          </button>
        </div>
      </div>
    </aside>
  );
};
