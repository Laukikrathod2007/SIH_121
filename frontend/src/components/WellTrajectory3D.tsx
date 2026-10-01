import React, { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import * as THREE from 'three';
import { SurveyStation, WellTrajectory, FormationTop, DrillingEvent } from '../types';
import { stationToVec3, positionAtMD, TRAJECTORY_SCALE as SCALE } from '../lib/trajectoryGeometry';

const FORMATION_PALETTE = [
  '#b45309', '#a16207', '#64748b', '#7c2d12', '#78350f', '#57534e', '#065f46', '#374151',
];

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  MEDIUM: '#f59e0b',
  LOW: '#eab308',
};

function WellboreTube({ stations, color, radius }: { stations: SurveyStation[]; color: string; radius: number }) {
  const geometry = useMemo(() => {
    if (stations.length < 2) return null;
    const points = stations.map(stationToVec3);
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, Math.max(32, stations.length * 2), radius, 8, false);
  }, [stations, radius]);

  if (!geometry) return null;
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={color} metalness={0.6} roughness={0.35} />
    </mesh>
  );
}

function FormationBands({ formations, extent }: { formations: FormationTop[]; extent: number }) {
  return (
    <>
      {formations.map((f, idx) => {
        const yTop = -f.top_tvd_m * SCALE;
        const thickness = Math.max(f.thickness_m * SCALE, 0.05);
        const color = FORMATION_PALETTE[idx % FORMATION_PALETTE.length];
        return (
          <mesh key={f.formation_name + idx} position={[0, yTop - thickness / 2, 0]}>
            <boxGeometry args={[extent, thickness, extent]} />
            <meshStandardMaterial color={color} transparent opacity={0.18} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
}

function EventMarkers({
  events,
  stations,
  onHover,
}: {
  events: DrillingEvent[];
  stations: SurveyStation[];
  onHover: (e: DrillingEvent | null) => void;
}) {
  return (
    <>
      {events.map((evt) => {
        const pos = positionAtMD(stations, evt.depth_start_md_m);
        if (!pos) return null;
        const color = SEVERITY_COLOR[evt.severity] || '#94a3b8';
        return (
          <mesh
            key={evt.event_id}
            position={pos}
            onPointerOver={(e) => {
              e.stopPropagation();
              onHover(evt);
            }}
            onPointerOut={() => onHover(null)}
          >
            <sphereGeometry args={[0.12, 16, 16]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
          </mesh>
        );
      })}
    </>
  );
}

interface WellTrajectory3DProps {
  activeTrajectory: WellTrajectory;
  offsetTrajectory?: WellTrajectory | null;
  formations: FormationTop[];
  events: DrillingEvent[];
}

export const WellTrajectory3D: React.FC<WellTrajectory3DProps> = ({
  activeTrajectory,
  offsetTrajectory,
  formations,
  events,
}) => {
  const [hovered, setHovered] = React.useState<DrillingEvent | null>(null);

  const maxTvd = Math.max(...activeTrajectory.stations.map((s) => s.tvd_m), 1);
  const extent = Math.max(maxTvd * SCALE * 0.9, 4);

  return (
    <div className="relative w-full h-full">
      <Canvas camera={{ position: [extent * 1.4, extent * 0.8, extent * 1.4], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 20, 10]} intensity={1.1} />
        <FormationBands formations={formations} extent={extent} />
        <WellboreTube stations={activeTrajectory.stations} color="#06b6d4" radius={0.05} />
        {offsetTrajectory && (
          <WellboreTube stations={offsetTrajectory.stations} color="#f59e0b" radius={0.04} />
        )}
        <EventMarkers events={events} stations={activeTrajectory.stations} onHover={setHovered} />
        <axesHelper args={[extent * 0.3]} />
        <OrbitControls enableDamping dampingFactor={0.08} />
      </Canvas>

      {hovered && (
        <div className="absolute bottom-3 left-3 bg-slate-950/95 border border-rose-500/40 rounded p-2.5 text-xs font-mono max-w-xs pointer-events-none">
          <div className="text-rose-400 font-bold">{hovered.event_type} · {hovered.severity}</div>
          <div className="text-slate-300 mt-1">{hovered.depth_start_md_m.toFixed(0)}m MD · {hovered.formation ?? 'n/a'}</div>
          <div className="text-slate-400 mt-1 leading-snug">{hovered.raw_narrative || hovered.outcome || 'No narrative recorded'}</div>
        </div>
      )}

      <div className="absolute top-3 right-3 bg-slate-950/90 border border-slate-800 rounded p-2 text-[10px] font-mono space-y-1">
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-500" /> Active well</div>
        {offsetTrajectory && <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Top offset well</div>}
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Hazard event</div>
      </div>
    </div>
  );
};
