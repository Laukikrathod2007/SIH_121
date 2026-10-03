import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { NearbyWellsMap, type WellPoint } from '../components/nwis-map/NearbyWellsMap';
import { WellDetailPanel } from '../components/nwis-map/WellDetailPanel';
import { EvidenceViewer, type Evidence } from '../components/nwis-map/EvidenceViewer';
import { useNwisMapData } from '../components/nwis-map/useNwisMapData';

// Wires the imported nwis-map-package (NearbyWellsMap / WellDetailPanel /
// EvidenceViewer, all copied in unchanged -- see their own file headers)
// to real backend data via useNwisMapData, following the same wiring
// pattern as the package's own App.tsx demo. Real wells only, all 14
// currently in the live store (12 synthetic + the 2 real Volve wells),
// not a fabricated subset. Evidence citations open real PDFs -- 39
// bundled synthetic DDRs plus 3 real Volve documents (F-12's COMPLETION
// report, F-1's MUD_LOG/MUD_LOG_COMBINED) -- via evidence-server/
// (also copied in unchanged from the package's server/), not the
// module 01 file endpoint, which needs an API-key header a plain iframe
// can't set.
const EVIDENCE_SERVER = (import.meta.env.VITE_EVIDENCE_SERVER as string | undefined) || 'http://localhost:4100/evidence';

// Some events' real `source_document` values (real_data/real_events_depth_tagged_fresh.json,
// generated on a Windows machine) carry a Windows-style relative path prefix,
// e.g. "volve\WELL-15_9-F-1_MUD_LOG.pdf", rather than a bare filename. The
// vendored EvidenceViewer/WellDetailPanel (nwis-map-package, copied in
// unchanged) pass this straight through as the `name` query param, and
// evidence-server's own path-traversal guard rejects any `/`/`\` in it --
// so the raw value always 400s there. Strip any directory prefix (forward
// or back slash) here, at the real-data boundary, rather than editing the
// vendored component or the committed source JSON.
function basenameOf(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export const NwisMapPage: React.FC = () => {
  const { activeWellId, setActiveWellId } = useApp();
  const { wells, eventsByWell, loading } = useNwisMapData();
  const [selected, setSelected] = useState<WellPoint | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);

  if (loading) {
    return (
      <div className="p-4 h-full flex items-center justify-center text-slate-500 font-mono text-xs">
        Loading real well data...
      </div>
    );
  }

  return (
    <div className="h-full flex">
      <div className="flex-1 relative">
        <NearbyWellsMap
          wells={wells}
          activeWellId={activeWellId}
          onSelectWell={(w) => setSelected(w)}
          height="100%"
        />
      </div>

      {selected && (
        <WellDetailPanel
          well={selected}
          events={eventsByWell[selected.well_id] ?? []}
          onBack={() => setSelected(null)}
          onOpenEvidence={(doc, page, title) => setEvidence({ doc: basenameOf(doc), page, title })}
          onSetActive={() => setActiveWellId(selected.well_id)}
        />
      )}

      <EvidenceViewer evidence={evidence} onClose={() => setEvidence(null)} apiBase={EVIDENCE_SERVER} />
    </div>
  );
};
