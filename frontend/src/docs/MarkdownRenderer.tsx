import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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

// Initialize mermaid once.
// The diagram renders inside a light card (bg-white / bg-[#fafaf9], see
// .mermaid-target / .mermaid-render-area below), so it must use a LIGHT
// mermaid theme. The previous config used theme: 'dark' with a near-black
// `background` themeVariable -- but mermaid only paints that color inside
// node fills it derives from it, not the light container the SVG actually
// sits in, so diagrams came out as dark-on-dark (illegible) boxes floating
// on a light background. 'base' + explicit light themeVariables keeps node
// fills, borders and text all consistent with the card chrome around them.
mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    darkMode: false,
    background: '#fafaf9',
    primaryColor: '#fdf1e6',
    primaryTextColor: '#1c1917',
    primaryBorderColor: '#c96a12',
    lineColor: '#78716c',
    secondaryColor: '#f5f5f4',
    secondaryTextColor: '#1c1917',
    secondaryBorderColor: '#a8a29e',
    tertiaryColor: '#ffffff',
    tertiaryTextColor: '#1c1917',
    tertiaryBorderColor: '#d6d3d1',
    textColor: '#1c1917',
    nodeTextColor: '#1c1917',
    mainBkg: '#fdf1e6',
    nodeBorder: '#c96a12',
    clusterBkg: '#f5f5f4',
    clusterBorder: '#a8a29e',
    edgeLabelBackground: '#fafaf9',
    fontFamily: 'ui-sans-serif, system-ui, sans-serif',
  },
  securityLevel: 'loose',
});

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  const navigate = useNavigate();
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
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-stone-200 text-[13px] font-mono text-stone-500 uppercase tracking-wider">
          <span class="inline-flex items-center gap-1.5 font-bold"><span class="w-2 h-2 rounded-full bg-stone-900"></span>Architecture Diagram</span>
          <div class="flex items-center gap-1.5">
            <button class="mermaid-expand-btn px-2 py-0.5 rounded border border-stone-300 bg-white hover:bg-stone-50 text-stone-700 text-[13px] font-mono transition" data-id="${id}">Full View</button>
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
        1: 'text-2xl md:text-3xl font-sans font-semibold text-stone-900 tracking-tight mt-8 mb-4 pb-2 border-b border-stone-200 flex items-center group',
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

    // Custom Links: content source files write cross-doc links as
    // file:///docs/<category>/<slug>.md (readable in a plain-markdown
    // viewer/editor), but served over https:// the browser can't navigate
    // to a file:// URL -- it just renders as dead, broken-looking text.
    // Rewrite any such link (or a bare /docs/.../<slug>.md path) to the
    // real in-app route /docs/<slug>; the click handler below then
    // intercepts these for client-side navigation instead of a full
    // page load.
    renderer.link = function ({ href, title, tokens }) {
      const text = this.parser.parseInline(tokens);
      const docMatch = href.match(/^(?:file:\/\/\/)?\/?docs\/(?:[\w-]+\/)*([\w-]+)\.md$/i);
      const resolvedHref = docMatch ? `/docs/${docMatch[1]}` : href;
      const isInternalDoc = resolvedHref.startsWith('/docs/');
      const titleAttr = title ? ` title="${title}"` : '';
      const extraAttrs = isInternalDoc
        ? ' data-doc-link="true"'
        : ' target="_blank" rel="noopener noreferrer"';
      return `<a href="${resolvedHref}"${titleAttr}${extraAttrs} class="text-[#c96a12] hover:text-[#a75208] underline decoration-[#c96a12]/30 hover:decoration-[#a75208] underline-offset-2 transition">${text}</a>`;
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
        <div class="px-4 py-2 bg-slate-900 border-b border-slate-800 text-xs text-slate-400">
          <span class="uppercase tracking-wider font-semibold text-[13px]">${language}</span>
        </div>
        <pre class="p-4 overflow-x-auto text-[13px] leading-relaxed text-slate-200"><code>${highlighted}</code></pre>
      </div>`;
    };

    // Custom Tables with SCADA Styling.
    // marked's default tablecell/tablerow emit bare <th>/<td> with no
    // padding or line-height of their own, and Tailwind's base reset
    // (@tailwind base) strips the browser's default table/cell padding
    // too -- so with nothing filling that gap, cells packed text edge to
    // edge against each other, which is what made dense tables (the
    // SIH26121 requirements matrix, etc.) read as cramped. Cells here get
    // real padding, top alignment (so short cells don't center-stretch
    // next to tall ones), and relaxed wrapping instead of the browser's
    // default break-anywhere behavior on narrow columns.
    renderer.tablecell = function (token: any) {
      const content = this.parser.parseInline(token.tokens);
      const tag = token.header ? 'th' : 'td';
      const alignClass = token.align ? ` text-${token.align}` : '';
      const cellClass = token.header
        ? `px-4 py-3 align-bottom font-semibold whitespace-normal${alignClass}`
        : `px-4 py-3 align-top whitespace-normal${alignClass}`;
      return `<${tag} class="${cellClass}">${content}</${tag}>`;
    };

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
        <table class="w-full text-left text-sm border-collapse leading-relaxed">
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
          <pre class="overflow-x-auto text-[13px] text-slate-300">${code}</pre>
        </div>`;
      }
    });
  }, [renderedHtml, mermaidDiagrams]);

  // Attach interactive click listeners for diagram modals and in-doc links
  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;

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

    // In-doc cross-links (rewritten to /docs/<slug> by renderer.link above)
    // carry data-doc-link so they navigate via React Router instead of a
    // full page reload, which would otherwise re-fetch and remount the
    // whole SPA shell for what is just a content swap.
    const handleDocLink = (e: MouseEvent) => {
      const target = (e.target as HTMLElement).closest('a[data-doc-link]') as HTMLAnchorElement | null;
      if (!target) return;
      const href = target.getAttribute('href');
      if (!href) return;
      e.preventDefault();
      navigate(href);
    };

    container.addEventListener('click', handleExpandMermaid);
    container.addEventListener('click', handleDocLink);

    return () => {
      container.removeEventListener('click', handleExpandMermaid);
      container.removeEventListener('click', handleDocLink);
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
                  onClick={() => setSelectedMermaid(null)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-rose-900/60 text-slate-300 hover:text-rose-200 text-xs font-mono transition"
                >
                  Close [Esc]
                </button>
              </div>
            </div>
            {/* Light background: the injected SVG uses the light mermaid
                theme (see mermaid.initialize above), so its node fills and
                text are tuned for a light pane, not the previous near-black
                one. */}
            <div
              className="p-8 overflow-auto flex-1 flex justify-center items-center bg-[#fafaf9]"
              dangerouslySetInnerHTML={{ __html: selectedMermaid.svg }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
