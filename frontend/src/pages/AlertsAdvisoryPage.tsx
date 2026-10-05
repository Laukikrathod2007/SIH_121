import React, { useState, useEffect, useCallback } from 'react';
import {
  BellRing,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  ShieldCheck,
  RotateCcw,
  Send,
  Zap,
  History,
  Radio,
  Loader2,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { AlertAdvisory } from '../types';

type HistoryState = 'loading' | 'ok' | 'not_configured' | 'unavailable';

export const AlertsAdvisoryPage: React.FC = () => {
  const { alerts, activeWellId, mitigateAlert, refreshAlerts } = useApp();

  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState<Record<string, boolean>>({});
  const [mitigatingId, setMitigatingId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'live' | 'history'>('live');
  const [historyAlerts, setHistoryAlerts] = useState<AlertAdvisory[]>([]);
  const [historyState, setHistoryState] = useState<HistoryState>('loading');

  const loadHistory = useCallback(async () => {
    setHistoryState('loading');
    try {
      const result = await api.getAlertHistory(activeWellId);
      setHistoryAlerts(result.alerts);
      setHistoryState(result.status === 'not_configured' ? 'not_configured' : 'ok');
    } catch {
      // A real 503 (database configured but unreachable) lands here --
      // never rendered as a silently-empty "ok" list (see api.ts's own
      // docstring on getAlertHistory).
      setHistoryAlerts([]);
      setHistoryState('unavailable');
    }
  }, [activeWellId]);

  useEffect(() => {
    if (activeTab === 'history') {
      loadHistory();
    }
  }, [activeTab, loadHistory]);

  const handleAcknowledge = (id: string) => {
    setAcknowledgedAlerts((prev) => ({ ...prev, [id]: true }));
  };

  const handleMitigate = async (id: string) => {
    setMitigatingId(id);
    try {
      await mitigateAlert(id);
      await refreshAlerts();
    } finally {
      setMitigatingId(null);
    }
  };

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-rose-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-rose-500/10 border border-rose-500/30 rounded text-rose-400">
            <BellRing className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              REAL-TIME ALERTS &amp; RECOMMENDED ACTIONS
              <span className="text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/30 px-1.5 py-0.5 rounded">
                SPE / IADC MITIGATION PROTOCOLS
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              Causal Evidence Verification | Human-In-The-Loop Feedback | Autonomous Recovery Verification
            </div>
          </div>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Active Well: <span className="text-cyan-400 font-bold">{activeWellId}</span>
        </div>
      </div>

      {/* Alert Lifecycle Stepper */}
      <div className="scada-panel p-3 flex items-center justify-between text-xs font-mono text-slate-300">
        <div className="flex items-center space-x-2">
          <span className="w-6 h-6 rounded-full bg-rose-500 text-slate-950 font-bold flex items-center justify-center text-[11px]">1</span>
          <span className="font-semibold text-rose-400">1. DETECTED</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-6 h-6 rounded-full bg-amber-500 text-slate-950 font-bold flex items-center justify-center text-[11px]">2</span>
          <span className="font-semibold text-amber-400">2. ACKNOWLEDGED</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-6 h-6 rounded-full bg-cyan-500 text-slate-950 font-bold flex items-center justify-center text-[11px]">3</span>
          <span className="font-semibold text-cyan-400">3. MITIGATION APPLIED</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-6 h-6 rounded-full bg-emerald-500 text-slate-950 font-bold flex items-center justify-center text-[11px]">4</span>
          <span className="font-semibold text-emerald-400">4. RECOVERED & CLEARED</span>
        </div>
      </div>

      {/* Live / History tab switcher — kept visually distinct so a
          persisted historical alert is never mistaken for an active one,
          or vice versa (Pass 6 requirement). */}
      <div className="scada-panel p-1.5 flex items-center gap-1.5">
        <button
          onClick={() => setActiveTab('live')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs font-mono font-bold transition ${
            activeTab === 'live'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
              : 'text-slate-400 hover:bg-slate-800 border border-transparent'
          }`}
        >
          <Radio className="w-3.5 h-3.5" /> LIVE ALERTS ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded text-xs font-mono font-bold transition ${
            activeTab === 'history'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
              : 'text-slate-400 hover:bg-slate-800 border border-transparent'
          }`}
        >
          <History className="w-3.5 h-3.5" /> ALERT HISTORY
        </button>
      </div>

      {activeTab === 'history' && (
        <div className="space-y-3">
          <div className="scada-panel p-2.5 text-[11px] font-mono text-slate-400 flex items-center gap-2">
            <History className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            Persisted alert record for <span className="text-cyan-400 font-bold">{activeWellId}</span> — this
            reflects everything saved to the shared database, including from earlier sessions, not just alerts
            raised during this browser session.
          </div>

          {historyState === 'loading' && (
            <div className="scada-panel p-8 text-center text-slate-400 text-xs font-mono flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading alert history…
            </div>
          )}

          {historyState === 'not_configured' && (
            <div className="scada-panel p-8 text-center space-y-2">
              <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
              <div className="text-sm font-bold text-slate-200 font-mono">Alert history is not enabled in this environment</div>
              <div className="text-xs text-slate-400 font-mono">
                No shared database is configured, so persisted alert history cannot be recorded or retrieved here.
              </div>
            </div>
          )}

          {historyState === 'unavailable' && (
            <div className="scada-panel p-8 text-center space-y-3">
              <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
              <div className="text-sm font-bold text-slate-200 font-mono">Alert history is temporarily unavailable</div>
              <div className="text-xs text-slate-400 font-mono">
                The shared database could not be reached. This does not mean the history is empty — try again shortly.
              </div>
              <button
                onClick={loadHistory}
                className="mx-auto flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-mono transition"
              >
                <RotateCcw className="w-3.5 h-3.5" /> RETRY
              </button>
            </div>
          )}

          {historyState === 'ok' && historyAlerts.length === 0 && (
            <div className="scada-panel p-8 text-center space-y-2">
              <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto" />
              <div className="text-sm font-bold text-slate-200 font-mono">No recorded alerts for this well yet</div>
              <div className="text-xs text-slate-400 font-mono">
                Nothing has been persisted to the shared alert history for this well.
              </div>
            </div>
          )}

          {historyState === 'ok' && historyAlerts.length > 0 && (
            <div className="space-y-2">
              {historyAlerts.map((alert) => (
                <div key={alert.alert_id} className="scada-panel p-3 border border-slate-800 rounded-lg space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                          alert.severity === 'CRITICAL'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : alert.severity === 'WARNING'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-slate-800 text-slate-300 border border-slate-700'
                        }`}
                      >
                        {alert.severity} — {alert.hazard_type}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">{alert.alert_id}</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(alert.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="text-xs text-slate-300 font-sans">{alert.headline}</div>
                  <div className="text-[10px] font-mono text-slate-500">STATUS: {alert.status}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Active Alerts List */}
      {activeTab === 'live' && (
      <div className="space-y-4">
        {alerts.length > 0 ? (
          alerts.map((alert) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isWarning = alert.severity === 'WARNING';
            const isCleared = alert.severity === 'CLEARED';
            const isAcked = acknowledgedAlerts[alert.alert_id] || alert.status === 'ACKNOWLEDGED';

            const borderClass = isCleared
              ? 'border-emerald-500/50 bg-[#0d1614]'
              : isCritical
              ? 'border-rose-500/50 bg-[#1a0f14]'
              : 'border-amber-500/50 bg-[#19150d]';

            return (
              <div key={alert.alert_id} className={`scada-panel p-4 border-2 rounded-lg space-y-4 ${borderClass}`}>
                {/* Alert Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
                  <div className="flex items-center space-x-2.5">
                    <span
                      className={`text-xs font-mono px-2.5 py-0.5 rounded font-bold uppercase ${
                        isCleared
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : isCritical
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      }`}
                    >
                      {alert.severity} — {alert.hazard_type}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      ID: {alert.alert_id} | Depth: {alert.measured_depth_m.toFixed(1)}m | Formation: {alert.formation}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{new Date(alert.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>

                {/* Headline & Causal Evidence Chain */}
                <div className="space-y-2">
                  <div className="text-base font-bold text-slate-100">{alert.headline}</div>
                  <div className="p-3 bg-slate-900/90 border border-slate-800 rounded space-y-1 font-mono text-xs">
                    <div className="text-slate-400 text-[10px] uppercase font-bold flex items-center gap-1.5">
                      <Zap className="w-3 h-3 text-cyan-400" />
                      GROUNDED CAUSAL EVIDENCE CHAIN:
                    </div>
                    {alert.causal_evidence_chain && alert.causal_evidence_chain.length > 0 ? (
                      alert.causal_evidence_chain.map((evidence, idx) => (
                        <div key={idx} className="text-slate-300 flex items-start gap-2">
                          <span className="text-cyan-400 font-bold">›</span>
                          <span>{evidence}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-400">Telemetry deviation exceeds physical safe drilling margin.</div>
                    )}
                  </div>
                </div>

                {/* Recommended SPE/IADC Action Card */}
                {alert.recommended_action && (
                  <div className="p-3.5 bg-slate-900/95 border border-cyan-500/30 rounded-lg space-y-2 font-mono">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-bold text-cyan-300 flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-cyan-400" />
                        RECOMMENDED DRILLING INTERVENTION: {alert.recommended_action.title}
                      </div>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold">
                        URGENCY: {alert.recommended_action.urgency}
                      </span>
                    </div>

                    <ol className="list-decimal list-inside text-xs text-slate-300 space-y-1 pl-1">
                      {alert.recommended_action.steps.map((step, idx) => (
                        <li key={idx} className="leading-relaxed">
                          <span className="text-slate-200">{step}</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Human-In-The-Loop Action Bar */}
                <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800">
                  <div className="flex items-center space-x-2 text-xs font-mono">
                    <span className="text-slate-400">STATUS:</span>
                    <span className={`font-bold ${isCleared ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {alert.status}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 font-mono text-xs">
                    {!isAcked && !isCleared && (
                      <button
                        onClick={() => handleAcknowledge(alert.alert_id)}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition"
                      >
                        ACKNOWLEDGE
                      </button>
                    )}

                    {!isCleared && (
                      <button
                        disabled={mitigatingId === alert.alert_id}
                        onClick={() => handleMitigate(alert.alert_id)}
                        className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded shadow-md shadow-emerald-600/30 transition flex items-center gap-1.5"
                      >
                        {mitigatingId === alert.alert_id ? (
                          <span>APPLYING SETPOINTS...</span>
                        ) : (
                          <>
                            <CheckCircle className="w-4 h-4 stroke-[2.5]" />
                            <span>EXECUTE MITIGATION</span>
                          </>
                        )}
                      </button>
                    )}

                    {isCleared && (
                      <span className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded flex items-center gap-1.5">
                        <CheckCircle className="w-4 h-4" /> RECOVERED & CLEARED
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="scada-panel p-8 text-center space-y-2">
            <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto" />
            <div className="text-sm font-bold text-slate-200 font-mono">NO ACTIVE DRILLING HAZARD ALERTS</div>
            <div className="text-xs text-slate-400 font-mono">
              Drilling parameters, annular hydraulics, and mechanical torques remain within safe operational bounds.
            </div>
          </div>
        )}
      </div>
      )}
    </div>
  );
};
