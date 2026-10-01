/**
 * Demo app — shows NearbyWellsMap + WellDetailPanel + EvidenceViewer wired
 * together exactly like the /map screen in the source project. This is the
 * file to copy patterns from if you're integrating into your own app;
 * everything else in src/ is a self-contained, reusable component.
 */
import React, { useState } from 'react';
import { NearbyWellsMap, type WellPoint } from './NearbyWellsMap';
import { WellDetailPanel } from './WellDetailPanel';
import { EvidenceViewer, type Evidence } from './EvidenceViewer';
import wellsData from './wells-data.json';
import eventsData from './events-data.json';

const ACTIVE_WELL_ID = 'WELL-HGJ-012';
const EVIDENCE_SERVER = 'http://localhost:4000/evidence';

export default function App() {
  const [selected, setSelected] = useState<WellPoint | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', background: '#f4f3ef' }}>
      <div style={{ flex: 1, position: 'relative' }}>
        <NearbyWellsMap
          wells={wellsData as WellPoint[]}
          activeWellId={ACTIVE_WELL_ID}
          onSelectWell={(w) => setSelected(w)}
        />
      </div>

      {selected && (
        <WellDetailPanel
          well={selected}
          events={(eventsData as Record<string, any[]>)[selected.well_id] ?? []}
          onBack={() => setSelected(null)}
          onOpenEvidence={(doc, page, title) => setEvidence({ doc, page, title })}
          onOpenWellFile={() => alert(`Would navigate to well file for ${selected.well_name}`)}
          onSetActive={() => alert(`Would set ${selected.well_name} as the active well`)}
        />
      )}

      <EvidenceViewer evidence={evidence} onClose={() => setEvidence(null)} apiBase={EVIDENCE_SERVER} />
    </div>
  );
}
