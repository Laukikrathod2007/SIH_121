/**
 * WellDetailPanel — side panel for a selected offset well: stats, and an
 * incident timeline by depth with "what they did" and a source-document
 * citation that opens the EvidenceViewer.
 *
 * Pairs with NearbyWellsMap (pass the selected WellPoint in) and
 * EvidenceViewer (render once at the app root, control via useState).
 *
 * Requires: react, lucide-react. Needs a `getEvents(wellId)` function you
 * supply (see events-data.json + the demo app for the simplest version —
 * just `(id) => eventsData[id] ?? []`).
 */

import React from 'react';
import { ArrowUpRight, FileText } from 'lucide-react';
import type { WellPoint } from './NearbyWellsMap';

export interface WellEvent {
  event_id: string;
  event_type: string;
  severity: string;
  depth_start_md_m: number | null;
  formation: string | null;
  raw_narrative: string;
  npt_hours: number;
  mitigation_description: string | null;
  outcome: string | null;
  source_document: string | null;
  source_page: number | null;
}

const HAZARD_COLORS: Record<string, { color: string; soft: string; label: string }> = {
  MUD_LOSS: { color: '#2c64c9', soft: '#e6edf9', label: 'Mud loss' },
  STUCK_PIPE: { color: '#6f47c2', soft: '#eee9f8', label: 'Stuck pipe' },
  KICK: { color: '#b62f5e', soft: '#f7e6ec', label: 'Kick / overpressure' },
  WELLBORE_INSTABILITY: { color: '#a8740a', soft: '#f6eedb', label: 'Wellbore instability' },
  TORQUE_SPIKE: { color: '#1c7f75', soft: '#e1f0ee', label: 'Torque spike' },
  CEMENTING_FAILURE: { color: '#5b6471', soft: '#eceef1', label: 'Cementing issue' },
};
const hazardOf = (h: string) => HAZARD_COLORS[h] ?? { color: '#5b6471', soft: '#eceef1', label: h.replace(/_/g, ' ').toLowerCase() };

const SEVERITY: Record<string, string> = { CRITICAL: '#b42318', HIGH: '#c4560f', MEDIUM: '#a87a05', MODERATE: '#a87a05', LOW: '#3d7a4c' };
const sevColor = (s: string) => SEVERITY[(s || 'LOW').toUpperCase()] ?? SEVERITY.LOW;

export interface WellDetailPanelProps {
  well: WellPoint;
  events: WellEvent[];
  onBack: () => void;
  onOpenEvidence: (doc: string, page: number | null | undefined, title?: string) => void;
  onOpenWellFile?: () => void;
  onSetActive?: () => void;
  width?: number;
}

export const WellDetailPanel: React.FC<WellDetailPanelProps> = ({
  well, events, onBack, onOpenEvidence, onOpenWellFile, onSetActive, width = 380,
}) => {
  const sorted = [...events].sort((a, b) => (a.depth_start_md_m ?? 0) - (b.depth_start_md_m ?? 0));

  return (
    <div style={{ width, display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'system-ui, sans-serif', fontSize: 14, color: '#17191d', background: '#f4f3ef', borderLeft: '1px solid #e3e0d8' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #e3e0d8' }}>
        <button onClick={onBack} style={{ fontSize: 12, color: '#868a91', background: 'none', border: 'none', cursor: 'pointer', padding: 0, marginBottom: 8 }}>
          ← All offset wells
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <h2 style={{ fontSize: 20, fontWeight: 500, margin: 0, fontFamily: 'ui-monospace, monospace' }}>{well.well_name}</h2>
        </div>
        <div style={{ fontSize: 12, color: '#868a91', marginTop: 2 }}>{well.field} field · {well.well_type} · {well.status.toLowerCase()}</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginTop: 12 }}>
          <MiniStat label="Total depth" value={`${Math.round(well.total_depth_md_m)} m`} />
          <MiniStat label="Incidents" value={String(well.total_events)} />
          <MiniStat label="Lost time" value={`${well.npt_hours} h`} />
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          {onOpenWellFile && (
            <button onClick={onOpenWellFile} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, height: 32, padding: '0 12px', borderRadius: 8, border: 'none', background: '#0e5a69', color: '#fff', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
              <ArrowUpRight size={14} /> Open well file
            </button>
          )}
          {onSetActive && (
            <button onClick={onSetActive} style={{ height: 32, padding: '0 12px', borderRadius: 8, border: '1px solid #cfcbc0', background: '#fff', color: '#17191d', fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
              Set as active well
            </button>
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto' }}>
        <div style={{ padding: '10px 16px 4px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#868a91' }}>
          What happened in this well, by depth
        </div>
        {sorted.length === 0 && <div style={{ padding: '10px 16px', fontSize: 13, color: '#868a91' }}>No incidents on record.</div>}
        <ol style={{ padding: '0 16px 16px', margin: 0, listStyle: 'none' }}>
          {sorted.map((e) => {
            const hz = hazardOf(e.event_type);
            return (
              <li key={e.event_id} style={{ position: 'relative', paddingLeft: 20, paddingTop: 10, paddingBottom: 10, borderLeft: '1px solid #e3e0d8', marginLeft: 6 }}>
                <span style={{ position: 'absolute', left: -5, top: 16, width: 10, height: 10, borderRadius: '50%', background: hz.color, boxShadow: '0 0 0 2px #f4f3ef' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 500, fontFamily: 'ui-monospace, monospace' }}>{e.depth_start_md_m !== null ? `${Math.round(e.depth_start_md_m)} m` : '—'}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: sevColor(e.severity) }}>{e.severity}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11, fontWeight: 500, padding: '2px 8px', borderRadius: 999, background: hz.soft, color: hz.color }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: hz.color }} />{hz.label}
                  </span>
                  {e.formation && <span style={{ fontSize: 11, color: '#868a91' }}>{e.formation}</span>}
                </div>
                <p style={{ fontSize: 12, color: '#4a4e56', marginTop: 6, lineHeight: 1.5 }}>{e.raw_narrative}</p>
                {e.mitigation_description && (
                  <p style={{ fontSize: 12, marginTop: 6, lineHeight: 1.5 }}>
                    <span style={{ fontWeight: 500, color: '#17191d' }}>What they did: </span>
                    <span style={{ color: '#4a4e56' }}>{e.mitigation_description}</span>
                  </p>
                )}
                {e.source_document && (
                  <button
                    onClick={() => onOpenEvidence(e.source_document!, e.source_page, `${e.source_document} · p.${e.source_page}`)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 6, fontSize: 12, color: '#0e5a69', background: 'none', border: 'none', cursor: 'pointer', padding: 0, textAlign: 'left' }}
                  >
                    <FileText size={13} />
                    Daily drilling report · {well.well_name} · {e.source_document && e.depth_start_md_m ? `${Math.round(e.depth_start_md_m)} m` : ''} · p.{e.source_page ?? 1}
                  </button>
                )}
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
};

const MiniStat: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div>
    <div style={{ fontSize: 10.5, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#868a91' }}>{label}</div>
    <div style={{ fontSize: 14, fontWeight: 500, fontFamily: 'ui-monospace, monospace' }}>{value}</div>
  </div>
);

export default WellDetailPanel;
