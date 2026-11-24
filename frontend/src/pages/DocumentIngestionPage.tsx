import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  FileUp,
  FileText,
  CheckCircle,
  XCircle,
  Upload,
  Download,
  Loader2,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  BookOpen,
} from 'lucide-react';
import { api } from '../services/api';
import { DocumentExtractionResult, ExtractedField, JobStatusResponse, ReviewQueueItem, ReviewDecisionResult, PostgresSyncStatus } from '../types';
import { PdfEvidenceViewer } from '../components/PdfEvidenceViewer';

// Real upload -> job poll -> result flow against modules/01_document_intelligence:
//   POST /api/v1/ingest              (multipart upload)
//   GET  /api/v1/jobs/{job_id}       (poll every 1.5s)
//   GET  /api/v1/results/{doc_id}    (fetched once the job completes)
//   POST /api/v1/review/{doc_id}/decision  (approve/reject, if flagged)
// This replaces the previous page's fake setInterval progress bar and
// hardcoded sample extraction tables — there is no simulated data here.

const POLL_INTERVAL_MS = 1500;

function fieldValue(f: ExtractedField | number | null | undefined): string {
  if (f == null) return '—';
  if (typeof f === 'number') return String(f);
  if (f.normalized_value != null) return String(f.normalized_value);
  return f.raw_text || '—';
}

// Pass 5: plain, user-facing copy for the closed PostgresSyncStatus enum —
// never shows a raw exception or a developer-oriented term like "write-
// through" or "DB unreachable". "not_configured" is a neutral statement of
// environment, not an error (this dev/demo environment simply has no
// shared database wired up yet).
function syncStatusCopy(status: PostgresSyncStatus | null): { label: string; tone: 'ok' | 'muted' | 'warn'; retry: boolean } {
  switch (status) {
    case 'synced':
      return { label: 'Saved to shared knowledge base', tone: 'ok', retry: false };
    case 'not_configured':
      return { label: 'Not yet saved (shared database not enabled in this environment)', tone: 'muted', retry: false };
    case 'unavailable':
      return { label: 'Temporarily unable to save — retry shortly', tone: 'warn', retry: true };
    case 'error':
      return { label: 'Save failed — retry', tone: 'warn', retry: true };
    default:
      return { label: '', tone: 'muted', retry: false };
  }
}

export const DocumentIngestionPage: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [result, setResult] = useState<DocumentExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewTab, setPreviewTab] = useState<'formations' | 'npt' | 'json'>('formations');
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<string | null>(null);
  const [showPdfViewer, setShowPdfViewer] = useState(false);
  // Pass 5: the knowledge-base handoff outcome and the document's shared-
  // database sync state — both already returned by the backend since
  // Pass 4/5 but previously discarded here without being shown anywhere.
  const [decisionOutcome, setDecisionOutcome] = useState<ReviewDecisionResult | null>(null);
  const [syncStatus, setSyncStatus] = useState<PostgresSyncStatus | null>(null);
  const [resyncing, setResyncing] = useState(false);

  // Review Queue panel (Priority 6 remediation, 2026-10-04): surfaces
  // GET /api/v1/review/queue, a real backend endpoint that previously had
  // no frontend caller at all. Lists every document across past sessions
  // that module 01 flagged for human review, not just the one just
  // uploaded above. Reuses the exact same submitDecision() flow already
  // wired for a freshly-uploaded document.
  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      const res = await api.getReviewQueue();
      setQueue(res.queue);
    } catch (err) {
      setQueueError('Could not load the review queue. Contact your system administrator if this persists.');
      console.error(err);
    } finally {
      setQueueLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const openQueuedDocument = useCallback(async (docId: string) => {
    setError(null);
    setReviewDecision(null);
    setDecisionOutcome(null);
    try {
      const doc = await api.getReviewDetail(docId);
      setResult(doc);
      setSyncStatus(doc.postgres_sync_status ?? null);
      setJobId(null);
      setJobStatus(null);
    } catch (err) {
      setError(`Could not load review detail for ${docId}.`);
      console.error(err);
    }
  }, []);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const startPolling = useCallback((id: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getJobStatus(id);
        setJobStatus(status);
        if (status.status === 'COMPLETED') {
          if (pollRef.current) clearInterval(pollRef.current);
          if (status.document_id) {
            const doc = await api.getResult(status.document_id);
            setResult(doc);
            setSyncStatus(doc.postgres_sync_status ?? null);
          }
          setUploading(false);
        } else if (status.status === 'FAILED') {
          if (pollRef.current) clearInterval(pollRef.current);
          setError(status.error || status.message || 'Extraction failed.');
          setUploading(false);
        }
      } catch (err) {
        if (pollRef.current) clearInterval(pollRef.current);
        setError('Lost connection to the server while checking extraction progress. Contact your system administrator if this persists.');
        setUploading(false);
        console.error(err);
      }
    }, POLL_INTERVAL_MS);
  }, []);

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are accepted by the ingestion pipeline.');
      return;
    }
    setError(null);
    setResult(null);
    setJobStatus(null);
    setReviewDecision(null);
    setDecisionOutcome(null);
    setSyncStatus(null);
    setUploading(true);
    try {
      const job = await api.ingestDocument(file);
      setJobId(job.job_id);
      startPolling(job.job_id);
    } catch (err) {
      setError('Could not reach the document processing service. Contact your system administrator if this persists.');
      setUploading(false);
      console.error(err);
    }
  }, [startPolling]);

  const loadSampleDocument = useCallback(async (filename: string) => {
    setError(null);
    setResult(null);
    setJobStatus(null);
    setReviewDecision(null);
    setDecisionOutcome(null);
    setSyncStatus(null);
    setUploading(true);
    try {
      const apiBase = (import.meta.env.VITE_API_BASE as string | undefined) || 'http://localhost:8000';
      const res = await fetch(`${apiBase}/api/evidence?name=${encodeURIComponent(filename)}`);
      if (!res.ok) {
        throw new Error(`Sample document "${filename}" could not be fetched (${res.status}). Verify backend is running.`);
      }
      const blob = await res.blob();
      const sampleFile = new File([blob], filename, { type: 'application/pdf' });
      await handleFile(sampleFile);
    } catch (err: any) {
      setError(err?.message || `Failed to fetch sample document ${filename}.`);
      setUploading(false);
      console.error(err);
    }
  }, [handleFile]);

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const submitDecision = async (decision: 'approved' | 'rejected') => {
    if (!result) return;
    setReviewSubmitting(true);
    try {
      const outcome = await api.submitReviewDecision(result.document_id, { reviewer: 'frontend-operator', decision });
      setReviewDecision(decision);
      setDecisionOutcome(outcome);
      setSyncStatus(outcome.postgres_sync_status);
      loadQueue(); // the decided document should drop out of the pending queue
    } catch (err) {
      console.error('Failed to submit review decision', err);
    } finally {
      setReviewSubmitting(false);
    }
  };

  const resyncCurrentDocument = async () => {
    if (!result) return;
    setResyncing(true);
    try {
      const outcome = await api.resyncDocument(result.document_id);
      setSyncStatus(outcome.postgres_sync_status);
    } catch (err) {
      console.error('Failed to resync document', err);
    } finally {
      setResyncing(false);
    }
  };

  const needsReview = result && result.validation_status !== 'PASS' && !reviewDecision;

  return (
    <div className="p-4 space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="scada-panel p-3 flex items-center justify-between border-l-4 border-l-cyan-500">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-cyan-500/10 border border-cyan-500/30 rounded text-cyan-400">
            <FileUp className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              DOCUMENT INTELLIGENCE & OCR EXTRACTION
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                LIVE
              </span>
            </div>
            <div className="text-xs text-slate-400 font-mono">
              PyMuPDF native extraction + Docling OCR + regex NER + Layer 5 physics validation
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="scada-panel p-3 border-l-4 border-l-rose-500 text-xs font-mono text-rose-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {error}
        </div>
      )}

      {/* Review Queue -- real GET /api/v1/review/queue data, every document
          module 01 has ever flagged across past sessions, not just the one
          uploaded in this session. Click a row to load it below exactly as
          if it had just been uploaded, reusing the same approve/reject flow. */}
      <div className="scada-panel p-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
            DOCUMENT REVIEW QUEUE
            <span className="text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded">
              LIVE
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">{queue.length} pending</span>
        </div>
        {queueLoading && <div className="text-[11px] font-mono text-slate-500 p-2">Loading queue...</div>}
        {queueError && <div className="text-[11px] font-mono text-rose-400 p-2">{queueError}</div>}
        {!queueLoading && !queueError && queue.length === 0 && (
          <div className="text-[11px] font-mono text-slate-500 p-2">No documents currently awaiting review.</div>
        )}
        {!queueLoading && queue.length > 0 && (
          <div className="max-h-48 overflow-y-auto mt-1">
            <table className="w-full text-[11px] font-mono">
              <thead>
                <tr className="text-slate-500 text-left">
                  <th className="py-1 pr-2 font-normal">Document</th>
                  <th className="py-1 pr-2 font-normal">Well</th>
                  <th className="py-1 pr-2 font-normal">Status</th>
                  <th className="py-1 pr-2 font-normal">Confidence</th>
                  <th className="py-1 pr-2 font-normal">Violations</th>
                  <th className="py-1 font-normal" />
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.document_id} className="border-t border-slate-800/60 hover:bg-slate-900/40">
                    <td className="py-1 pr-2 text-slate-300 truncate max-w-[220px]" title={item.source_filename}>{item.source_filename}</td>
                    <td className="py-1 pr-2 text-slate-400">{item.well_name || '—'}</td>
                    <td className="py-1 pr-2 text-amber-300">{item.validation_status}</td>
                    <td className="py-1 pr-2 text-slate-300">{(item.overall_confidence * 100).toFixed(1)}%</td>
                    <td className="py-1 pr-2 text-slate-300">{item.physics_violations_count}</td>
                    <td className="py-1">
                      <button
                        onClick={() => openQueuedDocument(item.document_id)}
                        className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded"
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Upload zone */}
        <div className="scada-panel p-4 flex flex-col justify-between space-y-3">
          <div>
            <div className="text-xs font-mono font-bold text-slate-200 pb-2 border-b border-slate-800">
              UPLOAD DRILLING REPORT (PDF)
            </div>

            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={onDrop}
              className="mt-3 p-6 border-2 border-dashed border-slate-700 hover:border-cyan-500 rounded-lg text-center space-y-2 cursor-pointer transition bg-slate-900/40"
            >
              {uploading ? (
                <Loader2 className="w-8 h-8 text-cyan-400 mx-auto animate-spin" />
              ) : (
                <Upload className="w-8 h-8 text-cyan-400 mx-auto" />
              )}
              <div className="text-xs font-mono text-slate-200">
                {uploading ? 'Processing…' : 'Drag & Drop PDF or Click to Browse'}
              </div>
              <div className="text-[10px] font-mono text-slate-400">
                Daily Drilling Reports (DDR), Well Completion Reports (WCR), Mud Logs
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                  e.target.value = '';
                }}
              />
            </div>

            {/* One-Click Presets for Hackathon Evaluators */}
            <div className="mt-3 p-2.5 bg-slate-950/70 border border-slate-800 rounded space-y-1.5 font-mono text-[11px]">
              <div className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center justify-between">
                <span>Evaluator One-Click Samples</span>
                <span className="text-cyan-400 text-[9px]">REAL ARCHIVES</span>
              </div>
              <div className="grid grid-cols-1 gap-1.5 pt-1">
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => loadSampleDocument('DDR_WELL-NHK-001_2658m.pdf')}
                  className="px-2 py-1 text-left bg-slate-900 hover:bg-slate-850 hover:border-cyan-500/50 border border-slate-800 text-slate-200 rounded flex items-center justify-between transition disabled:opacity-50"
                  title="Oil India Limited Nahorkatiya well: Barail Sandstone kick and mud loss incident"
                >
                  <span className="truncate">1. NHK-001 DDR (2658m Kick & Loss)</span>
                  <span className="text-[9px] text-amber-400 ml-1 shrink-0">OIL ASSAM</span>
                </button>
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => loadSampleDocument('DDR_WELL-BGJ-007_2905m.pdf')}
                  className="px-2 py-1 text-left bg-slate-900 hover:bg-slate-850 hover:border-cyan-500/50 border border-slate-800 text-slate-200 rounded flex items-center justify-between transition disabled:opacity-50"
                  title="Oil India Limited Baghjan well: High-pressure gas influx incident"
                >
                  <span className="truncate">2. BGJ-007 DDR (2905m Gas Influx)</span>
                  <span className="text-[9px] text-rose-400 ml-1 shrink-0">OIL BAGHJAN</span>
                </button>
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => loadSampleDocument('WELL-15_9-F-12_COMPLETION.pdf')}
                  className="px-2 py-1 text-left bg-slate-900 hover:bg-slate-850 hover:border-cyan-500/50 border border-slate-800 text-slate-200 rounded flex items-center justify-between transition disabled:opacity-50"
                  title="Equinor Volve 15/9-F-12 Well Completion Report: Multi-string casing and formation tops"
                >
                  <span className="truncate">3. Volve 15/9-F-12 WCR (Completion)</span>
                  <span className="text-[9px] text-emerald-400 ml-1 shrink-0">VOLVE WCR</span>
                </button>
              </div>
            </div>

            {jobStatus && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-[11px] font-mono">
                  <span className="text-slate-400">Job {jobId?.slice(0, 8)}… — {jobStatus.status}</span>
                  <span className="text-cyan-400 font-bold">{jobStatus.progress_percent.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-950 h-2 rounded overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-cyan-500 transition-all duration-300"
                    style={{ width: `${jobStatus.progress_percent}%` }}
                  />
                </div>
                <div className="text-[10px] font-mono text-slate-500">
                  {jobStatus.message}
                  {jobStatus.total_pages > 0 && ` (page ${jobStatus.current_page}/${jobStatus.total_pages})`}
                </div>
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-400">
            Requires the document processing service to be running
          </div>
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 scada-panel p-4 flex flex-col justify-between">
          {!result ? (
            <div className="flex items-center justify-center h-full min-h-[200px] text-xs font-mono text-slate-500">
              {uploading ? 'Waiting for extraction to complete…' : 'Upload a document to see real extraction results.'}
            </div>
          ) : (
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
                <div className="flex items-center space-x-2 text-xs font-mono font-bold text-slate-200">
                  <FileText className="w-4 h-4 text-cyan-400" />
                  <span>{result.source_filename}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                      result.validation_status === 'PASS'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                        : 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                    }`}
                  >
                    {result.validation_status}
                  </span>
                </div>
                <div className="flex items-center space-x-1 text-xs font-mono">
                  <button
                    onClick={() => setPreviewTab('formations')}
                    className={`px-2.5 py-1 rounded ${previewTab === 'formations' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Formation Tops ({result.all_formation_tops.length})
                  </button>
                  <button
                    onClick={() => setPreviewTab('npt')}
                    className={`px-2.5 py-1 rounded ${previewTab === 'npt' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    NPT Events ({result.all_npt_records.length})
                  </button>
                  <button
                    onClick={() => setPreviewTab('json')}
                    className={`px-2.5 py-1 rounded ${previewTab === 'json' ? 'bg-cyan-500 text-slate-950 font-bold' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    Raw JSON
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-3 text-xs font-mono">
                <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div className="text-slate-400 text-[10px]">CONFIDENCE</div>
                  <div className="text-slate-200 font-bold">{(result.overall_confidence * 100).toFixed(0)}%</div>
                </div>
                <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div className="text-slate-400 text-[10px]">PAGES</div>
                  <div className="text-slate-200 font-bold">{result.pages_processed}/{result.total_pages} ({result.scanned_pages} scanned)</div>
                </div>
                <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div className="text-slate-400 text-[10px]">PHYSICS VIOLATIONS</div>
                  <div className={`font-bold ${result.physics_violations_count > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                    {result.physics_violations_count}
                  </div>
                </div>
                <div className="bg-slate-900/80 p-2 rounded border border-slate-800">
                  <div className="text-slate-400 text-[10px]">TOTAL NPT</div>
                  <div className="text-slate-200 font-bold">{result.total_npt_hours.toFixed(1)} hrs</div>
                </div>
              </div>

              {previewTab === 'formations' && (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-2">Formation</th>
                        <th className="p-2">Top MD</th>
                        <th className="p-2">Top TVD</th>
                        <th className="p-2">Lithology</th>
                        <th className="p-2">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {result.all_formation_tops.map((f, i) => (
                        <tr key={i} className="hover:bg-slate-900/40">
                          <td className="p-2 text-amber-300 font-bold">{f.formation_name}</td>
                          <td className="p-2">{fieldValue(f.top_md_m)}</td>
                          <td className="p-2">{fieldValue(f.top_tvd_m)}</td>
                          <td className="p-2 text-slate-400">{f.lithology_description || '—'}</td>
                          <td className="p-2 text-emerald-400 font-bold">{(f.confidence * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                      {result.all_formation_tops.length === 0 && (
                        <tr><td colSpan={5} className="p-3 text-center text-slate-500">No formation tops extracted from this document.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {previewTab === 'npt' && (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-900 text-slate-400 text-[10px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-2">IADC Code</th>
                        <th className="p-2">Description</th>
                        <th className="p-2">Depth</th>
                        <th className="p-2">NPT Hours</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {result.all_npt_records.map((n, i) => (
                        <tr key={i} className="hover:bg-slate-900/40">
                          <td className="p-2 text-cyan-400 font-bold">{n.iadc_code || 'n/a'}</td>
                          <td className="p-2 text-slate-300">{n.description}</td>
                          <td className="p-2">{fieldValue(n.depth_md_m)}</td>
                          <td className="p-2 font-bold">{fieldValue(n.npt_hours)}</td>
                        </tr>
                      ))}
                      {result.all_npt_records.length === 0 && (
                        <tr><td colSpan={4} className="p-3 text-center text-slate-500">No NPT records extracted from this document.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {previewTab === 'json' && (
                <div className="mt-3 bg-slate-950 p-3 rounded border border-slate-800 font-mono text-[11px] text-cyan-300 max-h-96 overflow-y-auto">
                  <pre>{JSON.stringify(result, null, 2)}</pre>
                </div>
              )}

              {!needsReview && !reviewDecision && result.validation_status === 'PASS' && result.review_decision === 'approved' && (
                <div className="mt-3 p-2 text-xs font-mono text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5" />
                  No review needed — automatically added to the shared knowledge base.
                </div>
              )}
              {needsReview && (
                <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded flex items-center justify-between text-xs font-mono">
                  <span className="text-amber-300">
                    This document needs human review before it enters the shared knowledge base.
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      disabled={reviewSubmitting}
                      onClick={() => submitDecision('approved')}
                      className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded flex items-center gap-1"
                    >
                      <ThumbsUp className="w-3 h-3" /> Approve
                    </button>
                    <button
                      disabled={reviewSubmitting}
                      onClick={() => submitDecision('rejected')}
                      className="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-slate-100 font-bold rounded flex items-center gap-1"
                    >
                      <ThumbsDown className="w-3 h-3" /> Reject
                    </button>
                  </div>
                </div>
              )}
              {reviewDecision && (
                <div className="mt-3 p-2 text-xs font-mono text-slate-300 flex items-center gap-1.5">
                  {reviewDecision === 'approved' ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                  Review recorded: {reviewDecision}
                  {decisionOutcome && reviewDecision === 'approved' && (
                    decisionOutcome.events_migrated_to_knowledge_base > 0 ? (
                      <span className="text-slate-400">
                        — {decisionOutcome.events_migrated_to_knowledge_base} event{decisionOutcome.events_migrated_to_knowledge_base === 1 ? '' : 's'} added to the shared knowledge base
                        {decisionOutcome.events_skipped > 0 && `, ${decisionOutcome.events_skipped} could not be matched to a known well or hazard type`}
                      </span>
                    ) : decisionOutcome.events_skipped > 0 ? (
                      <span className="text-slate-400">
                        — {decisionOutcome.events_skipped} extracted event{decisionOutcome.events_skipped === 1 ? '' : 's'} could not be matched to a known well or hazard type, so none were added to the shared knowledge base
                      </span>
                    ) : null
                  )}
                </div>
              )}

              {/* Pass 5: shared-database sync state for this document —
                  honest tri-state copy (never a raw exception), with a
                  retry action wired to the idempotent /resync route when
                  a sync attempt failed or couldn't reach the database. */}
              {syncStatus && (() => {
                const copy = syncStatusCopy(syncStatus);
                const toneClass = copy.tone === 'ok'
                  ? 'text-emerald-400'
                  : copy.tone === 'warn'
                  ? 'text-amber-300'
                  : 'text-slate-500';
                return (
                  <div className={`mt-1 px-2 text-[11px] font-mono flex items-center gap-2 ${toneClass}`}>
                    <span>{copy.label}</span>
                    {copy.retry && (
                      <button
                        onClick={resyncCurrentDocument}
                        disabled={resyncing}
                        className="px-1.5 py-0.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded disabled:opacity-50"
                      >
                        {resyncing ? 'Retrying…' : 'Retry'}
                      </button>
                    )}
                  </div>
                );
              })()}

              <div className="mt-3 pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-500 flex items-center justify-between">
                <span>document_id: {result.document_id}</span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowPdfViewer(true)}
                    className="flex items-center gap-1 text-cyan-400 hover:underline"
                  >
                    <BookOpen className="w-3 h-3" /> View Source PDF
                  </button>
                  <a
                    href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(result, null, 2))}`}
                    download={`${result.document_id}.json`}
                    className="flex items-center gap-1 text-cyan-400 hover:underline"
                  >
                    <Download className="w-3 h-3" /> Export JSON
                  </a>
                </div>
              </div>
              {showPdfViewer && (
                <PdfEvidenceViewer
                  onClose={() => setShowPdfViewer(false)}
                  documentId={result.document_id}
                  contextLabel={result.source_filename}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
