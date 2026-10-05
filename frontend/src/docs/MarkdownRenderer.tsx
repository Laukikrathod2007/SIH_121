import React, { useEffect, useRef, useState } from 'react';
import { marked } from 'marked';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import mermaid from 'mermaid';
import Prism from 'prismjs';
import 'prismjs/themes/prism-tomorrow.css';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-typescript';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-sql';
import 'prismjs/components/prism-json';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-bash';
import {
  Check,
  Copy,
  Info,
  AlertTriangle,
  Flame,
  Lightbulb,
  ShieldAlert,
  Maximize2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
} from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

// Initialize mermaid once
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    darkMode: true,
    background: '#121722',
    primaryColor: '#c96a12',
    primaryTextColor: '#f8fafc',
    primaryBorderColor: '#a75208',
    lineColor: '#94a3b8',
    secondaryColor: '#1e2638',
    tertiaryColor: '#182030',
  },
  securityLevel: 'loose',
});

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [renderedHtml, setRenderedHtml] = useState<string>('');
  const [mermaidDiagrams, setMermaidDiagrams] = useState<Map<string, string>>(new Map());
  const [selectedMermaid, setSelectedMermaid] = useState<{ id: string; code: string; svg: string } | null>(null);

  // Preprocess text to parse Math, Mermaid blocks, and GitHub alert callouts
  useEffect(() => {
    let processed = content;

    // 1. Preprocess Math: Replace block math $$...$$ with placeholders
    const mathBlocks: string[] = [];
    processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (_, math) => {
      const idx = mathBlocks.length;
      try {
        const rendered = katex.renderToString(math.trim(), {
          displayMode: true,
          throwOnError: false,
        });
        mathBlocks.push(`<div class="my-5 overflow-x-auto py-2 text-center select-all">${rendered}</div>`);
      } catch (err) {
        mathBlocks.push(`<pre class="text-rose-400 font-mono text-xs">Error rendering math: ${math}</pre>`);
      }
      return `%%MATH_BLOCK_${idx}%%`;
    });

    // 2. Preprocess Inline Math: Replace $x$ with placeholder (skip $1M, $500, etc.)
    const inlineMath: string[] = [];
    processed = processed.replace(/(?<!\\|\$)\$([^\$\n]+?)\$(?!\$)/g, (fullMatch, expr) => {
      // Skip if looks like currency ($5M, $25,000, $15-$30M)
      if (/^\s*\d+[\d,\.]*\s*(?:M|B|k|K|USD|dollars|hours)?\s*$/i.test(expr)) {
        return fullMatch;
      }
      const idx = inlineMath.length;
      try {
        const rendered = katex.renderToString(expr.trim(), {
          displayMode: false,
          throwOnError: false,
        });
        inlineMath.push(`<span class="inline-math px-1">${rendered}</span>`);
      } catch {
        return fullMatch;
      }
      return `%%INLINE_MATH_${idx}%%`;
    });

    // 3. Extract Mermaid blocks before Marked parses them
    const mermaidCodes: Map<string, string> = new Map();
    let mermaidCounter = 0;
    processed = processed.replace(/```mermaid\s*([\s\S]+?)\s*```/g, (_, code) => {
      const id = `mermaid-container-${Date.now()}-${mermaidCounter++}`;
      mermaidCodes.set(id, code.trim());
      return `<div class="mermaid-target my-6 rounded-lg border border-stone-200 bg-white p-4 overflow-hidden relative group shadow-2xs" data-mermaid-id="${id}">
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-stone-200 text-[11px] font-mono text-stone-500 uppercase tracking-wider">
          <span class="inline-flex items-center gap-1.5 font-bold"><span class="w-2 h-2 rounded-full bg-stone-900"></span>Architecture Diagram</span>
          <div class="flex items-center gap-1.5">
            <button class="mermaid-copy-btn px-2 py-0.5 rounded border border-stone-300 bg-white hover:bg-stone-50 text-stone-700 text-[11px] font-mono transition" data-code="${encodeURIComponent(code.trim())}">Copy Code</button>
            <button class="mermaid-expand-btn px-2 py-0.5 rounded border border-stone-300 bg-white hover:bg-stone-50 text-stone-700 text-[11px] font-mono transition" data-id="${id}">Full View</button>
          </div>
        </div>
        <div id="${id}" class="mermaid-render-area flex justify-center overflow-x-auto min-h-[140px] items-center p-2 bg-[#fafaf9] rounded">
          <div class="text-xs text-stone-400 font-mono animate-pulse">Rendering technical diagram...</div>
        </div>
      </div>`;
    });

    // 4. Configure Marked renderer for Custom Headings, Links, Callouts, and Code Highlighting
    const renderer = new marked.Renderer();

    // Custom Headings with Anchors
    renderer.heading = ({ text, depth }) => {
      const slug = text
        .toLowerCase()
        .replace(/<[^>]*>/g, '')
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-');

      const sizeClasses: Record<number, string> = {
        1: 'text-2xl md:text-3xl font-serif font-bold text-stone-900 tracking-tight mt-8 mb-4 pb-2 border-b border-stone-200 flex items-center group',
        2: 'text-xl md:text-2xl font-bold text-stone-900 tracking-tight mt-8 mb-3 pb-1 border-b border-stone-200/80 flex items-center group',
        3: 'text-lg md:text-xl font-semibold text-stone-900 mt-6 mb-2 flex items-center group',
        4: 'text-base font-semibold text-stone-800 mt-4 mb-2',
      };

      const classes = sizeClasses[depth] || 'text-base font-medium text-stone-800 my-2';
      return `<h${depth} id="${slug}" class="${classes}">
        <span>${text}</span>
        <a href="#${slug}" class="ml-2 text-stone-400 hover:text-stone-900 opacity-0 group-hover:opacity-100 transition font-mono text-sm" aria-label="Direct link to heading">#</a>
      </h${depth}>`;
    };

    // Custom Code Blocks with Copy Button
    renderer.code = ({ text, lang }) => {
      const language = lang || 'text';
      let highlighted = text;
      try {
        if (Prism.languages[language]) {
          highlighted = Prism.highlight(text, Prism.languages[language], language);
        }
      } catch {
        highlighted = text;
      }

      return `<div class="relative my-5 rounded-lg border border-slate-800 bg-[#0f172a] overflow-hidden text-sm font-mono group shadow-2xs">
        <div class="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs text-slate-400">
          <span class="uppercase tracking-wider font-semibold text-[11px]">${language}</span>
          <button class="code-copy-btn inline-flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition" data-code="${encodeURIComponent(text)}">
            <span>Copy</span>
          </button>
        </div>
        <pre class="p-4 overflow-x-auto text-[13px] leading-relaxed text-slate-200"><code>${highlighted}</code></pre>
      </div>`;
    };

    // Custom Tables with SCADA Styling
    renderer.table = function (token: any) {
      let headerCells = '';
      if (Array.isArray(token.header)) {
        for (const cell of token.header) {
          headerCells += this.tablecell(cell);
        }
      }
      const headerRow = this.tablerow({ text: headerCells });

      let bodyRows = '';
      if (Array.isArray(token.rows)) {
        for (const row of token.rows) {
          let rowCells = '';
          if (Array.isArray(row)) {
            for (const cell of row) {
              rowCells += this.tablecell(cell);
            }
          }
          bodyRows += this.tablerow({ text: rowCells });
        }
      }

      return `<div class="my-6 overflow-x-auto rounded-lg border border-stone-200 bg-white shadow-2xs">
        <table class="w-full text-left text-xs sm:text-sm border-collapse">
          <thead class="bg-stone-100 text-xs uppercase font-mono font-bold text-stone-800 border-b border-stone-200">
            ${headerRow}
          </thead>
          <tbody class="divide-y divide-stone-200 text-stone-800">
            ${bodyRows}
          </tbody>
        </table>
      </div>`;
    };

    // Custom Blockquotes to Detect GitHub Alert Callouts
    renderer.blockquote = ({ text }) => {
      const trimmed = text.trim();
      if (trimmed.includes('[!NOTE]')) {
        const clean = trimmed.replace(/\[!NOTE\]\s*/i, '');
        return `<div class="my-4 rounded border-l-4 border-blue-600 bg-blue-50/70 p-4 text-sm text-blue-950">
          <div class="font-bold text-blue-800 flex items-center gap-1.5 mb-1 text-xs uppercase font-mono tracking-wider">Note</div>
          <div>${clean}</div>
        </div>`;
      }
      if (trimmed.includes('[!TIP]')) {
        const clean = trimmed.replace(/\[!TIP\]\s*/i, '');
        return `<div class="my-4 rounded border-l-4 border-emerald-600 bg-emerald-50/70 p-4 text-sm text-emerald-950">
          <div class="font-bold text-emerald-800 flex items-center gap-1.5 mb-1 text-xs uppercase font-mono tracking-wider">Tip</div>
          <div>${clean}</div>
        </div>`;
      }
      if (trimmed.includes('[!IMPORTANT]')) {
        const clean = trimmed.replace(/\[!IMPORTANT\]\s*/i, '');
        return `<div class="my-4 rounded border-l-4 border-amber-600 bg-amber-50/70 p-4 text-sm text-amber-950">
          <div class="font-bold text-amber-800 flex items-center gap-1.5 mb-1 text-xs uppercase font-mono tracking-wider">Important</div>
          <div>${clean}</div>
        </div>`;
      }
      if (trimmed.includes('[!WARNING]')) {
        const clean = trimmed.replace(/\[!WARNING\]\s*/i, '');
        return `<div class="my-4 rounded border-l-4 border-orange-600 bg-orange-50/70 p-4 text-sm text-orange-950">
          <div class="font-bold text-orange-800 flex items-center gap-1.5 mb-1 text-xs uppercase font-mono tracking-wider">Warning</div>
          <div>${clean}</div>
        </div>`;
      }
      if (trimmed.includes('[!CAUTION]')) {
        const clean = trimmed.replace(/\[!CAUTION\]\s*/i, '');
        return `<div class="my-4 rounded border-l-4 border-rose-600 bg-rose-50/70 p-4 text-sm text-rose-950">
          <div class="font-bold text-rose-800 flex items-center gap-1.5 mb-1 text-xs uppercase font-mono tracking-wider">Caution</div>
          <div>${clean}</div>
        </div>`;
      }

      return `<blockquote class="my-4 border-l-2 border-stone-300 pl-4 italic text-stone-600">${text}</blockquote>`;
    };

    marked.setOptions({ renderer, gfm: true, breaks: true });

    let html = marked.parse(processed) as string;

    // Restore math blocks and inline math
    html = html.replace(/%%MATH_BLOCK_(\d+)%%/g, (_, idx) => mathBlocks[parseInt(idx, 10)] || '');
    html = html.replace(/%%INLINE_MATH_(\d+)%%/g, (_, idx) => inlineMath[parseInt(idx, 10)] || '');

    setRenderedHtml(html);
    setMermaidDiagrams(mermaidCodes);
  }, [content]);

  // Render Mermaid diagrams into their placeholder containers
  useEffect(() => {
    if (!containerRef.current || mermaidDiagrams.size === 0) return;

    mermaidDiagrams.forEach(async (code, id) => {
      const targetEl = containerRef.current?.querySelector(`#${id}`);
      if (!targetEl) return;

      try {
        const uniqueId = `mermaid-svg-${id.replace(/[^\w-]/g, '')}`;
        const { svg } = await mermaid.render(uniqueId, code);
        targetEl.innerHTML = svg;

        // Make rendered SVG responsive
        const svgEl = targetEl.querySelector('svg');
        if (svgEl) {
          svgEl.style.maxWidth = '100%';
          svgEl.style.height = 'auto';
        }
      } catch (err) {
        console.error('Mermaid render error:', err);
        targetEl.innerHTML = `<div class="p-4 text-xs font-mono text-amber-400 bg-amber-950/20 rounded border border-amber-900/40">
          <div class="font-bold mb-1">Diagram Render Warning</div>
          <pre class="overflow-x-auto text-[11px] text-slate-300">${code}</pre>
        </div>`;
      }
    });
  }, [renderedHtml, mermaidDiagrams]);

  // Attach interactive click listeners for copy buttons and diagram modals
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

    const handleCopy = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest('.code-copy-btn, .mermaid-copy-btn') as HTMLButtonElement | null;
      if (!target) return;

      const rawCode = target.getAttribute('data-code');
      if (rawCode) {
        const text = decodeURIComponent(rawCode);
        navigator.clipboard.writeText(text);
        const originalText = target.innerHTML;
        target.innerHTML = `<span class="text-emerald-400 font-semibold">Copied!</span>`;
        setTimeout(() => {
          target.innerHTML = originalText;
        }, 2000);
      }
    };

    const handleExpandMermaid = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest('.mermaid-expand-btn') as HTMLButtonElement | null;
      if (!target) return;

      const id = target.getAttribute('data-id');
      if (id && mermaidDiagrams.has(id)) {
        const code = mermaidDiagrams.get(id)!;
        const targetSvg = container.querySelector(`#${id}`)?.innerHTML || '';
        setSelectedMermaid({ id, code, svg: targetSvg });
      }
    };

    container.addEventListener('click', handleCopy);
    container.addEventListener('click', handleExpandMermaid);

    return () => {
      container.removeEventListener('click', handleCopy);
      container.removeEventListener('click', handleExpandMermaid);
    };
  }, [renderedHtml, mermaidDiagrams]);

  return (
    <div className={`markdown-content prose prose-invert max-w-none ${className}`}>
      <div ref={containerRef} dangerouslySetInnerHTML={{ __html: renderedHtml }} />

      {/* Mermaid Fullscreen Modal */}
      {selectedMermaid && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-6xl max-h-[90vh] bg-[#0c1017] border border-slate-800 rounded-xl flex flex-col shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0f141f]">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#c96a12]"></span>
                <span className="font-mono text-sm uppercase tracking-wider text-slate-200 font-semibold">Diagram Modal Viewer</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(selectedMermaid.code);
                    alert('Mermaid syntax copied to clipboard!');
                  }}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition"
                >
                  Copy Syntax
                </button>
                <button
                  onClick={() => setSelectedMermaid(null)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-rose-900/60 text-slate-300 hover:text-rose-200 text-xs font-mono transition"
                >
                  Close [Esc]
                </button>
              </div>
            </div>
            <div
              className="p-8 overflow-auto flex-1 flex justify-center items-center bg-[#070b12]"
              dangerouslySetInnerHTML={{ __html: selectedMermaid.svg }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
