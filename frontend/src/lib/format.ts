import type { Hazard, Severity } from './api';

/** One vocabulary for hazards across every screen: label, short code, colour. */
export const HAZARDS: Record<Hazard, { label: string; short: string; color: string; soft: string }> = {
  MUD_LOSS: { label: 'Mud loss', short: 'ML', color: '#2c64c9', soft: '#e6edf9' },
  STUCK_PIPE: { label: 'Stuck pipe', short: 'SP', color: '#6f47c2', soft: '#eee9f8' },
  KICK: { label: 'Kick / overpressure', short: 'KK', color: '#b62f5e', soft: '#f7e6ec' },
  WELLBORE_INSTABILITY: { label: 'Wellbore instability', short: 'WI', color: '#a8740a', soft: '#f6eedb' },
  TORQUE_SPIKE: { label: 'Torque spike', short: 'TQ', color: '#1c7f75', soft: '#e1f0ee' },
  CEMENTING_FAILURE: { label: 'Cementing issue', short: 'CM', color: '#5b6471', soft: '#eceef1' },
};

export const hazardOf = (h: string) =>
  HAZARDS[h as Hazard] ?? { label: h.replace(/_/g, ' ').toLowerCase(), short: h.slice(0, 2), color: '#5b6471', soft: '#eceef1' };

export const SEVERITY: Record<string, { label: string; color: string; rank: number }> = {
  CRITICAL: { label: 'Critical', color: 'var(--sev-critical)', rank: 3 },
  HIGH: { label: 'High', color: 'var(--sev-high)', rank: 2 },
  MODERATE: { label: 'Moderate', color: 'var(--sev-medium)', rank: 1 },
  MEDIUM: { label: 'Medium', color: 'var(--sev-medium)', rank: 1 },
  LOW: { label: 'Low', color: 'var(--sev-low)', rank: 0 },
};
export const sevOf = (s?: string | null) => SEVERITY[(s || 'LOW').toUpperCase()] ?? SEVERITY.LOW;

export const m = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : `${v.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: digits })} m`;

export const n = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString('en-IN', { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const km = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${v < 10 ? v.toFixed(1) : v.toFixed(0)} km`);

export const ago = (iso?: string | null) => {
  if (!iso) return '—';
  const t = Date.parse(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(t).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
};

export const shortWell = (id: string) => id.replace(/^WELL-/, '');

export const docLabel = (name?: string | null) => {
  if (!name) return 'No source';
  const m2 = name.match(/^(DDR|WCR)_WELL-([A-Z]+-\d+)(?:_(\d+)m)?\.pdf$/);
  if (m2) return `${m2[1] === 'DDR' ? 'Daily drilling report' : 'Well completion report'} · ${m2[2]}${m2[3] ? ` · ${m2[3]} m` : ''}`;
  return name.replace(/\s*\[DOC-[A-Z0-9]+\]$/, '').replace(/^JOB-[0-9A-F]+_/i, '');
};
