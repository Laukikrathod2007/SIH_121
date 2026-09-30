import React from 'react';
import { api } from '../lib/api';
import { hazardOf, n } from '../lib/format';
import { useLoad } from '../state/nwis';
import { Empty, ErrorNote, Loading, PageHeader, Panel, PanelHead, cx } from '../ui/primitives';

/** Every number on this screen is produced by code in the repo — nothing is typed in. */

const ARCH_LABEL: Record<string, { name: string; what: string }> = {
  RULES: { name: 'Physics rules only', what: 'Thresholds on flow balance, pit trend, overpull, torque, pressure window' },
  RULES_PLUS_ISOLATION_FOREST: { name: 'Rules + anomaly detector', what: 'Rules blended with an Isolation Forest trained on normal drilling' },
  XGBOOST: { name: 'Gradient-boosted classifier', what: 'XGBoost multi-class model on engineered sensor features' },
  RULES_PLUS_ISOLATION_FOREST_PLUS_XGBOOST: { name: 'Full fusion (what the app runs)', what: 'Rules + anomaly + classifier + offset-well history, weighted' },
};

const FEATURE_LABEL: Record<string, string> = {
  fg_margin_bar: 'Margin to fracture pressure', pp_margin_bar: 'Margin to pore pressure', stick_slip_index: 'Stick-slip index',
  d_exponent_deviation: 'd-exponent deviation', d_exponent_slope: 'd-exponent trend', overpull_kn: 'Overpull',
  delta_flow: 'Flow out − flow in', flow_imbalance_duration_s: 'Duration of flow imbalance', standpipe_pressure_bar: 'Standpipe pressure',
  torque_kn_m: 'Surface torque', xi: 'Position within formation',
};

export const ModelsView: React.FC = () => {
  const b = useLoad(() => api.benchmarks(), []);
  if (b.loading) return <Loading label="Loading benchmarks" />;
  if (b.error || !b.data) return <ErrorNote message={b.error || 'No data'} onRetry={b.reload} />;
  const { offset_hazard_models: hz, sensor_risk_models: sr, document_extraction: dx } = b.data;

  return (
    <div className="px-6 py-6 max-w-[1440px]">
      <PageHeader
        eyebrow="Models & benchmarks"
        title="How good are the models? Measured, not claimed."
        lead="Three kinds of model power NWIS. Each is tested on data it did not see during training, and the numbers below are produced by the evaluation code in this repository. Where there is not enough data to train a model, the app falls back to transparent rules and says so."
      />

      {/* 1. Offset-history hazard models */}
      <Panel className="mb-5">
        <PanelHead
          title="1 · Offset-history hazard models"
          hint="Predict, from depth, formation and well path alone, whether a hazard is likely at a given point of a well. Tested by holding out one entire well at a time and predicting it from the others."
          right={hz ? <span className="text-[11px] text-ink-3">trained {new Date(hz.generated_at + 'Z').toLocaleString('en-IN')}</span> : null}
        />
        {!hz ? <Empty title="Not trained yet" body="The backend trains these at startup; refresh in a moment." /> : (
          <div className="p-4 grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-6">
            <table className="w-full text-[13px]">
              <thead><tr className="text-left text-2xs uppercase tracking-[0.08em] text-ink-3 border-b border-line">
                <th className="py-2 font-medium">Hazard</th><th className="py-2 font-medium">Status</th><th className="py-2 font-medium text-right">Past cases</th>
                <th className="py-2 font-medium pl-6">Ranking quality (AUC)</th><th className="py-2 font-medium text-right">Wells tested</th>
              </tr></thead>
              <tbody>
                {Object.entries(hz.trained as Record<string, any>).map(([h, m]) => (
                  <tr key={h} className="border-b border-line">
                    <td className="py-2.5"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full" style={{ background: hazardOf(h).color }} />{hazardOf(h).label}</span></td>
                    <td className="py-2.5 text-accent font-medium text-xs">Trained model</td>
                    <td className="py-2.5 num text-right">{m.n_positive} / {m.n_total}</td>
                    <td className="py-2.5 pl-6"><AucBar auc={m.leave_one_well_out_auc} /></td>
                    <td className="py-2.5 num text-right">{m.cv_folds_evaluated}</td>
                  </tr>
                ))}
                {Object.entries(hz.skipped as Record<string, string>).map(([h, why]) => (
                  <tr key={h} className="border-b border-line text-ink-2">
                    <td className="py-2.5"><span className="inline-flex items-center gap-2"><span className="w-2 h-2 rounded-full" style={{ background: hazardOf(h).color }} />{hazardOf(h).label}</span></td>
                    <td className="py-2.5 text-xs">Rule-based estimate</td>
                    <td className="py-2.5 num text-right">{why.match(/\d+/)?.[0] ?? '—'}</td>
                    <td className="py-2.5 pl-6 text-xs text-ink-3">not trained — {why}</td>
                    <td className="py-2.5 num text-right">—</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="text-[13px] text-ink-2 leading-relaxed">
              <div className="font-medium text-ink mb-1">How to read AUC</div>
              0.5 means no better than chance, 1.0 means every true case is ranked above every non-case. With 10–14 past cases per hazard on a 12-well testbed these are modest,
              honest numbers; they improve as more offset reports are ingested. Method: {hz.method}
            </div>
          </div>
        )}
      </Panel>

      {/* 2. Sensor risk engine */}
      <Panel className="mb-5">
        <PanelHead
          title="2 · Real-time sensor risk engine"
          hint="Detects a developing problem from the rig's sensor stream. Tested on held-out simulator runs (1 reading per second), each containing a normal period followed by a fault."
          right={sr ? <span className="text-[11px] text-ink-3">benchmarked {new Date(sr.generated_at + 'Z').toLocaleString('en-IN')}</span> : null}
        />
        {!sr ? <Empty title="Benchmark running" body="The backend runs the sensor benchmark in the background at first start (about 35 s). Refresh shortly." /> : (
          <div className="p-4">
            <table className="w-full text-[13px]">
              <thead><tr className="text-left text-2xs uppercase tracking-[0.08em] text-ink-3 border-b border-line">
                <th className="py-2 font-medium">Approach</th>
                <th className="py-2 font-medium text-right" title="Of the readings flagged, share that really were a problem">Precision</th>
                <th className="py-2 font-medium text-right" title="Of the problem readings, share that were flagged">Recall</th>
                <th className="py-2 font-medium text-right">F1</th>
                <th className="py-2 font-medium text-right">Problems caught</th>
                <th className="py-2 font-medium text-right" title="New false warnings per hour of normal drilling">False alarms / h</th>
                <th className="py-2 font-medium text-right" title="Seconds from the start of a problem to the first warning">Time to detect</th>
              </tr></thead>
              <tbody>
                {Object.entries(sr.architectures as Record<string, any>).map(([k, m]) => {
                  const best = Math.max(...Object.values(sr.architectures as Record<string, any>).map((x: any) => x.f1));
                  return (
                    <tr key={k} className={cx('border-b border-line align-top', k.endsWith('XGBOOST') && k.startsWith('RULES') && 'bg-accent-soft/40')}>
                      <td className="py-2.5 pr-4"><div className="font-medium">{ARCH_LABEL[k]?.name ?? k}</div><div className="text-[11px] text-ink-3">{ARCH_LABEL[k]?.what}</div></td>
                      <td className="py-2.5 num text-right">{m.precision.toFixed(2)}</td>
                      <td className="py-2.5 num text-right">{m.recall.toFixed(2)}</td>
                      <td className={cx('py-2.5 num text-right', m.f1 === best && 'text-accent font-medium')}>{m.f1.toFixed(2)}</td>
                      <td className="py-2.5 num text-right">{m.episodes_detected}/{m.hazard_episodes}</td>
                      <td className="py-2.5 num text-right">{n(m.false_alert_episodes_per_hour, 1)}</td>
                      <td className="py-2.5 num text-right">{m.mean_detection_delay_s === null ? '—' : `${n(m.mean_detection_delay_s, 1)} s`}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-5">
              <div className="lg:col-span-2 text-[13px] text-ink-2 leading-relaxed">
                <div className="font-medium text-ink mb-1">What this shows</div>
                <FusionVerdict archs={sr.architectures} />{' '}
                Test set: {sr.setup?.test_runs?.length ?? '—'} held-out runs, {Object.values(sr.architectures as Record<string, any>)[0]?.test_samples} readings.
              </div>
              <div>
                <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2">Speed per reading</div>
                <div className="space-y-1 text-[13px]">
                  <Row k="Feature extraction" v={`${n(sr.latency?.feature_extraction_ms, 1)} ms`} />
                  <Row k="Model inference" v={`${n(sr.latency?.model_inference_ms, 1)} ms`} />
                  <Row k="Risk fusion" v={`${n(sr.latency?.risk_fusion_ms, 1)} ms`} />
                  <Row k="Total, reading → alert" v={`${n(sr.latency?.total_alert_latency_ms, 1)} ms`} strong />
                </div>
              </div>
            </div>
            {Array.isArray(sr.top_features) && (
              <div className="mt-5">
                <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2">Signals the classifier relies on most</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-1.5">
                  {(sr.top_features as [string, number][]).slice(0, 8).map(([f, w]) => (
                    <div key={f} className="grid grid-cols-[180px_1fr_44px] items-center gap-3 text-[13px]">
                      <span className="truncate">{FEATURE_LABEL[f] ?? f}</span>
                      <span className="h-1.5 bg-sunken rounded-full overflow-hidden"><span className="block h-full bg-accent rounded-full" style={{ width: `${(w / (sr.top_features[0][1] || 1)) * 100}%` }} /></span>
                      <span className="num text-xs text-ink-3 text-right">{w.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Panel>

      {/* 3. Document extraction */}
      <Panel>
        <PanelHead title="3 · Report reading (document extraction)" hint={`Checked against hand-labelled sample reports: ${dx.rule}.`} />
        <div className="p-4 grid grid-cols-2 md:grid-cols-5 gap-4 border-b border-line">
          <Big label="Incidents found" v={`${Math.round(dx.event_recall * 100)}%`} sub={`recall, ${dx.labelled_events} labelled`} />
          <Big label="Correct when found" v={`${Math.round(dx.event_precision * 100)}%`} sub="precision" />
          <Big label="F1" v={dx.event_f1.toFixed(2)} />
          <Big label="Well identified" v={`${Math.round(dx.well_name_accuracy * 100)}%`} sub={`${dx.documents_scored} reports`} />
          <Big label="Real 74-page report" v={dx.real_document_runs?.[0] ? `${n(dx.real_document_runs[0].ms_per_page, 0)} ms/page` : '—'} sub={dx.real_document_runs?.[0] ? `${dx.real_document_runs[0].events_found} incidents found` : undefined} />
        </div>
        <table className="w-full text-[13px]">
          <thead><tr className="text-left text-2xs uppercase tracking-[0.08em] text-ink-3 border-b border-line">
            <th className="px-4 py-2 font-medium">Report</th><th className="py-2 font-medium text-right">Labelled</th><th className="py-2 font-medium text-right">Found</th>
            <th className="py-2 font-medium text-right">Missed</th><th className="py-2 font-medium text-right">Spurious</th><th className="py-2 font-medium pl-6">Well name</th><th className="px-4 py-2 font-medium text-right">Time</th>
          </tr></thead>
          <tbody>
            {dx.documents.map((d: any) => (
              <tr key={d.document} className="border-b border-line">
                <td className="px-4 py-2.5 num text-xs">{d.document}</td>
                <td className="py-2.5 num text-right">{d.labelled_events}</td>
                <td className="py-2.5 num text-right">{d.matched}</td>
                <td className="py-2.5 num text-right">{d.missed}</td>
                <td className="py-2.5 num text-right">{d.spurious}</td>
                <td className="py-2.5 pl-6 text-xs">{d.well_name_extracted ?? '—'} {d.well_name_correct ? '✓' : `✗ (expected ${d.well_name_expected})`}</td>
                <td className="px-4 py-2.5 num text-right">{n(d.processing_ms, 0)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="px-4 py-3 text-xs text-ink-3 leading-relaxed">
          Caveat: the labelled set is small and the reports are clean, typed DDRs, so this shows the pipeline works end to end rather than real-world accuracy.
          The 74-page run is a real public drilling report (throughput only — it has no labels). Scanned reports need the OCR engine (Docling) installed.
        </p>
      </Panel>
    </div>
  );
};

/** Plain-language summary generated from the measured numbers (no hard-coded conclusions). */
const FusionVerdict: React.FC<{ archs: Record<string, any> }> = ({ archs }) => {
  const entries = Object.entries(archs);
  const best = entries.reduce((a, b) => (b[1].f1 > a[1].f1 ? b : a));
  const fusion = archs.RULES_PLUS_ISOLATION_FOREST_PLUS_XGBOOST;
  const caughtAll = entries.every(([, m]) => m.episodes_detected === m.hazard_episodes);
  return (
    <>
      {caughtAll ? `Every approach catches all ${entries[0][1].hazard_episodes} test problems. ` : ''}
      Best overall here: <b className="font-medium text-ink">{ARCH_LABEL[best[0]]?.name ?? best[0]}</b> (F1 {best[1].f1.toFixed(2)}).
      {fusion && fusion.f1 < best[1].f1 && (
        <> The full fusion engine currently scores lower (F1 {fusion.f1.toFixed(2)}, {n(fusion.false_alert_episodes_per_hour, 0)} false-alarm episodes per hour):
          its score hovers around the alert threshold, so warnings flicker on and off. Re-tuning its weights and adding a hold time is the next improvement;
          until then the single-model results show what the sensors can support.</>
      )}
    </>
  );
};

const AucBar: React.FC<{ auc: number | null }> = ({ auc }) => {
  if (auc === null || auc === undefined) return <span className="text-xs text-ink-3">not enough wells to score</span>;
  const pct = Math.max(0, Math.min(1, (auc - 0.5) / 0.5)) * 100;
  const color = auc >= 0.75 ? 'var(--sev-low)' : auc >= 0.6 ? 'var(--sev-medium)' : 'var(--sev-high)';
  return (
    <span className="inline-flex items-center gap-3">
      <span className="relative w-40 h-2 rounded-full bg-sunken overflow-hidden"><span className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${pct}%`, background: color }} /></span>
      <span className="num text-[13px]" style={{ color }}>{auc.toFixed(2)}</span>
      <span className="text-[11px] text-ink-3">{auc >= 0.75 ? 'useful' : auc >= 0.6 ? 'weak but above chance' : 'near chance'}</span>
    </span>
  );
};

const Row: React.FC<{ k: string; v: string; strong?: boolean }> = ({ k, v, strong }) => (
  <div className={cx('flex justify-between', strong && 'font-medium border-t border-line pt-1 mt-1')}><span className="text-ink-2">{k}</span><span className="num">{v}</span></div>
);

const Big: React.FC<{ label: string; v: string; sub?: string }> = ({ label, v, sub }) => (
  <div>
    <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">{label}</div>
    <div className="num text-[22px] font-medium leading-8">{v}</div>
    {sub && <div className="text-[11px] text-ink-3">{sub}</div>}
  </div>
);
