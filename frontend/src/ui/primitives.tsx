import React from 'react';
import { AlertTriangle, FileText, Loader2 } from 'lucide-react';
import { hazardOf, sevOf, docLabel } from '../lib/format';
import { useNwis } from '../state/nwis';

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ');

export const Panel: React.FC<{ className?: string; children: React.ReactNode; as?: 'section' | 'div' }> = ({ className, children, as = 'section' }) =>
  React.createElement(as, { className: cx('bg-surface border border-line rounded-xl shadow-card', className) }, children);

export const PanelHead: React.FC<{ title: React.ReactNode; hint?: React.ReactNode; right?: React.ReactNode; className?: string }> = ({ title, hint, right, className }) => (
  <header className={cx('flex items-start justify-between gap-4 px-4 pt-3.5 pb-3 border-b border-line', className)}>
    <div className="min-w-0">
      <h2 className="text-[13px] font-semibold tracking-[-0.005em] text-ink">{title}</h2>
      {hint && <p className="text-xs text-ink-3 mt-0.5 leading-snug">{hint}</p>}
    </div>
    {right && <div className="shrink-0 flex items-center gap-2">{right}</div>}
  </header>
);

export const PageHeader: React.FC<{ eyebrow?: string; title: string; lead?: React.ReactNode; right?: React.ReactNode }> = ({ eyebrow, title, lead, right }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
    <div className="max-w-3xl">
      {eyebrow && <div className="text-2xs font-medium uppercase tracking-[0.12em] text-accent mb-1.5">{eyebrow}</div>}
      <h1 className="text-[22px] leading-7 font-semibold tracking-[-0.015em] text-ink">{title}</h1>
      {lead && <p className="text-[13.5px] text-ink-2 mt-1.5 leading-relaxed">{lead}</p>}
    </div>
    {right && <div className="flex items-center gap-2">{right}</div>}
  </div>
);

export const Stat: React.FC<{ label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: string; className?: string }> = ({ label, value, sub, tone, className }) => (
  <div className={cx('min-w-0', className)}>
    <div className="text-2xs uppercase tracking-[0.08em] text-ink-3">{label}</div>
    <div className="num text-[20px] leading-7 font-medium text-ink truncate" style={tone ? { color: tone } : undefined}>{value}</div>
    {sub && <div className="text-xs text-ink-3 truncate">{sub}</div>}
  </div>
);

export const HazardChip: React.FC<{ hazard: string; size?: 'sm' | 'md'; className?: string }> = ({ hazard, size = 'sm', className }) => {
  const h = hazardOf(hazard);
  return (
    <span
      className={cx('inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap', size === 'sm' ? 'text-[11px] px-2 py-0.5' : 'text-xs px-2.5 py-1', className)}
      style={{ background: h.soft, color: h.color }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: h.color }} />
      {h.label}
    </span>
  );
};

export const SeverityTag: React.FC<{ severity?: string | null; className?: string }> = ({ severity, className }) => {
  const s = sevOf(severity);
  return (
    <span className={cx('inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.06em]', className)} style={{ color: s.color }}>
      <span className="inline-block w-2 h-2 rotate-45" style={{ background: s.color }} />
      {s.label}
    </span>
  );
};

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: 'sm' | 'md'; icon?: React.ReactNode };
export const Button: React.FC<BtnProps> = ({ variant = 'secondary', size = 'md', icon, className, children, ...rest }) => (
  <button
    {...rest}
    className={cx(
      'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed select-none',
      size === 'sm' ? 'text-xs h-7 px-2.5' : 'text-[13px] h-9 px-3.5',
      variant === 'primary' && 'bg-accent text-white hover:bg-accent-ink',
      variant === 'secondary' && 'bg-surface border border-line-strong text-ink hover:bg-sunken',
      variant === 'ghost' && 'text-ink-2 hover:bg-sunken hover:text-ink',
      variant === 'danger' && 'bg-sev-critical text-white hover:opacity-90',
      className,
    )}
  >
    {icon}
    {children}
  </button>
);

export const Segmented = <T extends string>({ value, options, onChange, className }: { value: T; options: { value: T; label: React.ReactNode }[]; onChange: (v: T) => void; className?: string }) => (
  <div className={cx('inline-flex p-0.5 rounded-lg bg-sunken border border-line', className)} role="tablist">
    {options.map((o) => (
      <button
        key={o.value}
        role="tab"
        aria-selected={value === o.value}
        onClick={() => onChange(o.value)}
        className={cx('px-2.5 h-7 text-xs font-medium rounded-md transition-colors', value === o.value ? 'bg-surface text-ink shadow-card' : 'text-ink-3 hover:text-ink')}
      >
        {o.label}
      </button>
    ))}
  </div>
);

export const Loading: React.FC<{ label?: string; className?: string }> = ({ label = 'Loading', className }) => (
  <div className={cx('flex items-center gap-2 text-ink-3 text-[13px] p-6', className)}>
    <Loader2 className="w-4 h-4 animate-spin" /> {label}…
  </div>
);

export const Skeleton: React.FC<{ className?: string }> = ({ className }) => <div className={cx('rounded-md bg-sunken animate-pulse', className)} />;

export const ErrorNote: React.FC<{ message: string; onRetry?: () => void; className?: string }> = ({ message, onRetry, className }) => (
  <div className={cx('flex items-start gap-3 m-4 p-3 rounded-lg border text-[13px]', className)} style={{ borderColor: '#f0c8c2', background: '#fdf3f1', color: 'var(--sev-critical)' }}>
    <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
    <div className="flex-1">{message}</div>
    {onRetry && <button className="underline underline-offset-2 font-medium" onClick={onRetry}>Retry</button>}
  </div>
);

export const Empty: React.FC<{ title: string; body?: React.ReactNode; action?: React.ReactNode; className?: string }> = ({ title, body, action, className }) => (
  <div className={cx('text-center px-6 py-10', className)}>
    <div className="text-[13.5px] font-medium text-ink">{title}</div>
    {body && <div className="text-[13px] text-ink-3 mt-1 max-w-sm mx-auto leading-relaxed">{body}</div>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);

/** A clickable citation that opens the source PDF at the cited page. */
export const SourceLink: React.FC<{ doc?: string | null; page?: number | null; title?: string; compact?: boolean; className?: string }> = ({ doc, page, title, compact, className }) => {
  const { openEvidence } = useNwis();
  if (!doc) return <span className="text-xs text-ink-3">No source on record</span>;
  return (
    <button
      onClick={(e) => { e.stopPropagation(); openEvidence({ doc, page, title: title || docLabel(doc) }); }}
      className={cx('inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent-ink hover:underline underline-offset-2 text-left', className)}
      title="Open the source document at this page"
    >
      <FileText className="w-3.5 h-3.5 shrink-0" />
      <span className="truncate">{compact ? `p.${page ?? 1}` : `${docLabel(doc)}${page ? ` · p.${page}` : ''}`}</span>
    </button>
  );
};

export const Kbd: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <kbd className="num text-[10px] px-1.5 py-0.5 rounded border border-line bg-sunken text-ink-3">{children}</kbd>
);
