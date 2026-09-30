import React, { useEffect, useRef, useState } from 'react';
import { Pause, Play, RotateCcw, Zap } from 'lucide-react';
import { api } from '../lib/api';
import { n, sevOf } from '../lib/format';
import { Button, Empty, PageHeader, Panel, PanelHead, SeverityTag, cx } from '../ui/primitives';

/**
 * Rig sensors: the physics digital twin streams WITS-style channels over a
 * WebSocket (stand-in for the eRTMAC real-time feed); every second the latest
 * frame goes through the predictive engine (rules + anomaly detector + model +
 * offset history), which raises alerts from sensor behaviour alone.
 */

type Frame = {
  t: number; md: number; formation: string;
  flowIn: number; flowOut: number; pit: number; spp: number; torque: number; hookload: number; overpull: number;
  ecd: number; ppMargin: number; fgMargin: number; rop: number; stickSlip: number;
};

const SCENARIOS = [
  { id: 'LOST_CIRCULATION', label: 'Lost circulation', hint: 'Mud flows into a fracture: returns drop, pit falls' },
  { id: 'KICK_OVERPRESSURE', label: 'Kick', hint: 'Formation fluid enters: returns rise, pit gains' },
  { id: 'STUCK_PIPE', label: 'Stuck pipe', hint: 'String sticks: overpull and torque climb' },
  { id: 'STICK_SLIP', label: 'Stick-slip', hint: 'Torsional vibration: torque oscillates' },
  { id: 'POOR_HOLE_CLEANING', label: 'Poor hole cleaning', hint: 'Cuttings build up: pressure and drag rise' },
  { id: 'WASHOUT', label: 'Washout', hint: 'Leak in the string: pump pressure falls' },
];

const HAZARD_LABEL: Record<string, string> = {
  lost_circulation: 'Lost circulation', kick: 'Kick / influx', stuck_pipe: 'Stuck pipe', torque_drag: 'Torque & drag',
  washout: 'Washout', pack_off: 'Pack-off', stick_slip: 'Stick-slip', poor_hole_cleaning: 'Hole cleaning',
};

const wsUrl = () => {
  const { protocol, hostname, host } = window.location;
  if (import.meta.env.DEV && (hostname === 'localhost' || hostname === '127.0.0.1')) return 'ws://127.0.0.1:8008/api/v1/physics/stream';
  return `${protocol === 'https:' ? 'wss' : 'ws'}://${host}/api/v1/physics/stream`;
};

const toFrame = (raw: any): Frame | null => {
  const ch = raw?.channels, dep = raw?.depth;
  if (!ch || !dep) return null;
  return {
    t: raw.simulation_time_s ?? 0, md: dep.md_m, formation: raw.formation?.name ?? '—',
    flowIn: ch.flow_in_lpm, flowOut: ch.flow_out_lpm, pit: ch.pit_volume_m3, spp: ch.standpipe_pressure_bar,
    torque: ch.torque_kn_m, hookload: ch.hookload_kn, overpull: ch.overpull_kn, ecd: ch.ecd_gcc,
    ppMargin: ch.pp_margin_bar, fgMargin: ch.fg_margin_bar, rop: ch.rop_m_hr, stickSlip: ch.stick_slip_index,
  };
};

export const SensorsView: React.FC = () => {
  const [frames, setFrames] = useState<Frame[]>([]);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [severity, setSeverity] = useState(1.0);
  const lastRaw = useRef<any>(null);
  const buf = useRef<Frame[]>([]);

  // WebSocket: buffer at 25 Hz, render at ~6 Hz.
  useEffect(() => {
    let ws: WebSocket | null = null, retry: number | undefined, alive = true;
    const connect = () => {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => setConnected(true);
      ws.onclose = () => { setConnected(false); if (alive) retry = window.setTimeout(connect, 2500); };
      ws.onerror = () => ws?.close();
      ws.onmessage = (ev) => {
        try {
          const pkt = JSON.parse(ev.data);
          const raw = pkt.telemetry ?? pkt;
          const f = toFrame(raw);
          if (f) { lastRaw.current = raw; buf.current.push(f); if (buf.current.length > 600) buf.current.splice(0, buf.current.length - 600); }
        } catch { /* ping frames */ }
      };
    };
    connect();
    const draw = window.setInterval(() => setFrames(buf.current.filter((_, i, a) => i % 4 === 0 || i === a.length - 1).slice(-150)), 160);
    return () => { alive = false; window.clearTimeout(retry); window.clearInterval(draw); if (ws) { ws.onclose = null; ws.close(); } };
  }, []);

  // Predictive engine at 1 Hz on the newest frame; status + alerts every 2 s.
  useEffect(() => {
    const ev = window.setInterval(async () => {
      if (!lastRaw.current) return;
      try { setRisk(await api.evaluate(lastRaw.current)); } catch { /* ignore */ }
    }, 1000);
    const st = window.setInterval(async () => {
      try {
        const s = await api.simStatus();
        setStatus(s);
        const wid = s?.latest_record?.well_id;
        if (wid) setAlerts(await api.predictiveAlerts(wid));
      } catch { /* ignore */ }
    }, 2000);
    return () => { window.clearInterval(ev); window.clearInterval(st); };
  }, []);

  const last = frames[frames.length - 1];
  const running = status?.is_running;
  const active: string[] = (status?.active_scenarios ?? []).map((x: any) => (typeof x === 'string' ? x : x.scenario_type ?? x.type));
  const hazards = Object.entries(risk?.hazards ?? {}) as [string, any][];
  const wellId = status?.latest_record?.well_id;

  const act = async (fn: () => Promise<any>) => { try { await fn(); setStatus(await api.simStatus()); } catch { /* shown by status */ } };

  return (
    <div className="px-6 py-6 max-w-[1500px]">
      <PageHeader
        eyebrow="Real-time sensors · physics digital twin"
        title="Can the sensors see trouble before the crew does?"
        lead="A drilling-physics model plays the role of the rig's eRTMAC feed (25 readings per second). Inject a downhole problem below; the risk engine reads only the sensor traces and raises its own alert. Replace this simulator with the live eRTMAC stream and nothing else changes."
        right={
          <>
            <span className={cx('text-xs px-2.5 py-1 rounded-full', connected ? 'bg-accent-soft text-accent' : 'bg-sunken text-ink-3')}>{connected ? 'Stream connected' : 'Connecting…'}</span>
            {running ? <Button onClick={() => act(api.simPause)} icon={<Pause className="w-4 h-4" />}>Pause</Button> : <Button variant="primary" onClick={() => act(api.simStart)} icon={<Play className="w-4 h-4" />}>Run</Button>}
            <Button variant="ghost" onClick={() => act(() => api.simReset(2500))} icon={<RotateCcw className="w-4 h-4" />}>Reset</Button>
          </>
        }
      />

      <Panel className="mb-5">
        <div className="flex flex-wrap items-center gap-2 px-4 py-3">
          <span className="text-xs text-ink-2 mr-1 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" />Inject a problem</span>
          {SCENARIOS.map((s) => (
            <button key={s.id} title={s.hint} onClick={() => act(() => api.simScenario(s.id, severity))}
              className={cx('text-[13px] px-3 h-8 rounded-lg border transition-colors', active.includes(s.id) ? 'bg-ink text-white border-ink' : 'border-line-strong hover:border-ink')}>
              {s.label}
            </button>
          ))}
          <label className="flex items-center gap-2 ml-2 text-xs text-ink-2">Severity
            <input type="range" min={0.3} max={2} step={0.1} value={severity} onChange={(e) => setSeverity(Number(e.target.value))} className="w-24" />
            <span className="num w-7">{severity.toFixed(1)}</span>
          </label>
          {active.length > 0 && <Button size="sm" variant="ghost" onClick={() => act(api.simClearScenarios)}>Clear problems</Button>}
          <span className="ml-auto text-xs text-ink-3 num">{last ? `${n(last.md, 1)} m MD · ${last.formation} · ROP ${n(last.rop, 1)} m/h` : '—'}</span>
        </div>
      </Panel>

      <div className="grid grid-cols-1 2xl:grid-cols-[1fr_400px] gap-5">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <Chart title="Flow in vs flow out" unit="L/min" note="Out < in = losing mud · out > in = influx" series={[{ k: 'flowIn', label: 'In', color: '#8a8f97' }, { k: 'flowOut', label: 'Out', color: '#0e5a69' }]} frames={frames} />
          <Chart title="Pit volume" unit="m³" note="Falling = losses · rising = kick" series={[{ k: 'pit', label: 'Pit', color: '#2c64c9' }]} frames={frames} />
          <Chart title="Surface torque" unit="kN·m" note="Spikes / oscillation = sticking or stick-slip" series={[{ k: 'torque', label: 'Torque', color: '#1c7f75' }]} frames={frames} />
          <Chart title="Overpull" unit="kN" note="Rising overpull = pipe getting stuck" series={[{ k: 'overpull', label: 'Overpull', color: '#6f47c2' }]} frames={frames} />
          <Chart title="Standpipe pressure" unit="bar" note="Sudden drop = washout · rise = pack-off" series={[{ k: 'spp', label: 'SPP', color: '#a8740a' }]} frames={frames} />
          <Chart title="Pressure window" unit="bar margin" note="Distance to pore (kick) and fracture (loss) pressure" series={[{ k: 'ppMargin', label: 'to pore', color: '#b62f5e' }, { k: 'fgMargin', label: 'to fracture', color: '#2c64c9' }]} frames={frames} />
        </div>

        <div className="flex flex-col gap-5">
          <Panel>
            <PanelHead title="Risk engine, live" hint="Rules + anomaly detector + model + offset history, fused every second." />
            {hazards.length === 0 ? <Empty title="Waiting for sensor data" /> : (
              <ul className="divide-y divide-line">
                {hazards.sort((a, b) => b[1].score - a[1].score).map(([k, h]) => (
                  <li key={k} className="px-4 py-2.5">
                    <div className="flex items-center gap-3">
                      <span className="text-[13px] flex-1">{HAZARD_LABEL[k] ?? k}</span>
                      <span className="w-24 h-1.5 bg-sunken rounded-full overflow-hidden"><span className="block h-full rounded-full transition-all duration-500" style={{ width: `${Math.round(h.score * 100)}%`, background: sevOf(h.state).color }} /></span>
                      <span className="text-[11px] font-semibold w-16 text-right" style={{ color: sevOf(h.state).color }}>{sevOf(h.state).label}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel>
            <PanelHead title="Sensor alerts" hint="Raised by the risk engine, not by the simulator." />
            {alerts.length === 0 ? <Empty title="No sensor alerts" body="Inject a problem and give it 10–30 seconds to develop." /> : (
              <ul className="divide-y divide-line max-h-[420px] overflow-y-auto">
                {alerts.slice().reverse().slice(0, 8).map((a: any) => (
                  <li key={a.alert_id} className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <SeverityTag severity={a.severity === 'WARNING' ? 'HIGH' : a.severity === 'ADVISORY' ? 'MEDIUM' : a.severity} />
                      <span className="text-[11px] text-ink-3">{String(a.status).toLowerCase()} · score {Number(a.score).toFixed(2)}</span>
                    </div>
                    <div className="text-[13px] font-medium mt-1">{HAZARD_LABEL[String(a.hazard_type).toLowerCase()] ?? String(a.hazard_type).replace(/_/g, ' ').toLowerCase()}</div>
                    <div className="text-xs text-ink-2 mt-0.5 leading-snug">{a.trigger_reason}</div>
                    {Array.isArray(a.evidence_chain) && a.evidence_chain.length > 0 && (
                      <ul className="mt-1.5 text-[11px] text-ink-3 list-disc pl-4 space-y-0.5">{a.evidence_chain.slice(0, 3).map((e: string, i: number) => <li key={i}>{e}</li>)}</ul>
                    )}
                    {a.recommended_mitigation && (
                      <div className="text-xs mt-1.5"><span className="font-medium">{a.recommended_mitigation.title}: </span><span className="text-ink-2">{a.recommended_mitigation.description}</span></div>
                    )}
                    {a.status === 'ACTIVE' && wellId && (
                      <Button size="sm" className="mt-2" onClick={async () => { await api.mitigate(wellId, a.alert_id); setAlerts(await api.predictiveAlerts(wellId)); }}>Mark action applied</Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
};

const Chart: React.FC<{ title: string; unit: string; note: string; series: { k: keyof Frame; label: string; color: string }[]; frames: Frame[] }> = ({ title, unit, note, series, frames }) => {
  const W = 520, H = 150, pad = 6;
  const vals = frames.flatMap((f) => series.map((s) => f[s.k] as number)).filter((v) => Number.isFinite(v));
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (!Number.isFinite(lo)) { lo = 0; hi = 1; }
  if (hi - lo < 1e-6) { hi += 1; lo -= 1; }
  const span = hi - lo; lo -= span * 0.1; hi += span * 0.1;
  const x = (i: number) => pad + (i / Math.max(1, frames.length - 1)) * (W - pad * 2);
  const y = (v: number) => H - pad - ((v - lo) / (hi - lo)) * (H - pad * 2);
  const last = frames[frames.length - 1];
  return (
    <Panel>
      <div className="px-4 pt-3 flex items-baseline justify-between gap-2">
        <div>
          <div className="text-[13px] font-semibold">{title}</div>
          <div className="text-[11px] text-ink-3">{note}</div>
        </div>
        <div className="text-right">
          {series.map((s) => (
            <div key={String(s.k)} className="num text-[13px]" style={{ color: s.color }}>{last ? n(last[s.k] as number, 1) : '—'} <span className="text-[10px] text-ink-3">{s.label}</span></div>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-[150px]" preserveAspectRatio="none">
        {[0.25, 0.5, 0.75].map((f) => <line key={f} x1={0} x2={W} y1={H * f} y2={H * f} stroke="var(--line)" strokeWidth={0.6} />)}
        {series.map((s) => (
          <polyline key={String(s.k)} fill="none" stroke={s.color} strokeWidth={1.8} vectorEffect="non-scaling-stroke" strokeLinejoin="round"
            points={frames.map((f, i) => `${x(i).toFixed(1)},${y(f[s.k] as number).toFixed(1)}`).join(' ')} />
        ))}
      </svg>
      <div className="px-4 pb-2 text-[10.5px] text-ink-3 num">{unit} · range {n(lo, 1)}–{n(hi, 1)} · last ~25 s</div>
    </Panel>
  );
};
