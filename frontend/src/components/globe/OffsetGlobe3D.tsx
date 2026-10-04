import React, { Suspense, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import * as THREE from 'three';
import { MapWell } from '../../types';
import { EarthGlobe } from './EarthGlobe';
import { WellMarkers } from './WellMarkers';
import { GLOBE_RADIUS } from '../../lib/globeGeometry';

// The real interactive 3D offset-well globe. Consumes the SAME
// GET /api/v2/map/wells data as the 2D Offset Map / Nearby Wells pages
// (fetched once by the parent, GlobeMapPage, via useApp()'s existing
// wells + a direct api.getMapWells() call for lat/lon+event-count fields
// the Well type alone doesn't carry) -- this is a second VIEW of the same
// authoritative application data, not a second well dataset. Active-well
// selection and radius here are the same state shape NearbyWellsPage
// already uses (activeWellId from useApp(), a local radiusKm slider),
// so switching between the 2D map and this view shows the same "nearby"
// set for the same well.
interface OffsetGlobe3DProps {
  wells: MapWell[];
  activeWellId: string;
  radiusKm: number;
  onSelectWell: (wellId: string) => void;
}

// Rotates its children together, at the same rate -- the Earth sphere's
// texture AND the well markers must share one rotation, otherwise the
// texture spins under the (differently-parented) markers and every real
// well's apparent position on the visible continents drifts further wrong
// the longer the page has been open. Found exactly this way during the
// end-to-end verification pass: a real well's marker was screenshotted in
// two different wrong locations a few seconds apart, which traced back to
// EarthGlobe owning its own independent rotating <group> that WellMarkers
// (a Canvas-level sibling, not a child of that group) never shared.
function RotatingGroup({ paused, children }: { paused?: boolean; children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (paused || !ref.current) return;
    ref.current.rotation.y += delta * 0.03;
  });
  return <group ref={ref}>{children}</group>;
}

export const OffsetGlobe3D: React.FC<OffsetGlobe3DProps> = ({
  wells,
  activeWellId,
  radiusKm,
  onSelectWell,
}) => {
  const [hoveredWellId, setHoveredWellId] = useState<string | null>(null);
  const activeWell = wells.find((w) => w.well_id === activeWellId);

  return (
    <div className="relative w-full h-full bg-slate-950">
      <Canvas camera={{ position: [0, 0, GLOBE_RADIUS * 2.6], fov: 45 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 3, 5]} intensity={1.2} />
        {/* Real starfield via drei's built-in Stars -- not a fabricated
            data element, purely an environment backdrop, same category as
            the dark page background every other scene in this app uses. */}
        <Stars radius={50} depth={30} count={2500} factor={2} fade speed={0.5} />
        <RotatingGroup>
          <Suspense fallback={null}>
            <EarthGlobe />
          </Suspense>
          <WellMarkers
            wells={wells}
            activeWellId={activeWellId}
            radiusKm={radiusKm}
            hoveredWellId={hoveredWellId}
            onHoverWell={setHoveredWellId}
            onSelectWell={onSelectWell}
          />
        </RotatingGroup>
        <OrbitControls
          enableDamping
          dampingFactor={0.08}
          minDistance={GLOBE_RADIUS * 1.3}
          maxDistance={GLOBE_RADIUS * 6}
          rotateSpeed={0.5}
        />
      </Canvas>

      <div className="absolute top-3 left-3 bg-slate-950/90 border border-slate-800 rounded p-2 text-[10px] font-mono space-y-1 pointer-events-none">
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-400" /> Active well{activeWell ? ` — ${activeWell.well_name}` : ''}</div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> Offset well (within {radiusKm} km)</div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> Catalog well</div>
      </div>

      <div className="absolute bottom-3 right-3 bg-slate-950/80 border border-slate-800 rounded px-2 py-1 text-[9px] font-mono text-slate-500 pointer-events-none">
        Drag to rotate &middot; scroll to zoom &middot; click a marker to select
      </div>
    </div>
  );
};
