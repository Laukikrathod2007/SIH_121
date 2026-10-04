import React, { useMemo } from 'react';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { MapWell } from '../../types';
import { latLonToVec3, haversineKm, greatCircleArcPoint } from '../../lib/globeGeometry';

// Real well markers on the globe, driven entirely by module 02's real
// GET /api/v2/map/wells data (see OffsetGlobe3D's data fetch) -- no demo
// coordinates, no invented well list. Color/size logic mirrors
// NearbyWellsPage/BasinMap's existing conventions (active = cyan,
// in-radius offset = amber, out-of-radius catalog well = slate) so the
// globe agrees visually with the 2D map rather than inventing its own
// palette.
const ACTIVE_COLOR = '#22d3ee';
const OFFSET_COLOR = '#f59e0b';
const CATALOG_COLOR = '#64748b';

function markerColor(well: MapWell, activeWellId: string, inRadius: boolean): string {
  if (well.well_id === activeWellId) return ACTIVE_COLOR;
  if (inRadius) return OFFSET_COLOR;
  return CATALOG_COLOR;
}

function GreatCircleArc({ from, to, color }: { from: MapWell; to: MapWell; color: string }) {
  const points = useMemo(() => {
    const N = 48;
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= N; i++) {
      pts.push(greatCircleArcPoint(from.lat, from.lon, to.lat, to.lon, i / N));
    }
    return pts;
  }, [from.lat, from.lon, to.lat, to.lon]);

  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points]);

  return (
    <primitive object={new THREE.Line(geometry, new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.55 }))} />
  );
}

interface WellMarkersProps {
  wells: MapWell[];
  activeWellId: string;
  radiusKm: number;
  hoveredWellId: string | null;
  onHoverWell: (wellId: string | null) => void;
  onSelectWell: (wellId: string) => void;
}

export const WellMarkers: React.FC<WellMarkersProps> = ({
  wells,
  activeWellId,
  radiusKm,
  hoveredWellId,
  onHoverWell,
  onSelectWell,
}) => {
  const activeWell = wells.find((w) => w.well_id === activeWellId);

  const withDistance = useMemo(() => {
    if (!activeWell) return wells.map((w) => ({ well: w, distanceKm: Infinity, inRadius: false }));
    return wells.map((w) => {
      const distanceKm = haversineKm(activeWell.lat, activeWell.lon, w.lat, w.lon);
      return { well: w, distanceKm, inRadius: w.well_id !== activeWellId && distanceKm <= radiusKm };
    });
  }, [wells, activeWell, radiusKm]);

  return (
    <group>
      {/* Great-circle connector arcs from the active well to every offset
          well currently inside the selected radius -- real distances, not
          decorative lines; disappears/reappears as the radius slider or
          active well changes, exactly like the 2D map's distance-lines
          toggle already does. */}
      {activeWell &&
        withDistance
          .filter((d) => d.inRadius)
          .map((d) => (
            <GreatCircleArc key={`arc-${d.well.well_id}`} from={activeWell} to={d.well} color={OFFSET_COLOR} />
          ))}

      {withDistance.map(({ well, distanceKm, inRadius }) => {
        const pos = latLonToVec3(well.lat, well.lon);
        const isActive = well.well_id === activeWellId;
        const isHovered = well.well_id === hoveredWellId;
        const color = markerColor(well, activeWellId, inRadius);
        const size = isActive ? 0.045 : inRadius ? 0.035 : 0.022;

        return (
          <group key={well.well_id} position={pos}>
            <mesh
              onPointerOver={(e) => {
                e.stopPropagation();
                onHoverWell(well.well_id);
              }}
              onPointerOut={() => onHoverWell(null)}
              onClick={(e) => {
                e.stopPropagation();
                onSelectWell(well.well_id);
              }}
            >
              <sphereGeometry args={[size, 16, 16]} />
              <meshBasicMaterial color={color} />
            </mesh>
            {/* Subtle glow halo on the active well, cheap additive sprite
                rather than a bloom post-process pass. */}
            {isActive && (
              <mesh>
                <sphereGeometry args={[size * 2.2, 16, 16]} />
                <meshBasicMaterial color={color} transparent opacity={0.25} depthWrite={false} />
              </mesh>
            )}
            {isHovered && (
              <Html distanceFactor={6} style={{ pointerEvents: 'none' }}>
                <div className="bg-slate-950/95 border border-cyan-500/40 rounded px-2 py-1.5 text-[10px] font-mono whitespace-nowrap -translate-x-1/2 -translate-y-full -mt-2">
                  <div className="text-cyan-300 font-bold">{well.well_name}</div>
                  <div className="text-slate-400">{well.field} &middot; {well.total_depth_md_m.toFixed(0)}m MD</div>
                  {!isActive && Number.isFinite(distanceKm) && (
                    <div className="text-slate-400">{distanceKm.toFixed(1)} km from active well</div>
                  )}
                  {well.total_events > 0 && (
                    <div className="text-amber-400">{well.total_events} logged event{well.total_events === 1 ? '' : 's'}</div>
                  )}
                </div>
              </Html>
            )}
          </group>
        );
      })}
    </group>
  );
};
