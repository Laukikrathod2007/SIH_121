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
import { DocumentExtractionResult, ExtractedField, JobStatusResponse } from '../types';
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
          }
          setUploading(false);
        } else if (status.status === 'FAILED') {
          if (pollRef.current) clearInterval(pollRef.current);
          setError(status.error || status.message || 'Extraction failed.');
          setUploading(false);
        }
      } catch (err) {
        if (pollRef.current) clearInterval(pollRef.current);
        setError('Lost connection to module 01 while polling job status (is it still running on :8001?).');
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
    setUploading(true);
    try {
      const job = await api.ingestDocument(file);
      setJobId(job.job_id);
      startPolling(job.job_id);
    } catch (err) {
      setError('Failed to reach /api/v1/ingest on module 01 (is it running on :8001?).');
      setUploading(false);
      console.error(err);
    }
  }, [startPolling]);

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  const submitDecision = async (decision: 'approved' | 'rejected') => {
    if (!result) return;
    setReviewSubmitting(true);
    try {
      await api.submitReviewDecision(result.document_id, { reviewer: 'frontend-operator', decision });
      setReviewDecision(decision);
    } catch (err) {
      console.error('Failed to submit review decision', err);
    } finally {
      setReviewSubmitting(false);
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
              MODULE 01: DOCUMENT INTELLIGENCE & OCR EXTRACTION
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                LIVE: POST /api/v1/ingest
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
            Requires modules/01_document_intelligence running on :8001 (python run_server.py)
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

              {needsReview && (
                <div className="mt-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded flex items-center justify-between text-xs font-mono">
                  <span className="text-amber-300">
                    This document needs human review (POST /api/v1/review/{result.document_id}/decision).
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
                </div>
              )}

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
