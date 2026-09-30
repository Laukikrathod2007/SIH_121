import React, { useEffect } from 'react';
import { ExternalLink, FileText, X } from 'lucide-react';
import { useNwis } from '../state/nwis';
import { api } from '../lib/api';

/** Right-side drawer showing the cited source PDF, opened at the cited page. */
export const EvidenceViewer: React.FC = () => {
  const { evidence, closeEvidence } = useNwis();

  useEffect(() => {
    if (!evidence) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closeEvidence();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [evidence, closeEvidence]);

  if (!evidence) return null;
  const url = api.evidenceUrl(evidence.doc, evidence.page);

  return (
    <div className="fixed inset-0 z-[1100] flex justify-end" role="dialog" aria-modal="true" aria-label="Source document">
      <button className="absolute inset-0 bg-ink/20" aria-label="Close" onClick={closeEvidence} />
      <div className="relative w-[min(760px,92vw)] h-full bg-surface border-l border-line shadow-pop flex flex-col animate-slide-in">
        <div className="h-14 px-4 flex items-center gap-3 border-b border-line">
          <FileText className="w-4 h-4 text-accent" />
          <div className="min-w-0 flex-1">
            <div className="text-[13px] font-medium truncate">{evidence.title || evidence.doc}</div>
            <div className="text-[11px] text-ink-3 truncate">
              Source document{evidence.page ? ` · opened at page ${evidence.page}` : ''} · {evidence.doc}
            </div>
          </div>
          <a href={url} target="_blank" rel="noreferrer" className="text-xs text-ink-2 hover:text-ink inline-flex items-center gap-1">
            Open in tab <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <button onClick={closeEvidence} aria-label="Close" className="p-1.5 rounded-md hover:bg-sunken"><X className="w-4 h-4" /></button>
        </div>
        <iframe key={url} src={url} title="Source document" className="flex-1 w-full bg-sunken" />
      </div>
    </div>
  );
};
