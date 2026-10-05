/**
 * EvidenceViewer — drawer that shows a source PDF (opened at a specific page)
 * so a citation like "Daily drilling report · HGJ-011 · p.3" is never just
 * text — it opens the actual document.
 *
 * This needs a server that can serve the PDF bytes (browsers can't read
 * arbitrary local files via a URL for security reasons). The bundled
 * server/index.js does this in ~30 lines — run it alongside your frontend,
 * or point `apiBase` at your own backend's equivalent endpoint.
 *
 * Requires: react, lucide-react.
 */

import React, { useEffect } from 'react';
import { ExternalLink, FileText, X } from 'lucide-react';

export interface Evidence {
  doc: string;
  page?: number | null;
  title?: string;
}

export interface EvidenceViewerProps {
  evidence: Evidence | null;
  onClose: () => void;
  /** Base URL of the PDF-serving endpoint, e.g. 'http://localhost:4000/evidence'. */
  apiBase: string;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({ evidence, onClose, apiBase }) => {
  useEffect(() => {
    if (!evidence) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [evidence, onClose]);

  if (!evidence) return null;
  const url = `${apiBase}?name=${encodeURIComponent(evidence.doc)}${evidence.page ? `#page=${evidence.page}` : ''}`;

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1100, display: 'flex', justifyContent: 'flex-end', fontFamily: 'system-ui, sans-serif' }} role="dialog" aria-modal="true">
      <button onClick={onClose} aria-label="Close" style={{ position: 'absolute', inset: 0, background: 'rgba(23,25,29,0.2)', border: 'none', cursor: 'pointer' }} />
      <div style={{ position: 'relative', width: 'min(760px, 92vw)', height: '100%', background: '#fff', borderLeft: '1px solid #e3e0d8', boxShadow: '0 12px 32px -8px rgba(22,24,29,0.18)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ height: 56, padding: '0 16px', display: 'flex', alignItems: 'center', gap: 12, borderBottom: '1px solid #e3e0d8' }}>
          <FileText size={16} color="#0e5a69" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{evidence.title || evidence.doc}</div>
            <div style={{ fontSize: 11, color: '#868a91', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              Source document{evidence.page ? ` · opened at page ${evidence.page}` : ''} · {evidence.doc}
            </div>
          </div>
          <a href={url} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#4a4e56', display: 'inline-flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
            Open in tab <ExternalLink size={14} />
          </a>
          <button onClick={onClose} aria-label="Close" style={{ padding: 6, borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', display: 'flex' }}>
            <X size={16} />
          </button>
        </div>
        <iframe key={url} src={url} title="Source document" style={{ flex: 1, width: '100%', border: 'none', background: '#efede7' }} />
      </div>
    </div>
  );
};

export default EvidenceViewer;
