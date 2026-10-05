import React, { useEffect, useRef, useState } from 'react';
import { X, ChevronLeft, ChevronRight, Loader2, AlertTriangle, FileWarning, ZoomIn, ZoomOut } from 'lucide-react';
import * as pdfjsLib from 'pdfjs-dist';
// Vite-native worker import (`?url` returns the built asset's served URL) —
// pdfjs-dist requires its worker to be reachable at a real URL, it can't run
// inline. This must point at the .mjs worker matching the installed
// pdfjs-dist version (see package.json) or rendering silently hangs.
// eslint-disable-next-line import/no-unresolved
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { api } from '../services/api';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

// ============================================================================
// PdfEvidenceViewer — the "1-click PDF proof" evidence modal.
//
// Fetches the REAL uploaded PDF from module 01
// (GET /api/v1/documents/{doc_id}/file, added alongside this component) and
// renders it client-side with pdfjs-dist, jumping straight to the page a
// given extracted field/event/formation/NPT record came from.
//
// HONEST LIMITATION — disclosed here and in the UI, not papered over:
// modules/01_document_intelligence's schema (models/schemas.py: BoundingBox)
// supports per-field pixel bounding boxes, and
// pipeline/tier1_native_extractor.py even has a get_word_bounding_boxes()
// helper that can compute them — but nothing in tier3_entity_extractor.py's
// _make_field() calls ever actually passes bbox=, so no extracted field in
// this codebase carries real coordinates today. This viewer therefore only
// navigates to and displays the correct PAGE. It does NOT draw a highlight
// box around the specific value — doing that without real coordinates would
// mean faking a box, which this project's zero-hallucination design
// philosophy (see search/knowledge_search.py, HistoricalIntelligencePage's
// "Illustrative summary" labeling) explicitly avoids.
//
// Two ways to open this viewer:
//   - `documentId` — already known (e.g. DocumentIngestionPage, which has
//     the module 01 document_id in scope directly after an ingest).
//   - `sourceFilename` — only a filename string is known (e.g.
//     HistoricalIntelligencePage's events come from module 02's synthetic
//     testbed, whose `source_document` is a filename like
//     "DDR_WELL-NHK-001_2500m.pdf" that was never actually run through
//     module 01's ingestion pipeline). In that case this component looks the
//     filename up against GET /api/v1/results (module 01's real processed
//     documents) and, if there's no match, says so plainly instead of
//     fabricating a viewer for a document that was never ingested.
// ============================================================================

interface PdfEvidenceViewerProps {
  onClose: () => void;
  /** 1-indexed page to jump to on open. */
  page?: number | null;
  /** Known module 01 document_id — skips the filename lookup entirely. */
  documentId?: string;
  /** module 02 event's source_document filename — resolved against module 01's real archive. */
  sourceFilename?: string;
  /** Label shown in the header, e.g. the well_id or event_id this evidence backs. */
  contextLabel?: string;
}

type ViewerStatus = 'resolving' | 'loading' | 'ready' | 'not_found' | 'error';

export const PdfEvidenceViewer: React.FC<PdfEvidenceViewerProps> = ({
  onClose,
  page,
  documentId,
  sourceFilename,
  contextLabel,
}) => {
  const [status, setStatus] = useState<ViewerStatus>('resolving');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [resolvedDocId, setResolvedDocId] = useState<string | null>(documentId ?? null);
  const [resolvedFilename, setResolvedFilename] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(Math.max(1, page || 1));
  const [scale, setScale] = useState<number>(1.35);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pdfDocRef = useRef<pdfjsLib.PDFDocumentProxy | null>(null);
  const renderTaskRef = useRef<ReturnType<pdfjsLib.PDFPageProxy['render']> | null>(null);

  // Step 1: resolve a document_id (direct, or by looking up source_filename
  // against module 01's real processed-document list).
  useEffect(() => {
    let cancelled = false;

    const resolve = async () => {
      if (documentId) {
        setResolvedDocId(documentId);
        return;
      }
      if (!sourceFilename) {
        setStatus('error');
        setErrorMessage('No document_id or source_filename was provided to the evidence viewer.');
        return;
      }
      setStatus('resolving');
      try {
        const listing = await api.listResults();
        const match = listing.results.find((r: any) => r.source_filename === sourceFilename);
        if (cancelled) return;
        if (!match) {
          setStatus('not_found');
          return;
        }
        setResolvedDocId(match.document_id);
      } catch (err) {
        if (cancelled) return;
        setStatus('error');
        setErrorMessage('Could not look up this source document. Contact your system administrator if this persists.');
      }
    };

    resolve();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, sourceFilename]);

  // Step 2: once we have a document_id, fetch the real PDF bytes and load them into pdfjs.
  useEffect(() => {
    if (!resolvedDocId) return;
    let cancelled = false;

    const load = async () => {
      setStatus('loading');
      try {
        const bytes = await api.getDocumentFile(resolvedDocId);
        if (cancelled) return;
        const loadingTask = pdfjsLib.getDocument({ data: bytes });
        const pdf = await loadingTask.promise;
        if (cancelled) return;
        pdfDocRef.current = pdf;
        setNumPages(pdf.numPages);
        setCurrentPage((p) => Math.min(Math.max(1, p), pdf.numPages));
        setStatus('ready');
      } catch (err) {
        if (cancelled) return;
        console.error('Failed to load PDF evidence', err);
        setStatus('error');
        setErrorMessage(
          'Could not load the source document. Requires the document processing service to be running — ' +
            'contact your system administrator if this persists.',
        );
      }
    };

    load();
    return () => {
      cancelled = true;
      pdfDocRef.current?.destroy();
      pdfDocRef.current = null;
    };
  }, [resolvedDocId]);

  // Step 3: render the current page to canvas whenever page/scale changes.
  useEffect(() => {
    const pdf = pdfDocRef.current;
    if (!pdf || status !== 'ready') return;
    let cancelled = false;

    const renderPage = async () => {
      try {
        const pageProxy = await pdf.getPage(currentPage);
        if (cancelled) return;
        const viewport = pageProxy.getViewport({ scale });
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        // Cancel any in-flight render before starting a new one (rapid page
        // clicks otherwise throw "cannot use the same canvas" from pdfjs).
        renderTaskRef.current?.cancel();
        const task = pageProxy.render({ canvasContext: ctx, viewport });
        renderTaskRef.current = task;
        await task.promise;
      } catch (err: any) {
        if (err?.name !== 'RenderingCancelledException') {
          console.error('Failed to render PDF page', err);
        }
      }
    };

    renderPage();
    return () => {
      cancelled = true;
    };
  }, [currentPage, scale, status]);

  const goToPage = (delta: number) => {
    setCurrentPage((p) => Math.min(Math.max(1, p + delta), numPages || p));
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="scada-panel w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 shrink-0">
          <div className="min-w-0">
            <div className="text-sm font-bold text-slate-100 flex items-center gap-2">
              SOURCE DOCUMENT
              <span className="text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 px-1.5 py-0.5 rounded">
                EVIDENCE
              </span>
            </div>
            <div className="text-xs font-mono text-slate-400 truncate">
              {contextLabel || resolvedFilename || sourceFilename || resolvedDocId || 'Loading…'}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition shrink-0"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Honest limitation banner */}
        <div className="px-4 py-2 bg-amber-500/10 border-b border-amber-500/20 text-[11px] font-mono text-amber-300 flex items-start gap-2 shrink-0">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <span>
            Page-level navigation only. This pipeline does not store per-field pixel bounding boxes, so no
            highlight box is drawn around the specific value — scan the displayed page for it.
          </span>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto bg-slate-950 flex items-center justify-center p-4">
          {status === 'resolving' && (
            <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Looking up source document…
            </div>
          )}
          {status === 'loading' && (
            <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading source document…
            </div>
          )}
          {status === 'not_found' && (
            <div className="max-w-md text-center text-xs font-mono text-slate-300 space-y-2">
              <FileWarning className="w-8 h-8 text-amber-400 mx-auto" />
              <div className="font-bold text-amber-300">Source document not available</div>
              <div className="text-slate-400">
                "{sourceFilename}" does not match any document on file in the document archive.
                This record was generated as part of the demonstration dataset and was never itself
                uploaded through the document ingestion workflow, so no original PDF is available to
                display — this message says so honestly rather than fabricating a viewer.
              </div>
            </div>
          )}
          {status === 'error' && (
            <div className="max-w-md text-center text-xs font-mono text-rose-300 space-y-2">
              <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
              <div>{errorMessage}</div>
            </div>
          )}
          {status === 'ready' && <canvas ref={canvasRef} className="shadow-2xl" />}
        </div>

        {/* Footer: page nav */}
        {status === 'ready' && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-slate-800 shrink-0 text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setScale((s) => Math.max(0.5, s - 0.15))}
                className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
                aria-label="Zoom out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <button
                onClick={() => setScale((s) => Math.min(3, s + 0.15))}
                className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
                aria-label="Zoom in"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => goToPage(-1)}
                disabled={currentPage <= 1}
                className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent transition"
                aria-label="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-slate-200">
                Page <span className="text-cyan-400 font-bold">{currentPage}</span> / {numPages}
              </span>
              <button
                onClick={() => goToPage(1)}
                disabled={currentPage >= numPages}
                className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-slate-800 disabled:opacity-30 disabled:hover:bg-transparent transition"
                aria-label="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            <span className="text-slate-500">document_id: {resolvedDocId}</span>
          </div>
        )}
      </div>
    </div>
  );
};
