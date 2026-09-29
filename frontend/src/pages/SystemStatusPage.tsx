import React, { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle,
  XCircle,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { HealthResponseM01, HealthResponseM02 } from '../types';

// Renders REAL health data from GET /api/v1/health (module 01) and
// GET /api/v2/health (module 02) — replaces the previous page's fetch-then-
// ignore pattern and its hardcoded "105/105 TESTS PASSING" banner, fake
// per-stage latency table, and fake ROC-AUC/F1 model-registry cards.
// Module 03 (physics engine) has no health endpoint because it has no HTTP
// routes at all yet — shown honestly as "NOT CONNECTED" below, not faked.

function StatusDot({ ok }: { ok: boolean | null }) {
  if (ok === null) return <span className="w-2 h-2 rounded-full bg-slate-600 inline-block" />;
  return <span className={`w-2 h-2 rounded-full inline-block ${ok ? 'bg-emerald-400' : 'bg-rose-400'}`} />;
}

export const SystemStatusPage: React.FC = () => {
  const [healthM01, setHealthM01] = useState<HealthResponseM01 | null>(null);
  const [healthM02, setHealthM02] = useState<HealthResponseM02 | null>(null);
  const [errorM01, setErrorM01] = useState<string | null>(null);
  const [errorM02, setErrorM02] = useState<string | null>(null);
  const [pinging, setPinging] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setPinging(true);
    const [m01, m02] = await Promise.allSettled([api.getHealthM01(), api.getHealthM02()]);

    if (m01.status === 'fulfilled') {
      setHealthM01(m01.value);
      setErrorM01(null);
    } else {
      setHealthM01(null);
      setErrorM01('Unreachable — is module 01 running on port 8001 (python run_server.py)?');
    }

    if (m02.status === 'fulfilled') {
      setHealthM02(m02.value);
      setErrorM02(null);
    } else {
      setHealthM02(null);
      setErrorM02('Unreachable — is module 02 running on port 8012 (NWIS_PORT=8012 python run_server.py)?');
    }

    setLastChecked(new Date());
    setPinging(false);
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const m01Healthy = healthM01?.status === 'healthy';
  const m02Healthy = healthM02?.status === 'healthy';

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-emerald-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              SYSTEM STATUS — LIVE BACKEND HEALTH
            </div>
            <div className="text-xs text-slate-400 font-mono">
              GET /api/v1/health (module 01) · GET /api/v2/health (module 02) ·{' '}
              {lastChecked ? `last checked ${lastChecked.toLocaleTimeString()}` : ''}
            </div>
          </div>
        </div>

        <button
          onClick={fetchHealth}
          disabled={pinging}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono flex items-center gap-1.5 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${pinging ? 'animate-spin' : ''}`} /> RE-PING ENDPOINTS
        </button>
      </div>

      {/* Module 01 & 02 Health Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Module 01 */}
        <div className="scada-panel p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono font-bold text-slate-200">MODULE 01 — DOCUMENT INTELLIGENCE (:8001)</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${
              m01Healthy ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
            }`}>
              {m01Healthy ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {healthM01?.status?.toUpperCase() ?? 'UNREACHABLE'}
            </span>
          </div>

          {errorM01 && (
            <div className="text-[11px] font-mono text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded p-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> {errorM01}
            </div>
          )}

          {healthM01 && (
            <div className="space-y-1.5 text-xs font-mono">
              {Object.entries(healthM01.components).map(([name, comp]: [string, any]) => (
                <div key={name} className="flex items-center justify-between p-2 bg-slate-900/70 border border-slate-800 rounded">
                  <span className="flex items-center gap-2 text-slate-200">
                    <StatusDot ok={comp.status === 'ok' || comp.status === 'enabled' || comp.status === 'configured'} />
                    {name}
                  </span>
                  <span className="text-slate-400 text-[10px]">
                    {comp.status}{comp.required ? ' · required' : ''}
                  </span>
                </div>
              ))}
              <div className="text-[10px] text-slate-500 pt-1">jobs_in_queue: {healthM01.jobs_in_queue}</div>
            </div>
          )}
        </div>

        {/* Module 02 */}
        <div className="scada-panel p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono font-bold text-slate-200">MODULE 02 — NWIS BACKEND INTELLIGENCE (:8012)</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${
              m02Healthy ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-rose-500/20 text-rose-300 border-rose-500/40'
            }`}>
              {m02Healthy ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {healthM02?.status?.toUpperCase() ?? 'UNREACHABLE'}
            </span>
          </div>

          {errorM02 && (
            <div className="text-[11px] font-mono text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded p-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> {errorM02}
            </div>
          )}

          {healthM02 && (
            <div className="space-y-1.5 text-xs font-mono">
              <div className="p-2 bg-slate-900/70 border border-slate-800 rounded">
                <div className="text-slate-400 text-[10px]">DATA STORE</div>
                <div className="text-slate-200">{Object.entries(healthM02.data_store).map(([k, v]) => `${k}: ${v}`).join(' · ')}</div>
              </div>
              <div className="p-2 bg-slate-900/70 border border-slate-800 rounded">
                <div className="text-slate-400 text-[10px]">ENGINES</div>
                <div className="text-slate-200">{healthM02.engines.join(', ')}</div>
              </div>
              <div className="flex items-center justify-between p-2 bg-slate-900/70 border border-slate-800 rounded">
                <span className="flex items-center gap-2 text-slate-200">
                  <StatusDot ok={healthM02.auth.status === 'enabled'} /> auth
                </span>
                <span className="text-slate-400 text-[10px]">
                  {healthM02.auth.status} · rate limit {healthM02.auth.rate_limiting.enabled ? `${healthM02.auth.rate_limiting.max_requests}/${healthM02.auth.rate_limiting.window_seconds}s` : 'off'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Module 03 — honestly not connected */}
      <div className="scada-panel p-4 space-y-2 border-l-4 border-l-amber-500">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="text-xs font-mono font-bold text-slate-200">MODULE 03 — PHYSICS DIGITAL TWIN / PREDICTIVE ML</span>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold border bg-amber-500/20 text-amber-300 border-amber-500/40">
            NOT CONNECTED
          </span>
        </div>
        <div className="text-[11px] font-mono text-slate-400">
          modules/03_physics_engine/ is being ported in a parallel effort and has no FastAPI routes exposed yet in
          this project — there is no health endpoint to poll, and LiveDrillingPage / SimulatorPage /
          RiskPredictionPage's live hazard scores / AlertsAdvisoryPage all point at a placeholder base URL
          (VITE_M03_API_BASE, default http://localhost:8003) that nothing is currently listening on. This is a
          known gap, not a fabricated "online" status.
        </div>
      </div>
    </div>
  );
};
