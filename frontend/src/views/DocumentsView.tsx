import React, { useCallback, useEffect, useRef, useState } from 'react';
import { CheckCircle2, FileUp, Loader2, UploadCloud, XCircle } from 'lucide-react';
import { api, type DocumentResult, type Job } from '../lib/api';
import { ago, hazardOf, n } from '../lib/format';
import { useLoad, useNwis } from '../state/nwis';
import { Button, Empty, ErrorNote, HazardChip, Loading, PageHeader, Panel, PanelHead, SeverityTag, cx } from '../ui/primitives';

const EVENT_TO_HAZARD: Record<string, string | null> = {
  MUD_LOSS: 'MUD_LOSS', LOST_CIRCULATION: 'MUD_LOSS', STUCK_PIPE: 'STUCK_PIPE', KICK: 'KICK', GAS_INFLUX: 'KICK',
  WELLBORE_INSTABILITY: 'WELLBORE_INSTABILITY', EQUIPMENT_FAILURE: null, DEVIATION_CONTROL: null, NPT_OPERATIONAL: null, UNKNOWN: null,
};
const val = (f: any) => (f && typeof f === 'object' ? f.normalized_value : f);
const cleanName = (name?: string | null) => (name ?? '').replace(/^JOB-[0-9A-F]+_/i, '');
const prettyType = (t?: string | null) => (t ?? 'report').replace(/_/g, ' ').toLowerCase();
const dur = (ms?: number) => (!ms ? '—' : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`);

export const DocumentsView: React.FC = () => {
  const { openEvidence } = useNwis();
  const results = useLoad(() => api.results(), []);
  const samples = useLoad(() => api.samples(), []);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refreshJobs = useCallback(async () => {
    try { setJobs((await api.jobs()).slice(0, 8)); } catch { /* offline */ }
  }, []);
  useEffect(() => { refreshJobs(); }, [refreshJobs]);

  // Poll while anything is in flight; refresh results when a job completes.
  const running = jobs.some((j) => j.status === 'QUEUED' || j.status === 'PROCESSING');
  useEffect(() => {
    if (!running) return;
    const t = window.setInterval(async () => {
      const before = jobs.filter((j) => j.status !== 'COMPLETED').map((j) => j.job_id);
      const next = (await api.jobs().catch(() => jobs)).slice(0, 8);
      setJobs(next);
      const done = next.find((j) => before.includes(j.job_id) && j.status === 'COMPLETED' && j.document_id);
      if (done) { results.reload(); setSelected(done.document_id!); }
    }, 1200);
    return () => window.clearInterval(t);
  }, [running, jobs]); // eslint-disable-line react-hooks/exhaustive-deps

  const upload = async (file: File) => {
    setErr(null);
    if (!file.name.toLowerCase().endsWith('.pdf')) { setErr('Only PDF reports are accepted.'); return; }
    try { await api.ingest(file); await refreshJobs(); } catch (e: any) { setErr(e.message); }
  };
  const runSample = async (name: string) => {
    setErr(null);
    try { await api.ingestSample(name); await refreshJobs(); } catch (e: any) { setErr(e.message); }
  };

  const list = results.data?.results ?? [];
  useEffect(() => { if (!selected && list[0]) setSelected(list[0].document_id); }, [list, selected]);

  return (
    <div className="px-6 py-6 max-w-[1440px]">
      <PageHeader
        eyebrow="Document intelligence"
        title="Reports in, structured events out"
        lead="Drop a daily drilling report or well completion report. NWIS reads it (text layer, or OCR for scans), finds incidents, depths, formations and remedial actions, checks them against drilling physics, and adds them to the searchable archive with a link back to the page."
      />

      <div className="grid grid-cols-1 xl:grid-cols-[400px_1fr] gap-5">
        <div className="flex flex-col gap-5">
          <Panel>
            <div
              onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) upload(f); }}
              className={cx('m-4 rounded-xl border-2 border-dashed p-6 text-center transition-colors', drag ? 'border-accent bg-accent-soft' : 'border-line-strong')}
            >
              <UploadCloud className="w-7 h-7 mx-auto text-ink-3" strokeWidth={1.5} />
              <div className="text-[13.5px] font-medium mt-2">Drop a PDF report here</div>
              <div className="text-xs text-ink-3 mt-1">DDR or WCR · up to 100 MB · processed on this server</div>
              <Button className="mt-3" size="sm" onClick={() => fileRef.current?.click()} icon={<FileUp className="w-3.5 h-3.5" />}>Choose file</Button>
              <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ''; }} />
            </div>
            {samples.data && samples.data.samples.length > 0 && (
              <div className="px-4 pb-4">
                <div className="text-2xs uppercase tracking-[0.08em] text-ink-3 mb-2">Or run a sample report</div>
                {samples.data.samples.map((s) => (
                  <button key={s.name} onClick={() => runSample(s.name)} className="w-full text-left flex items-center justify-between px-3 py-2 rounded-lg border border-line hover:border-accent mb-1.5 text-[13px]">
                    <span className="num truncate">{s.name}</span><span className="text-xs text-accent shrink-0 ml-2">Process →</span>
                  </button>
                ))}
              </div>
            )}
            {err && <ErrorNote message={err} />}
          </Panel>

          <Panel>
            <PanelHead title="Processing queue" />
            {jobs.length === 0 ? <Empty title="No jobs yet" /> : (
              <ul className="divide-y divide-line">
                {jobs.map((j) => (
                  <li key={j.job_id} className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      {j.status === 'COMPLETED' ? <CheckCircle2 className="w-4 h-4 text-sev-low" /> : j.status === 'FAILED' ? <XCircle className="w-4 h-4 text-sev-critical" /> : <Loader2 className="w-4 h-4 animate-spin text-accent" />}
                      <span className="text-[13px] truncate flex-1">{j.filename}</span>
                      <span className="text-[11px] text-ink-3">{ago(j.submitted_at)}</span>
                    </div>
                    {(j.status === 'PROCESSING' || j.status === 'QUEUED') && (
                      <div className="h-1 bg-sunken rounded-full mt-2 overflow-hidden"><div className="h-full bg-accent transition-all" style={{ width: `${Math.max(5, j.progress_percent)}%` }} /></div>
                    )}
                    <div className="text-[11px] text-ink-3 mt-1 truncate">{j.error || j.message}</div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel>
            <PanelHead title={`Processed reports (${list.length})`} />
            {results.loading ? <Loading /> : list.length === 0 ? <Empty title="Nothing processed yet" body="Upload a report or run the sample." /> : (
              <ul className="divide-y divide-line max-h-[360px] overflow-y-auto">
                {list.map((r) => (
                  <li key={r.document_id}>
                    <button onClick={() => setSelected(r.document_id)} className={cx('w-full text-left px-4 py-2.5', selected === r.document_id ? 'bg-accent-soft/60' : 'hover:bg-sunken/60')}>
                      <div className="text-[13px] font-medium truncate">{cleanName(r.source_filename)}</div>
                      <div className="text-[11px] text-ink-3">{r.well_name ?? 'well not detected'} · {r.events_count} events · {r.validation_status?.toLowerCase().replace('_', ' ')}{r.reviewed ? ` · ${r.review_decision}` : ''}</div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        {selected ? <ResultDetail docId={selected} onChanged={results.reload} openPage={(page) => openEvidence({ doc: `${list.find((x) => x.document_id === selected)?.source_filename} [${selected}]`, page })} /> : (
          <Panel><Empty title="Select a processed report" body="Its extracted events, formations and lost-time records appear here." /></Panel>
        )}
      </div>
    </div>
  );
};

const ResultDetail: React.FC<{ docId: string; onChanged: () => void; openPage: (page: number) => void }> = ({ docId, onChanged, openPage }) => {
  const r = useLoad(() => api.result(docId), [docId]);
  const [busy, setBusy] = useState(false);
  if (r.loading) return <Panel><Loading label="Loading extraction" /></Panel>;
  if (r.error || !r.data) return <Panel><ErrorNote message={r.error || 'Not found'} /></Panel>;
  const d = r.data;
  const events: { page: number; e: any }[] = (d.pages ?? []).flatMap((p: any) => (p.drilling_events ?? []).map((e: any) => ({ page: (p.page_number ?? 0) + 1, e })));
  const pushed = events.filter(({ e }) => EVENT_TO_HAZARD[e.event_type]).length;

  const decide = async (decision: 'approved' | 'rejected') => {
    setBusy(true);
    try { await api.reviewDecision(docId, 'Drilling engineer', decision); r.reload(); onChanged(); } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col gap-5 min-w-0">
      <Panel>
        <div className="p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">{prettyType(d.document_type)} · {d.total_pages} page{d.total_pages === 1 ? '' : 's'} · read in {dur(d.total_processing_time_ms)}</div>
              <h2 className="text-[18px] font-semibold mt-1">{cleanName(d.source_filename)}</h2>
              <div className="text-[13px] text-ink-2 mt-0.5">Well <span className="num font-medium text-ink">{d.well_name ?? 'not detected'}</span>{d.operator ? ` · ${d.operator}` : ''}{d.report_date ? ` · ${d.report_date}` : ''}</div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => openPage(1)}>View original</Button>
              {!d.reviewed ? (
                <>
                  <Button size="sm" variant="primary" disabled={busy} onClick={() => decide('approved')}>Approve</Button>
                  <Button size="sm" disabled={busy} onClick={() => decide('rejected')}>Reject</Button>
                </>
              ) : <span className="text-xs px-2.5 py-1 rounded-full bg-sunken text-ink-2 self-center">Reviewed · {d.review_decision}</span>}
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4">
            <Mini label="Read confidence" v={`${Math.round((d.overall_confidence ?? 0) * 100)}%`} />
            <Mini label="Physics check" v={(d.validation_status ?? '—').toLowerCase().replace('_', ' ')} />
            <Mini label="Incidents found" v={String(events.length)} />
            <Mini label="Added to archive" v={String(pushed)} />
            <Mini label="Scanned pages (OCR)" v={String(d.scanned_pages ?? 0)} />
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHead title="Extracted incidents" hint="Each row: page in the report → fact read → event created in the archive." />
        {events.length === 0 ? <Empty title="No incidents detected in this report" /> : (
          <table className="w-full text-[13px]">
            <thead><tr className="text-left text-2xs uppercase tracking-[0.08em] text-ink-3 border-b border-line">
              <th className="px-4 py-2 font-medium">Page</th><th className="py-2 font-medium">Read from the report</th><th className="py-2 font-medium">Depth</th><th className="py-2 font-medium">Crew action</th><th className="px-4 py-2 font-medium">In archive as</th>
            </tr></thead>
            <tbody>
              {events.map(({ page, e }) => {
                const hz = EVENT_TO_HAZARD[e.event_type];
                return (
                  <tr key={e.event_id} className="border-b border-line align-top">
                    <td className="px-4 py-3"><button className="num text-accent hover:underline" onClick={() => openPage(page)}>p.{page}</button></td>
                    <td className="py-3 pr-4 max-w-[360px]"><p className="text-ink-2 leading-snug">{e.raw_narrative.replace(/^\d{4}\s*-\s*\d{4}\s*:\s*/, '')}</p><div className="mt-1 flex items-center gap-2"><SeverityTag severity={e.severity} />{e.formation && <span className="text-[11px] text-ink-3">{e.formation}</span>}</div></td>
                    <td className="py-3 num whitespace-nowrap">{val(e.depth_start_md_m) ? `${n(val(e.depth_start_md_m))} m` : <span className="text-ink-3 font-sans text-xs">not stated</span>}</td>
                    <td className="py-3 pr-4 text-ink-2 leading-snug max-w-[260px]">{e.mitigation_description ?? '—'}</td>
                    <td className="px-4 py-3">{hz ? <HazardChip hazard={hz} /> : <span className="text-[11px] text-ink-3">not a geological hazard — kept in report only</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Panel>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Panel>
          <PanelHead title={`Formation tops (${(d.all_formation_tops ?? []).length})`} />
          <ul className="divide-y divide-line">
            {(d.all_formation_tops ?? []).map((f: any, i: number) => (
              <li key={i} className="px-4 py-2 flex justify-between text-[13px]"><span>{f.formation_name}</span><span className="num text-ink-2">{val(f.top_md_m) ? `${n(val(f.top_md_m))} m` : '—'}</span></li>
            ))}
            {(d.all_formation_tops ?? []).length === 0 && <li className="px-4 py-3 text-[13px] text-ink-3">None found.</li>}
          </ul>
        </Panel>
        <Panel>
          <PanelHead title={`Lost-time records (${(d.all_npt_records ?? []).length})`} />
          <ul className="divide-y divide-line">
            {(d.all_npt_records ?? []).map((r2: any, i: number) => (
              <li key={i} className="px-4 py-2 flex justify-between gap-3 text-[13px]"><span className="text-ink-2 truncate">{r2.description || r2.iadc_code || 'NPT'}</span><span className="num">{n(val(r2.npt_hours), 1)} h</span></li>
            ))}
            {(d.all_npt_records ?? []).length === 0 && <li className="px-4 py-3 text-[13px] text-ink-3">None found.</li>}
          </ul>
        </Panel>
      </div>
    </div>
  );
};

const Mini: React.FC<{ label: string; v: string }> = ({ label, v }) => (
  <div>
    <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">{label}</div>
    <div className="num text-[15px] font-medium mt-0.5 capitalize">{v}</div>
  </div>
);


