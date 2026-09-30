/**
 * App-wide state: active well, backend status, the live depth stream
 * (Server-Sent Events from /live/replay), the alert list, and the evidence viewer.
 *
 * The live stream is the demo stand-in for eRTMAC: the backend replays the
 * active well's trajectory depth-by-depth and runs the full analysis at each
 * step. Swapping in a real eRTMAC feed only changes the backend adapter; this
 * provider consumes the same event shape.
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, type Alert, type ReplayTick, type Well } from '../lib/api';

type Evidence = { doc: string; page?: number | null; title?: string; subtitle?: string };

interface ReplayState {
  status: 'idle' | 'running' | 'finished' | 'error';
  tick: ReplayTick | null;
  history: { depth: number; risk: string }[];
  startDepth: number;
  endDepth: number;
  error?: string;
}

interface Toast { id: string; title: string; body: string; severity: string }

interface Ctx {
  online: boolean | null;
  wells: Well[];
  activeWellId: string;
  activeWell?: Well;
  setActiveWellId: (id: string) => void;
  replay: ReplayState;
  startReplay: (opts?: { start?: number; end?: number; ticks?: number; tickSeconds?: number; reset?: boolean }) => void;
  stopReplay: () => void;
  bitDepth: number | null;
  alerts: Alert[];
  activeAlerts: number;
  refreshAlerts: () => Promise<void>;
  evidence: Evidence | null;
  openEvidence: (e: Evidence) => void;
  closeEvidence: () => void;
  toasts: Toast[];
  dismissToast: (id: string) => void;
}

const NwisContext = createContext<Ctx | null>(null);
const LS_KEY = 'nwis.activeWell';

const readLS = (k: string) => {
  try { return localStorage.getItem(k); } catch { return null; }
};
const writeLS = (k: string, v: string) => {
  try { localStorage.setItem(k, v); } catch { /* storage unavailable */ }
};

export const NwisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [online, setOnline] = useState<boolean | null>(null);
  const [wells, setWells] = useState<Well[]>([]);
  const [activeWellId, setActiveWellIdState] = useState<string>(readLS(LS_KEY) || '');
  const [replay, setReplay] = useState<ReplayState>({ status: 'idle', tick: null, history: [], startDepth: 0, endDepth: 0 });
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const esRef = useRef<EventSource | null>(null);
  const seenAlerts = useRef<Set<string>>(new Set());

  // Boot: health + wells, retrying until the backend answers.
  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const boot = async () => {
      try {
        const [h, ws] = await Promise.all([api.health(), api.wells()]);
        if (cancelled) return;
        setWells(ws);
        setOnline(true);
        setActiveWellIdState((cur) => (cur && ws.some((w) => w.well_id === cur) ? cur : h.data_store.active_well_id || ws[0]?.well_id || ''));
      } catch {
        if (cancelled) return;
        setOnline(false);
        timer = window.setTimeout(boot, 3000);
      }
    };
    boot();
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, []);

  const setActiveWellId = useCallback((id: string) => {
    setActiveWellIdState(id);
    writeLS(LS_KEY, id);
  }, []);

  const refreshAlerts = useCallback(async () => {
    try {
      const r = await api.alerts();
      setAlerts(r.alerts);
      r.alerts.forEach((a) => seenAlerts.current.add(a.alert_id));
    } catch { /* offline — keep last list */ }
  }, []);

  useEffect(() => {
    if (!online) return;
    refreshAlerts();
    const t = window.setInterval(refreshAlerts, 6000);
    return () => window.clearInterval(t);
  }, [online, refreshAlerts]);

  const stopReplay = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setReplay((r) => (r.status === 'running' ? { ...r, status: 'idle' } : r));
  }, []);

  const startReplay = useCallback<Ctx['startReplay']>(async (opts = {}) => {
    const well = wells.find((w) => w.well_id === activeWellId);
    if (!well) return;
    esRef.current?.close();
    const start = opts.start ?? Math.max(0, Math.round(well.total_depth_md_m * 0.85));
    const end = opts.end ?? well.total_depth_md_m;
    if (opts.reset !== false) {
      try { await api.clearAlerts(well.well_id); } catch { /* ignore */ }
      seenAlerts.current = new Set();
      setAlerts((a) => a.filter((x) => x.well_id !== well.well_id));
    }
    setReplay({ status: 'running', tick: null, history: [], startDepth: start, endDepth: end });
    const es = new EventSource(api.replayUrl(well.well_id, { start, end, ticks: opts.ticks ?? 60, tickSeconds: opts.tickSeconds ?? 0.9 }));
    esRef.current = es;
    es.onmessage = (ev) => {
      const tick = JSON.parse(ev.data) as ReplayTick;
      setReplay((r) => ({ ...r, tick, history: [...r.history, { depth: tick.depth_m, risk: tick.overall_risk_level }] }));
      const fresh = tick.alerts.filter((a) => !seenAlerts.current.has(a.alert_id));
      if (fresh.length) {
        fresh.forEach((a) => seenAlerts.current.add(a.alert_id));
        setToasts((t) => [...t, ...fresh.map((a) => ({ id: a.alert_id, title: a.title, body: a.message, severity: a.severity }))].slice(-3));
        refreshAlerts();
      }
    };
    es.addEventListener('done', () => {
      es.close();
      setReplay((r) => ({ ...r, status: 'finished' }));
      refreshAlerts();
    });
    es.addEventListener('error', () => {
      if (es.readyState === EventSource.CLOSED) return;
      es.close();
      setReplay((r) => (r.status === 'running' ? { ...r, status: 'error', error: 'Live stream interrupted' } : r));
    });
  }, [wells, activeWellId, refreshAlerts]);

  // Changing the active well stops a stream that belongs to the previous one.
  useEffect(() => { stopReplay(); setReplay({ status: 'idle', tick: null, history: [], startDepth: 0, endDepth: 0 }); }, [activeWellId, stopReplay]);
  useEffect(() => () => esRef.current?.close(), []);

  const dismissToast = useCallback((id: string) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  useEffect(() => {
    if (!toasts.length) return;
    const t = window.setTimeout(() => setToasts((x) => x.slice(1)), 7000);
    return () => window.clearTimeout(t);
  }, [toasts]);

  const value = useMemo<Ctx>(() => ({
    online,
    wells,
    activeWellId,
    activeWell: wells.find((w) => w.well_id === activeWellId),
    setActiveWellId,
    replay,
    startReplay,
    stopReplay,
    bitDepth: replay.tick?.depth_m ?? null,
    alerts,
    activeAlerts: alerts.filter((a) => a.status === 'ACTIVE').length,
    refreshAlerts,
    evidence,
    openEvidence: setEvidence,
    closeEvidence: () => setEvidence(null),
    toasts,
    dismissToast,
  }), [online, wells, activeWellId, setActiveWellId, replay, startReplay, stopReplay, alerts, refreshAlerts, evidence, toasts, dismissToast]);

  return <NwisContext.Provider value={value}>{children}</NwisContext.Provider>;
};

export const useNwis = () => {
  const ctx = useContext(NwisContext);
  if (!ctx) throw new Error('useNwis must be used inside NwisProvider');
  return ctx;
};

/** Small fetch hook with loading / error / reload, keyed by deps. */
export function useLoad<T>(fn: () => Promise<T>, deps: React.DependencyList) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    fn().then(
      (d) => { if (alive) { setData(d); setLoading(false); } },
      (e) => { if (alive) { setError(e?.message || 'Request failed'); setLoading(false); } },
    );
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);
  return { data, error, loading, reload: () => setNonce((x) => x + 1), setData };
}
