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
  // User Persona / Role (Field vs Office)
  userRole: 'field' | 'office';
  setUserRole: (role: 'field' | 'office') => void;
  // eRTMAC WITSML Stream Integration
  ertmacStatus: any;
  ertmacSources: Array<{ id: string; name: string; well_id: string; stations: number; description: string }>;
  selectedErtmacSource: string;
  setErtmacSource: (source: string, wellId?: string) => Promise<void>;
  ertmacLeadTime: any;
  refreshErtmacStatus: () => Promise<void>;
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

// Physics digital twin WebSocket stream, served by the unified backend
// (Backend/app/main.py) at /api/v3/physics/stream -- same origin as every
// other API call (see services/api.ts), just with ws:// instead of http://.
//
// The native WebSocket constructor cannot set the X-API-Key header every
// other request uses, so the backend accepts the same shared key as a
// `?api_key=` query parameter for this one route (see
// modules/04_physics_engine/api/server.py's physics_stream()) -- reusing
// VITE_API_KEY, the same value api.ts already sends as a header elsewhere,
// not a new secret. Never log the returned URL (it would put the key in
// plain sight in the browser console/network panel more visibly than a
// header does).
const telemetryWsUrl = () => {
  const override = import.meta.env.VITE_TELEMETRY_WS_URL as string | undefined;
  const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) || 'http://localhost:8000';
  const wsBase = override || `${apiBase.replace(/^http/, 'ws')}/api/v3/physics/stream`;
  const key = import.meta.env.VITE_API_KEY as string | undefined;
  if (!key) return wsBase;
  return `${wsBase}${wsBase.includes('?') ? '&' : '?'}api_key=${encodeURIComponent(key)}`;
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
  // Default to a real Upper Assam well, not the Volve North Sea well
  // (15/9-F-12) — that well's coordinates sit over open ocean, so every
  // map view defaulted to a dark, featureless patch of sea with no land
  // basemap detail on first load, confirmed by a user screenshot. WELL-
  // HGJ-012 is this project's own designated live-simulation well (its
  // well_id is telemetry_stream.json's own `active_well_id`, with the
  // only full 3600-record synthetic telemetry stream in the testbed), so
  // it also means the Dashboard/Command Center/Live Drilling pages show
  // real moving telemetry immediately instead of an empty state.
  const [activeWellId, setActiveWellId] = useState<string>('WELL-HGJ-012');
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

  // User Role (Field vs Office)
  const [userRole, setUserRoleState] = useState<'field' | 'office'>(() => {
    try {
      return (localStorage.getItem('nwis.user_role') as 'field' | 'office') || 'field';
    } catch {
      return 'field';
    }
  });

  const setUserRole = (role: 'field' | 'office') => {
    setUserRoleState(role);
    try {
      localStorage.setItem('nwis.user_role', role);
    } catch {}
  };

  // eRTMAC Stream State
  const [ertmacStatus, setErtmacStatus] = useState<any>(null);
  const [ertmacSources, setErtmacSources] = useState<Array<{ id: string; name: string; well_id: string; stations: number; description: string }>>([
    { id: 'physics_twin', name: 'Physics Digital Twin (HGJ-012)', well_id: 'WELL-HGJ-012', stations: 3600, description: 'Coupled hydraulic-mechanical drilling simulation' },
    { id: 'volve_witsml_f12', name: 'Equinor Volve 15/9-F-12 (Real WITSML Feed)', well_id: 'NO-15/9-F-12', stations: 438, description: 'Real Equinor North Sea production well WITSML log replay' },
    { id: 'volve_witsml_f1', name: 'Equinor Volve 15/9-F-1 (Real WITSML Feed)', well_id: 'NO-15/9-F-1', stations: 110, description: 'Real Equinor North Sea exploration well WITSML trajectory replay' },
  ]);
  const [selectedErtmacSource, setSelectedErtmacSource] = useState<string>('physics_twin');
  const [ertmacLeadTime, setErtmacLeadTime] = useState<any>(null);

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
        // The call succeeding is what proves the backend is reachable --
        // not the row count. Gating isBackendOnline on length > 0 (as this
        // did) left the flag stuck at false whenever the store legitimately
        // answered with an empty list, which is a different condition from
        // an outage and should not be reported as one.
        setWells(wellsData ?? []);
        setIsBackendOnline(true);
      } catch (err) {
        console.warn('Backend not responding yet; retrying in background...', err);
        setIsBackendOnline(false);
      }

      // Load eRTMAC sources and initial status
      try {
        const srcRes = await api.getErtmacSources();
        if (srcRes?.sources) {
          setErtmacSources(srcRes.sources);
          setSelectedErtmacSource(srcRes.active_source || 'physics_twin');
        }
        const statusRes = await api.getErtmacStatus();
        if (statusRes) {
          setErtmacStatus(statusRes);
        }
      } catch (e) {
        // eRTMAC optional on initial boot
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
  const startSim = async () => {
    await api.startSim();
    setSimStatus((prev) => prev ? { ...prev, is_running: true } : null);
  };

  const pauseSim = async () => {
    await api.pauseSim();
    setSimStatus((prev) => prev ? { ...prev, is_running: false } : null);
  };

  const stepSim = async () => {
    const stepData = await api.stepSim();
    if (stepData) {
      handleNewTelemetry(stepData);
    }
  };

  const resetSim = async (initialMd?: number) => {
    await api.resetSim(initialMd || 2500.0);
    setTelemetryHistory([]);
    refreshAlerts();
  };

  const setSimSpeed = async (speed: number) => {
    await api.setSimSpeed(speed);
    setSimStatus((prev) => prev ? { ...prev, speed_multiplier: speed } : null);
  };

  const injectScenario = async (scenario: string, severity: number = 1.0) => {
    await api.injectScenario(scenario, severity);
    const status = await api.getSimStatus();
    if (status) setSimStatus(status);
  };

  const clearScenarios = async () => {
    await api.clearScenarios();
    const status = await api.getSimStatus();
    if (status) setSimStatus(status);
  };

  const refreshErtmacStatus = useCallback(async () => {
    try {
      const [status, leadTime] = await Promise.all([
        api.getErtmacStatus(),
        api.getErtmacLeadTime(),
      ]);
      if (status) {
        setErtmacStatus(status);
        if (status.source) setSelectedErtmacSource(status.source);
      }
      if (leadTime) setErtmacLeadTime(leadTime);
    } catch (e) {
      // ignore
    }
  }, []);

  const setErtmacSource = async (source: string, wellId?: string) => {
    try {
      await api.selectErtmacSource(source, wellId);
      setSelectedErtmacSource(source);
      await refreshErtmacStatus();
      await refreshAlerts();
    } catch (e) {
      console.error('Failed to switch eRTMAC source', e);
    }
  };

  const mitigateAlert = async (alertId: string) => {
    await api.mitigateAlert(activeWellId, alertId);
    await refreshAlerts();
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
        userRole,
        setUserRole,
        ertmacStatus,
        ertmacSources,
        selectedErtmacSource,
        setErtmacSource,
        ertmacLeadTime,
        refreshErtmacStatus,
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
