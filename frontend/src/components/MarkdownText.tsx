import React from 'react';

/**
 * Minimal Markdown renderer for Copilot answers.
 *
 * The agent replies in Markdown (bold well IDs, numbered rankings, nested
 * bullet breakdowns, an italic data-source footer), but CopilotPage used to
 * render `msg.content` as a bare string inside `whitespace-pre-wrap` -- so
 * operators saw literal `**WELL-BGJ-008**` and `- **DORS Score:**` instead
 * of formatted text, which reads as broken output in a demo.
 *
 * This deliberately does NOT pull in react-markdown + rehype-sanitize: the
 * agent's output is model-generated text, and the safe way to show it is to
 * never build HTML from it at all. Everything below returns React elements
 * with the text as children, so a `<script>` or `<img onerror=...>` in a
 * reply is displayed as characters, never parsed as markup -- the same
 * guarantee the previous plain-text rendering had.
 *
 * Supported, because it is what the backend actually emits:
 *   **bold**, *italic*, `code`, "- " / "* " bullets (incl. indented),
 *   "1." ordered items, blank-line paragraph breaks.
 * Anything else falls through as plain text rather than being mangled.
 */

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*)/g;

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split(INLINE).filter(Boolean).map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={key} className="font-semibold text-[var(--text-primary)]">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={key} className="font-mono text-[11px] px-1 py-0.5 rounded bg-slate-500/10">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={key} className="opacity-80">{part.slice(1, -1)}</em>;
    }
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });
}

export const MarkdownText: React.FC<{ text: string; className?: string }> = ({ text, className }) => {
  const lines = text.split('\n');

  return (
    <div className={className ?? 'leading-relaxed font-sans text-xs space-y-1'}>
      {lines.map((raw, i) => {
        const line = raw.trimEnd();
        if (!line.trim()) return <div key={i} className="h-2" />;

        const indent = raw.length - raw.trimStart().length;
        const bullet = line.trimStart().match(/^[-*]\s+(.*)$/);
        if (bullet) {
          return (
            <div key={i} className="flex gap-2" style={{ paddingLeft: indent > 2 ? 16 : 0 }}>
              <span className="text-[var(--text-secondary)] select-none">•</span>
              <span className="flex-1">{renderInline(bullet[1], `b${i}`)}</span>
            </div>
          );
        }

        const ordered = line.trimStart().match(/^(\d+)\.\s+(.*)$/);
        if (ordered) {
          return (
            <div key={i} className="flex gap-2 mt-1.5">
              <span className="font-mono text-[var(--text-secondary)] select-none">{ordered[1]}.</span>
              <span className="flex-1">{renderInline(ordered[2], `o${i}`)}</span>
            </div>
          );
        }

        return <div key={i}>{renderInline(line, `p${i}`)}</div>;
      })}
    </div>
  );
};
