import React, { useMemo, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUp, Bot, Terminal, Printer, Bookmark, Users } from 'lucide-react';

interface DocsTableOfContentsProps {
  content: string;
}

interface HeadingItem {
  id: string;
  text: string;
  level: number;
}

export const DocsTableOfContents: React.FC<DocsTableOfContentsProps> = ({ content }) => {
  const [activeId, setActiveId] = useState<string>('');

  const headings: HeadingItem[] = useMemo(() => {
    if (!content) return [];
    const lines = content.split('\n');
    const result: HeadingItem[] = [];

    for (const line of lines) {
      const h2Match = line.match(/^##\s+(.+)$/);
      const h3Match = line.match(/^###\s+(.+)$/);

      if (h2Match) {
        const rawText = h2Match[1].trim();
        if (!rawText.startsWith('#')) {
          const cleanText = rawText.replace(/[*`_]/g, '').trim();
          const id = cleanText
            .toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, '-');
          result.push({ id, text: cleanText, level: 2 });
        }
      } else if (h3Match) {
        const rawText = h3Match[1].trim();
        if (!rawText.startsWith('#')) {
          const cleanText = rawText.replace(/[*`_]/g, '').trim();
          const id = cleanText
            .toLowerCase()
            .replace(/[^\w\s-]/g, '')
            .replace(/\s+/g, '-');
          result.push({ id, text: cleanText, level: 3 });
        }
      }
    }

    return result;
  }, [content]);

  useEffect(() => {
    if (headings.length === 0) return;
    setActiveId(headings[0].id);

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      {
        rootMargin: '-80px 0% -60% 0%',
        threshold: 0.1,
      }
    );

    headings.forEach((h) => {
      const el = document.getElementById(h.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [headings]);

  const scrollToHeading = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveId(id);
    }
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    const mainEl = document.getElementById('docs-content-viewport');
    if (mainEl) mainEl.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (headings.length === 0) {
    return null;
  }

  return (
    <aside className="hidden xl:block w-64 shrink-0 py-6 px-4 space-y-6 text-xs sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto select-none border-l border-stone-200 bg-[#fafaf9]">
      <div>
        <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-stone-500 font-bold mb-3">
          <Bookmark className="w-3.5 h-3.5 text-stone-700" />
          <span>ON THIS PAGE</span>
        </div>

        <nav className="space-y-1">
          {headings.map((h, i) => {
            const isActive = activeId === h.id || (i === 0 && !activeId);
            return (
              <button
                key={`${h.id}-${i}`}
                onClick={() => scrollToHeading(h.id)}
                className={`block text-left w-full truncate transition-all py-1 ${
                  h.level === 3 ? 'pl-4 text-[11px]' : 'pl-1 font-medium'
                } ${
                  isActive
                    ? 'text-stone-950 font-bold border-l-2 border-stone-900 -ml-px'
                    : 'text-stone-500 hover:text-stone-800'
                }`}
                title={h.text}
              >
                {h.text}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Helpful Action Links */}
      <div className="pt-4 border-t border-stone-200 space-y-2">
        <button
          onClick={scrollToTop}
          className="flex items-center gap-2 text-stone-600 hover:text-stone-900 transition text-[11px] font-mono"
        >
          <ArrowUp className="w-3.5 h-3.5 text-stone-500" />
          <span>Back to top</span>
        </button>

        <Link
          to="/app/copilot"
          className="flex items-center gap-2 text-stone-600 hover:text-stone-950 transition text-[11px] font-mono"
        >
          <Bot className="w-3.5 h-3.5 text-stone-700" />
          <span>Ask Subsurface Copilot</span>
        </Link>

        <Link
          to="/app"
          className="flex items-center gap-2 text-stone-600 hover:text-stone-950 transition text-[11px] font-mono"
        >
          <Terminal className="w-3.5 h-3.5 text-stone-700" />
          <span>Launch Rig Cockpit</span>
        </Link>

        <button
          onClick={() => window.print()}
          className="flex items-center gap-2 text-stone-600 hover:text-stone-900 transition text-[11px] font-mono"
        >
          <Printer className="w-3.5 h-3.5 text-stone-500" />
          <span>Print / Save PDF</span>
        </button>
      </div>

      {/* Evaluation Context Card */}
      <div className="p-3 rounded-sm bg-white border border-stone-200 text-[11px] space-y-1.5 font-mono shadow-2xs">
        <div className="flex items-center gap-1.5 font-bold text-stone-900">
          <Users className="w-3.5 h-3.5 text-[#c96a12]" />
          <span>Midnight Ciphers</span>
        </div>
        <p className="text-stone-600 leading-relaxed text-[10px]">
          Smart India Hackathon 2026 · Problem Statement SIH26121 for Oil India Limited (Duliajan).
        </p>
      </div>
    </aside>
  );
};
