import React, { useEffect, useState } from 'react';
import {
  Activity,
  CheckCircle,
  XCircle,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { HealthResponseM01, HealthResponseM02, SimulationStatus } from '../types';

// Renders REAL health data from GET /api/v1/health (module 01),
// GET /api/v2/health (module 02), and GET /api/v3/physics/status + /predictive/models
// (module 04, which also hosts module 05's predictive code) — replaces the
// previous page's fetch-then-ignore pattern and its hardcoded
// "105/105 TESTS PASSING" banner, fake per-stage latency table, and fake
// ROC-AUC/F1 model-registry cards. Module 04/05's card used to be a
// permanently-amber "NOT CONNECTED" static block written before that module
// existed in this project — found stale (module 04 is real, running, and
// healthy) during the end-to-end verification pass and replaced with a real
// check, same pattern as the other two cards (module 04/05 has no
// dedicated /api/v3 health route of its own, so /physics/status is used as
// the liveness probe, same as BackendStatusStrip.tsx already does).

function StatusDot({ ok }: { ok: boolean | null }) {
  if (ok === null) return <span className="w-2 h-2 rounded-full bg-slate-600 inline-block" />;
  return <span className={`w-2 h-2 rounded-full inline-block ${ok ? 'bg-emerald-400' : 'bg-rose-400'}`} />;
}

export const SystemStatusPage: React.FC = () => {
  const [healthM01, setHealthM01] = useState<HealthResponseM01 | null>(null);
  const [healthM02, setHealthM02] = useState<HealthResponseM02 | null>(null);
  const [statusM04, setStatusM04] = useState<SimulationStatus | null>(null);
  const [modelsM04, setModelsM04] = useState<any[] | null>(null);
  const [errorM01, setErrorM01] = useState<string | null>(null);
  const [errorM02, setErrorM02] = useState<string | null>(null);
  const [errorM04, setErrorM04] = useState<string | null>(null);
  const [pinging, setPinging] = useState<boolean>(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setPinging(true);
    const [m01, m02, m04status, m04models] = await Promise.allSettled([
      api.getHealthM01(),
      api.getHealthM02(),
      api.getSimStatus(),
      api.getRegisteredModels(),
    ]);

    if (m01.status === 'fulfilled') {
      setHealthM01(m01.value);
      setErrorM01(null);
    } else {
      setHealthM01(null);
      setErrorM01('Unreachable. Contact your system administrator if this persists.');
    }

    if (m02.status === 'fulfilled') {
      setHealthM02(m02.value);
      setErrorM02(null);
    } else {
      setHealthM02(null);
      setErrorM02('Unreachable. Contact your system administrator if this persists.');
    }

    if (m04status.status === 'fulfilled') {
      setStatusM04(m04status.value);
      setErrorM04(null);
    } else {
      setStatusM04(null);
      setErrorM04('Unreachable. Contact your system administrator if this persists.');
    }
    setModelsM04(m04models.status === 'fulfilled' ? m04models.value : null);

    setLastChecked(new Date());
    setPinging(false);
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const m01Healthy = healthM01?.status === 'healthy';
  const m02Healthy = healthM02?.status === 'healthy';
  const m04Healthy = statusM04 !== null;

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
              SYSTEM STATUS — LIVE SERVICE HEALTH
            </div>
            <div className="text-xs text-slate-400 font-mono">
              {lastChecked ? `Last checked ${lastChecked.toLocaleTimeString()}` : 'Checking…'}
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

      {/* Document Intelligence & Well Intelligence Health Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Document Intelligence */}
        <div className="scada-panel p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono font-bold text-slate-200">DOCUMENT INTELLIGENCE</span>
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

        {/* Well Intelligence */}
        <div className="scada-panel p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-mono font-bold text-slate-200">WELL INTELLIGENCE</span>
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

      {/* Simulation & Predictive Risk — real check via live physics status
          (liveness) and the predictive model registry (honest
          fitted/unfitted ML status) */}
      <div className={`scada-panel p-4 space-y-2 border-l-4 ${m04Healthy ? 'border-l-emerald-500' : 'border-l-amber-500'}`}>
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <span className="text-xs font-mono font-bold text-slate-200">SIMULATION &amp; PREDICTIVE RISK</span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${
            m04Healthy ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
          }`}>
            {m04Healthy ? <CheckCircle className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
            {m04Healthy ? 'HEALTHY' : 'UNREACHABLE'}
          </span>
        </div>

        {errorM04 && (
          <div className="text-[11px] font-mono text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded p-2 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> {errorM04}
          </div>
        )}

        {statusM04 && (
          <div className="space-y-1.5 text-xs font-mono">
            <div className="p-2 bg-slate-900/70 border border-slate-800 rounded">
              <div className="text-slate-400 text-[10px]">PHYSICS ENGINE</div>
              <div className="text-slate-200">
                running: {String(statusM04.is_running)} · depth: {statusM04.measured_depth_m?.toFixed(1)}m · speed: {statusM04.speed_multiplier}x
              </div>
            </div>
            {modelsM04 && (
              <div className="p-2 bg-slate-900/70 border border-slate-800 rounded">
                <div className="text-slate-400 text-[10px]">PREDICTIVE MODELS</div>
                <div className="space-y-1 mt-1">
                  {modelsM04.map((m: any) => (
                    <div key={m.model_id} className="flex items-center justify-between">
                      <span className="flex items-center gap-2 text-slate-200">
                        <StatusDot ok={m.status === 'ACTIVE'} /> {m.model_id}
                      </span>
                      <span className={`text-[10px] ${m.status === 'ACTIVE' ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {m.status}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="text-[10px] text-slate-500 pt-1">
                  UNFITTED_FALLBACK means no trained .joblib artifact exists on disk for that model — the rule
                  engine pillar still runs real, deterministic hazard scoring; this is not a fabricated metric.
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
