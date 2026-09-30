import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ChevronRight, Play } from 'lucide-react';
import { api, type Alert } from '../lib/api';
import { ago, hazardOf, m, n, sevOf, shortWell } from '../lib/format';
import { useNwis } from '../state/nwis';
import { Button, Empty, HazardChip, PageHeader, Panel, PanelHead, Segmented, SeverityTag, SourceLink, cx } from '../ui/primitives';

type Filter = 'ACTIVE' | 'ACKNOWLEDGED' | 'ALL';

export const AlertsView: React.FC = () => {
  const { alerts, refreshAlerts, activeWell, startReplay, replay } = useNwis();
  const [filter, setFilter] = useState<Filter>('ACTIVE');
  const [sel, setSel] = useState<string | null>(null);

  const list = useMemo(() => alerts.filter((a) => filter === 'ALL' || a.status === filter), [alerts, filter]);
  useEffect(() => {
    if (!sel || !list.some((a) => a.alert_id === sel)) setSel(list[0]?.alert_id ?? null);
  }, [list, sel]);
  const current = alerts.find((a) => a.alert_id === sel) ?? null;

  return (
    <div className="px-6 py-6 max-w-[1440px]">
      <PageHeader
        eyebrow="Alert center"
        title="Warnings, with the evidence behind them"
        lead="An alert is raised when the bit nears a depth where offset wells had trouble, or when the combined risk score turns high. Each one shows which wells, which reports, and what those crews did about it."
        right={<Segmented<Filter> value={filter} onChange={setFilter} options={[
          { value: 'ACTIVE', label: `Active (${alerts.filter((a) => a.status === 'ACTIVE').length})` },
          { value: 'ACKNOWLEDGED', label: 'Acknowledged' },
          { value: 'ALL', label: 'History' },
        ]} />}
      />

      {alerts.length === 0 ? (
        <Panel>
          <Empty
            title="No alerts yet"
            body={`Alerts come from the live stream. Start it on ${activeWell?.well_name ?? 'the active well'} and NWIS will warn as the bit approaches historical trouble zones.`}
            action={<Button variant="primary" disabled={replay.status === 'running'} onClick={() => startReplay()} icon={<Play className="w-4 h-4" />}>{replay.status === 'running' ? 'Stream running…' : 'Start live stream'}</Button>}
          />
        </Panel>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-[380px_1fr] gap-5">
          <Panel className="self-start overflow-hidden">
            <ul className="divide-y divide-line max-h-[calc(100vh-220px)] overflow-y-auto">
              {list.length === 0 && <li className="p-6 text-[13px] text-ink-3">Nothing in this view.</li>}
              {list.map((a) => (
                <li key={a.alert_id}>
                  <button onClick={() => setSel(a.alert_id)} className={cx('w-full text-left px-4 py-3 relative transition-colors', sel === a.alert_id ? 'bg-accent-soft/60' : 'hover:bg-sunken/60')}>
                    <span className="absolute left-0 top-0 bottom-0 w-1" style={{ background: a.status === 'ACTIVE' ? sevOf(a.severity).color : 'var(--line)' }} />
                    <div className="flex items-center justify-between gap-2">
                      <SeverityTag severity={a.severity} />
                      <span className="text-[11px] text-ink-3">{ago(a.updated_at)}</span>
                    </div>
                    <div className="text-[13px] font-medium mt-1 flex items-center gap-1">{a.title}<ChevronRight className="w-3.5 h-3.5 text-ink-3" /></div>
                    <div className="text-xs text-ink-3 mt-0.5">{shortWell(a.well_id)} · bit {m(a.depth_m)} · {a.status === 'ACTIVE' ? 'active' : `ack by ${a.acknowledged_by}`}</div>
                  </button>
                </li>
              ))}
            </ul>
          </Panel>
          {current ? <AlertDetail a={current} onChanged={refreshAlerts} /> : <Panel><Empty title="Select an alert" /></Panel>}
        </div>
      )}
    </div>
  );
};

const AlertDetail: React.FC<{ a: Alert; onChanged: () => Promise<void> }> = ({ a, onChanged }) => {
  const [who, setWho] = useState(() => { try { return localStorage.getItem('nwis.user') || ''; } catch { return ''; } });
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const hz = hazardOf(a.hazard_type);
  const s = sevOf(a.severity);
  const b = a.score_breakdown;

  const ack = async () => {
    setBusy(true); setErr(null);
    try {
      try { localStorage.setItem('nwis.user', who); } catch { /* ignore */ }
      await api.acknowledge(a.alert_id, who || 'Drilling engineer', note || undefined);
      setNote('');
      await onChanged();
    } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col gap-5 min-w-0" key={a.alert_id}>
      <Panel className="overflow-hidden">
        <div className="p-5 border-l-4" style={{ borderColor: s.color }}>
          <div className="flex items-center gap-3 flex-wrap">
            <SeverityTag severity={a.severity} />
            <HazardChip hazard={a.hazard_type} size="md" />
            <span className="text-xs text-ink-3">{shortWell(a.well_id)} · raised {ago(a.created_at)} · {a.source === 'live_replay' ? 'from live stream' : 'on-demand check'}</span>
          </div>
          <h2 className="text-[20px] font-semibold tracking-[-0.01em] mt-2">{a.title}</h2>
          <p className="text-[14px] text-ink-2 mt-1">{a.message}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <Fact label="Bit depth" value={m(a.depth_m)} />
            <Fact label="Trouble zone" value={a.zone ? `${m(a.zone.from_m)}–${m(a.zone.to_m)}` : '—'} />
            <Fact label="Distance to zone" value={a.lead_distance_m === null || a.lead_distance_m === undefined ? '—' : a.lead_distance_m > 0 ? m(a.lead_distance_m) : 'inside'} />
            <Fact label="Formation at bit" value={a.formation_at_bit ?? '—'} />
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel>
          <PanelHead
            title="Why NWIS raised it"
            hint={a.zone
              ? `Trigger: the bit is ${a.lead_distance_m && a.lead_distance_m > 0 ? `${Math.round(a.lead_distance_m)} m above` : 'inside'} a depth interval where ${a.offset_wells.length} offset well(s) had this problem. Supporting signals (combined ${a.risk_score.toFixed(2)}):`
              : `Trigger: combined risk score ${a.risk_score.toFixed(2)} crossed the high threshold. Its three signals:`}
          />
          <div className="p-4 space-y-3">
            <Signal label="What nearby wells experienced at this depth" v={b.offset_history} color={hz.color} />
            <Signal label="Live sensor behaviour (flow, torque, pressure)" v={b.live_sensors} color={hz.color} />
            <Signal label={b.model_source === 'trained_model' ? 'Trained hazard model' : 'Rule-based estimate — not enough past cases to train a model'} v={b.model} color={hz.color} />
          </div>
        </Panel>
        <Panel>
          <PanelHead title="Recommended before entering the zone" />
          <div className="p-4">
            <p className="text-[13.5px] leading-relaxed">{a.recommendation.summary}</p>
            {a.recommendation.offset_well_practice.length > 0 && (
              <>
                <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mt-4 mb-2">What worked in the offset wells</div>
                <ol className="space-y-2.5">
                  {a.recommendation.offset_well_practice.map((p, i) => (
                    <li key={i} className="text-[13px] leading-snug">
                      <span className="num text-xs font-medium text-accent mr-1.5">{p.from_well}</span>{p.action}
                      {p.outcome && <span className="text-ink-3"> → {p.outcome}</span>}
                      <div className="mt-0.5"><SourceLink doc={p.source_document} page={p.source_page} /></div>
                    </li>
                  ))}
                </ol>
              </>
            )}
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelHead title={`Evidence · ${a.evidence.length} offset-well record${a.evidence.length === 1 ? '' : 's'}`} hint="Source report → extracted fact → event → this alert." />
        <ul className="divide-y divide-line">
          {a.evidence.map((e) => (
            <li key={e.event_id} className="px-4 py-3 grid grid-cols-[110px_1fr_auto] gap-4 items-start">
              <div>
                <Link to={`/wells/${e.well_id}`} className="num text-[13px] font-medium hover:underline">{e.well_name}</Link>
                <div className="num text-xs text-ink-3">{m(e.depth_m)}</div>
                <div className="text-[11px] text-ink-3">{e.formation}</div>
              </div>
              <div className="min-w-0">
                <p className="text-[13px] text-ink-2 leading-snug">{e.narrative}</p>
                {e.mitigation && <p className="text-[13px] mt-1 leading-snug"><span className="font-medium">Action: </span>{e.mitigation}</p>}
                <div className="mt-1.5"><SourceLink doc={e.source_document} page={e.source_page} /></div>
              </div>
              <div className="text-right">
                <SeverityTag severity={e.severity} />
                {e.npt_hours ? <div className="num text-xs text-ink-3 mt-1">{n(e.npt_hours, 1)} h lost</div> : null}
              </div>
            </li>
          ))}
          {a.evidence.length === 0 && <li className="p-4 text-[13px] text-ink-3">This alert was driven by the live risk score rather than a specific offset-well record.</li>}
        </ul>
      </Panel>

      <Panel>
        {a.status === 'ACTIVE' ? (
          <div className="p-4 flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-2xs uppercase tracking-[0.08em] text-ink-3">Your name</span>
              <input value={who} onChange={(e) => setWho(e.target.value)} placeholder="Drilling engineer" className="h-9 px-3 rounded-lg border border-line-strong bg-surface text-[13px] w-48 outline-none focus:border-accent" />
            </label>
            <label className="flex flex-col gap-1 flex-1 min-w-[240px]">
              <span className="text-2xs uppercase tracking-[0.08em] text-ink-3">Action taken (optional)</span>
              <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. 30 bbl LCM pill pre-mixed, pump rate reduced" className="h-9 px-3 rounded-lg border border-line-strong bg-surface text-[13px] outline-none focus:border-accent" />
            </label>
            <Button variant="primary" onClick={ack} disabled={busy} icon={<Check className="w-4 h-4" />}>Acknowledge</Button>
            {err && <div className="w-full text-xs" style={{ color: 'var(--sev-critical)' }}>{err}</div>}
          </div>
        ) : (
          <div className="p-4 text-[13px] text-ink-2">
            Acknowledged by <span className="font-medium text-ink">{a.acknowledged_by}</span> {ago(a.acknowledged_at)}{a.ack_note ? <> — “{a.ack_note}”</> : null}
          </div>
        )}
      </Panel>
    </div>
  );
};

const Fact: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">{label}</div>
    <div className="num text-[15px] font-medium mt-0.5">{value}</div>
  </div>
);

const Signal: React.FC<{ label: string; v: number; color: string }> = ({ label, v, color }) => (
  <div>
    <div className="flex justify-between text-[13px]"><span className="text-ink-2">{label}</span><span className="num">{v.toFixed(2)}</span></div>
    <div className="h-1.5 rounded-full bg-sunken mt-1.5 overflow-hidden"><div className="h-full rounded-full" style={{ width: `${Math.round(v * 100)}%`, background: color }} /></div>
  </div>
);
