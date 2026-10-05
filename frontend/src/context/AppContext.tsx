import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { Well, TelemetryData, RiskEvaluation, AlertAdvisory, SimulationStatus } from '../types';
import { api } from '../services/api';

interface AppContextType {
  activeWellId: string;
  setActiveWellId: (id: string) => void;
  wells: Well[];
  activeWell: Well | undefined;
  activeDepth: number;
  setActiveDepth: (depth: number) => void;
  telemetry: TelemetryData | null;
  telemetryHistory: TelemetryData[];
  activeRisk: RiskEvaluation | null;
  alerts: AlertAdvisory[];
  simStatus: SimulationStatus | null;
  isBackendOnline: boolean;
  isWsConnected: boolean;
  telemetryRateHz: number;
  telemetryLatencyMs: number | null;
  // Control actions
  startSim: () => Promise<void>;
  pauseSim: () => Promise<void>;
  stepSim: () => Promise<void>;
  resetSim: (initialMd?: number) => Promise<void>;
  setSimSpeed: (speed: number) => Promise<void>;
  injectScenario: (scenario: string, severity?: number) => Promise<void>;
  clearScenarios: () => Promise<void>;
  mitigateAlert: (alertId: string) => Promise<void>;
  refreshAlerts: () => Promise<void>;
}

const AppContext = createContext<AppContextType | null>(null);

const HISTORY_SIZE = 250; // ~10 s of trace at 25 Hz

// NOT YET WIRED: the physics digital twin / predictive engine
// (modules/04_physics_engine, modules/05_predictive_analytics) has no
// FastAPI/WebSocket routes exposed yet — see services/api.ts's "MODULE 03"
// section (named after this feature area, not after either module's real
// folder number). This URL points at a placeholder base (VITE_M03_API_BASE,
// default http://localhost:8003) so the connect attempt below fails cleanly
// (caught by ws.onerror -> reconnect loop) instead of pointing at a backend
// that doesn't exist in this project at all. Update the path once a real
// telemetry stream endpoint ships.
const telemetryWsUrl = () => {
  const override = import.meta.env.VITE_TELEMETRY_WS_URL as string | undefined;
  if (override) return override;
  const m03Base = (import.meta.env.VITE_M03_API_BASE as string | undefined) || 'http://localhost:8003';
  const wsBase = m03Base.replace(/^http/, 'ws');
  return `${wsBase}/api/v3/physics/stream`;
};

const DEFAULT_TELEMETRY: TelemetryData = {
  timestamp: new Date().toISOString(),
  measured_depth_m: 2450.0,
  tvd_m: 2435.2,
  tvdss_m: 2315.6,
  formation: 'Porous_Sandstone',
  xi: 0.25,
  rop_m_hr: 12.4,
  wob_kn: 120.0,
  rpm: 110.0,
  torque_knm: 14.5,
  flow_in_lpm: 2200.0,
  flow_out_lpm: 2195.0,
  delta_flow: -5.0,
  standpipe_pressure_bar: 185.0,
  bottomhole_pressure_bar: 242.0,
  pore_pressure_bar: 225.0,
  fracture_pressure_bar: 260.0,
  ecd_gcc: 1.29,
  pit_volume_m3: 45.2,
  pit_volume_rate_m3_min: 0.0,
  mse_mpa: 118.0,
  stick_slip_index: 0.12,
  overpull_kn: 0.0,
  cuttings_concentration: 0.02,
  quality: 'GOOD',
  provenance: 'SYNTHETIC',
};

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeWellId, setActiveWellId] = useState<string>('15/9-F-12');
  const [wells, setWells] = useState<Well[]>([]);
  const [activeDepth, setActiveDepth] = useState<number>(2450.0);
  const [telemetry, setTelemetry] = useState<TelemetryData>(DEFAULT_TELEMETRY);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryData[]>([]);
  const [activeRisk, setActiveRisk] = useState<RiskEvaluation | null>(null);
  const [alerts, setAlerts] = useState<AlertAdvisory[]>([]);
  const [simStatus, setSimStatus] = useState<SimulationStatus | null>({
    is_running: false,
    speed_multiplier: 1.0,
    sim_time_s: 0,
    measured_depth_m: 2450.0,
    active_scenarios: {},
  });
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(false);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);
  const [telemetryRateHz, setTelemetryRateHz] = useState<number>(0);
  const [telemetryLatencyMs, setTelemetryLatencyMs] = useState<number | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const frameCountRef = useRef(0);
  const lastLatencyRef = useRef<number | null>(null);
  const lastEvalAtRef = useRef(0);

  useEffect(() => {
    const t = setInterval(() => {
      setTelemetryRateHz(frameCountRef.current);
      setTelemetryLatencyMs(lastLatencyRef.current);
      frameCountRef.current = 0;
    }, 1000);
    return () => clearInterval(t);
  }, []);

  // 1. Initial Load: Wells & Initial Health
  useEffect(() => {
    const initData = async () => {
      try {
        const wellsData = await api.getWells();
        if (wellsData && wellsData.length > 0) {
          setWells(wellsData);
          setIsBackendOnline(true);
        }
      } catch (err) {
        console.warn('Backend not responding yet; retrying in background...', err);
        setIsBackendOnline(false);
      }
    };
    initData();
  }, []);

  // 2. Fetch Active Well Alerts
  const refreshAlerts = useCallback(async () => {
    try {
      const alertList = await api.getAlerts(activeWellId);
      if (alertList && Array.isArray(alertList) && alertList.length > 0) {
        setAlerts(alertList.slice(0, 30));
      }
    } catch (err) {
      // Backend might be offline
    }
  }, [activeWellId]);

  useEffect(() => {
    refreshAlerts();
    const alertInterval = setInterval(refreshAlerts, 5000); // alerts from ML eval; 5s is fine
    return () => clearInterval(alertInterval);
  }, [refreshAlerts]);

  // Normalize telemetry: accepts both flat TelemetryData and nested TelemetryEnvelope
  const normalizeTelemetry = useCallback((raw: any): TelemetryData | null => {
    if (!raw || typeof raw !== 'object') return null;

    // Flat TelemetryData: has measured_depth_m AND rop_m_hr at top level
    if (raw.measured_depth_m !== undefined && raw.rop_m_hr !== undefined) {
      return raw as TelemetryData;
    }

    // Nested TelemetryEnvelope: has depth.md_m and channels.rop_m_hr
    const ch = raw.channels || {};
    const dep = raw.depth || {};
    const fm = raw.formation || {};
    if (dep.md_m === undefined && ch.rop_m_hr === undefined) return null;

    const bhp = ch.bhp_bar ?? ch.bottomhole_pressure_bar ?? 0;
    const ppMargin = ch.pp_margin_bar;
    const fgMargin = ch.fg_margin_bar;

    return {
      timestamp: typeof raw.timestamp === 'string' ? raw.timestamp : new Date().toISOString(),
      sim_time_s: raw.simulation_time_s,
      measured_depth_m: dep.md_m ?? 2450,
      tvd_m: dep.tvd_m ?? 2435,
      tvdss_m: dep.tvdss_m ?? 2315,
      formation: (typeof fm === 'object' ? fm.name : fm) ?? 'Unknown',
      xi: typeof fm === 'object' ? (fm.xi ?? 0.0) : 0.0,
      rop_m_hr: ch.rop_m_hr ?? 0,
      wob_kn: ch.wob_kn ?? 0,
      rpm: ch.rpm ?? 0,
      torque_knm: ch.torque_kn_m ?? ch.torque_knm ?? 0,
      flow_in_lpm: ch.flow_in_lpm ?? 0,
      flow_out_lpm: ch.flow_out_lpm ?? 0,
      delta_flow: (ch.flow_out_lpm ?? 0) - (ch.flow_in_lpm ?? 0),
      standpipe_pressure_bar: ch.standpipe_pressure_bar ?? 0,
      bottomhole_pressure_bar: bhp,
      pore_pressure_bar: ppMargin != null ? bhp - ppMargin : ch.pore_pressure_bar ?? 0,
      fracture_pressure_bar: fgMargin != null ? bhp + fgMargin : ch.fracture_pressure_bar ?? 0,
      ecd_gcc: ch.ecd_gcc ?? 0,
      pit_volume_m3: ch.pit_volume_m3 ?? 0,
      pit_volume_rate_m3_min: 0,
      mse_mpa: ch.mse_mpa ?? 0,
      stick_slip_index: ch.stick_slip_index ?? 0,
      overpull_kn: ch.overpull_kn ?? 0,
      cuttings_concentration: ch.cuttings_concentration ?? 0,
      quality: (raw.quality?.overall ?? 1) > 0.7 ? 'GOOD' : 'DEGRADED',
      provenance: raw.provenance?.tier ?? 'SYNTHETIC',
    };
  }, []);

  // 3. Process new telemetry packet — hot path, must be non-blocking
  const handleNewTelemetry = useCallback((rawData: any) => {
    const data = normalizeTelemetry(rawData);
    if (!data) return;

    frameCountRef.current += 1;
    const sentAt = Date.parse(data.timestamp);
    if (!Number.isNaN(sentAt)) lastLatencyRef.current = Math.max(0, Date.now() - sentAt);

    setTelemetry(data);
    setActiveDepth(data.measured_depth_m);
    setTelemetryHistory((prev) => {
      const next = [...prev, data];
      return next.length > HISTORY_SIZE ? next.slice(next.length - HISTORY_SIZE) : next;
    });

    // ML risk evaluation at ~1 Hz; the stream runs at 25 Hz and the model doesn't need every frame.
    const now = Date.now();
    if (now - lastEvalAtRef.current < 1000) return;
    lastEvalAtRef.current = now;

    // Send the original nested envelope (rawData): the backend feature engine expects TelemetryEnvelope shape.
    api.evaluateTelemetry(rawData).then((risk) => {
      if (!risk) return;
      setActiveRisk(risk);
      if (risk.alerts && risk.alerts.length > 0) {
        setAlerts((prev) => {
          const combined = [...risk.alerts!, ...prev.filter(a => !risk.alerts!.some(ra => ra.alert_id === a.alert_id))];
          return combined.slice(0, 30);
        });
      }
    }).catch(() => { /* evaluateTelemetry failure is non-fatal */ });
  }, [normalizeTelemetry]);

  // 4. WebSocket Streaming Connection
  useEffect(() => {
    let cancelled = false;
    let reconnectTimeout: any = null;
    let currentWs: WebSocket | null = null;

    const connectWs = () => {
      if (cancelled) return;

      const wsUrl = telemetryWsUrl();

      try {
        const ws = new WebSocket(wsUrl);
        currentWs = ws;
        wsRef.current = ws;

        ws.onopen = () => {
          if (cancelled || ws !== currentWs) return;
          setIsWsConnected(true);
          setIsBackendOnline(true);
        };

        ws.onmessage = (event) => {
          if (cancelled || ws !== currentWs) return;
          try {
            const packet = JSON.parse(event.data);
            // Backend sends raw telemetry dict OR {telemetry: {...}}
            if (packet && packet.telemetry) {
              handleNewTelemetry(packet.telemetry);
            } else if (packet && (packet.channels || packet.depth || packet.measured_depth_m !== undefined)) {
              handleNewTelemetry(packet);
            }
          } catch (e) {
            // Non-fatal — ignore parse errors on WS ping/pong frames
          }
        };

        ws.onclose = () => {
          if (ws !== currentWs) return; // superseded by a newer socket; ignore
          if (cancelled) return;
          setIsWsConnected(false);
          reconnectTimeout = setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          if (ws !== currentWs) return;
          if (cancelled) return;
          setIsWsConnected(false);
          ws.close();
        };
      } catch (err) {
        if (cancelled) return;
        setIsWsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    };

    connectWs();

    return () => {
      cancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (currentWs) {
        // Detach handlers before closing so a still-CONNECTING socket
        // doesn't fire onclose/onerror into a torn-down effect (StrictMode
        // double-invokes this effect in dev, which raced the reconnect logic).
        currentWs.onopen = null;
        currentWs.onmessage = null;
        currentWs.onclose = null;
        currentWs.onerror = null;
        currentWs.close();
      }
    };
  }, [handleNewTelemetry]);

  // 5. Unified background poller (status every 2s; historian fallback only when WS is down)
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const status = await api.getSimStatus();
        if (status) {
          // Normalize: backend returns {md_m, sim_time_s, ...}, frontend expects {measured_depth_m, ...}
          setSimStatus({
            is_running: status.is_running ?? false,
            speed_multiplier: status.speed_multiplier ?? 1.0,
            sim_time_s: (status as any).sim_time_s ?? 0,
            measured_depth_m: (status as any).md_m ?? (status as any).measured_depth_m ?? 2450,
            active_scenarios: (status as any).active_scenarios ?? {},
          });
          setIsBackendOnline(true);
        }
      } catch {
        setIsBackendOnline(false);
      }

      // Historian fallback: only if WebSocket is not delivering frames
      if (!isWsConnected) {
        try {
          const hist = await api.getHistorian(1);
          if (hist && hist.length > 0) {
            handleNewTelemetry(hist[hist.length - 1]);
          }
        } catch { /* offline */ }
      }
    };

    pollStatus();
    const interval = setInterval(pollStatus, 2000);
    return () => clearInterval(interval);
  }, [isWsConnected, handleNewTelemetry]);

  // Simulator Actions
  //
  // All seven of these call modules/04_physics_engine's simulator routes,
  // which this project's backend never actually serves (see the
  // telemetryWsUrl comment above) -- so every call here was rejecting
  // silently with no try/catch, leaving every Simulator/Live-Drilling/
  // Alerts button looking like it did nothing when clicked. Each one now
  // short-circuits when isBackendOnline is false (skips a network call
  // already known to fail) and swallows a genuine failure instead of
  // throwing an unhandled rejection. UI components should still prefer
  // disabling these controls via isBackendOnline rather than relying on
  // this catch -- this is a safety net, not a substitute for an honest
  // disabled state.
  const startSim = async () => {
    if (!isBackendOnline) return;
    try {
      await api.startSim();
      setSimStatus((prev) => prev ? { ...prev, is_running: true } : null);
    } catch { /* physics backend unreachable */ }
  };

  const pauseSim = async () => {
    if (!isBackendOnline) return;
    try {
      await api.pauseSim();
      setSimStatus((prev) => prev ? { ...prev, is_running: false } : null);
    } catch { /* physics backend unreachable */ }
  };

  const stepSim = async () => {
    if (!isBackendOnline) return;
    try {
      const stepData = await api.stepSim();
      if (stepData) {
        handleNewTelemetry(stepData);
      }
    } catch { /* physics backend unreachable */ }
  };

  const resetSim = async (initialMd?: number) => {
    if (!isBackendOnline) return;
    try {
      await api.resetSim(initialMd || 2500.0);
      setTelemetryHistory([]);
      refreshAlerts();
    } catch { /* physics backend unreachable */ }
  };

  const setSimSpeed = async (speed: number) => {
    if (!isBackendOnline) return;
    try {
      await api.setSimSpeed(speed);
      setSimStatus((prev) => prev ? { ...prev, speed_multiplier: speed } : null);
    } catch { /* physics backend unreachable */ }
  };

  const injectScenario = async (scenario: string, severity: number = 1.0) => {
    if (!isBackendOnline) return;
    try {
      await api.injectScenario(scenario, severity);
      const status = await api.getSimStatus();
      if (status) setSimStatus(status);
    } catch { /* physics backend unreachable */ }
  };

  const clearScenarios = async () => {
    if (!isBackendOnline) return;
    try {
      await api.clearScenarios();
      const status = await api.getSimStatus();
      if (status) setSimStatus(status);
    } catch { /* physics backend unreachable */ }
  };

  const mitigateAlert = async (alertId: string) => {
    if (!isBackendOnline) return;
    try {
      await api.mitigateAlert(activeWellId, alertId);
      await refreshAlerts();
    } catch { /* physics backend unreachable */ }
  };

  const activeWell = wells.find((w) => w.well_id === activeWellId);

  return (
    <AppContext.Provider
      value={{
        activeWellId,
        setActiveWellId,
        wells,
        activeWell,
        activeDepth,
        setActiveDepth,
        telemetry,
        telemetryHistory,
        activeRisk,
        alerts,
        simStatus,
        isBackendOnline,
        isWsConnected,
        telemetryRateHz,
        telemetryLatencyMs,
        startSim,
        pauseSim,
        stepSim,
        resetSim,
        setSimSpeed,
        injectScenario,
        clearScenarios,
        mitigateAlert,
        refreshAlerts,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
