import React, { useMemo, useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { SurveyStation, WellTrajectory, FormationTop, DrillingEvent, RiskCorridor } from '../../types';
import { stationToVec3, positionAtMD, TRAJECTORY_SCALE as SCALE } from '../../lib/trajectoryGeometry';
import { CameraRig, CameraPreset, CAMERA_PRESET_LIST } from '../three/CameraRig';
import { Compass, Layers, Radio, Map as MapIcon, Eye } from 'lucide-react';

const FORMATION_PALETTE = ['#78350f', '#92400e', '#57534e', '#3f3f46', '#1c1917', '#44403c', '#065f46', '#374151'];
const SEVERITY_COLOR: Record<string, string> = { CRITICAL: '#ef4444', HIGH: '#f97316', MEDIUM: '#f59e0b', LOW: '#eab308' };
const RISK_COLOR: Record<string, string> = { CRITICAL: '#f43f5e', HIGH: '#f97316', MODERATE: '#f59e0b', LOW: '#10b981' };

function WellboreTube({ stations, color, radius, opacity = 1 }: { stations: SurveyStation[]; color: string; radius: number; opacity?: number }) {
  const geometry = useMemo(() => {
    if (stations.length < 2) return null;
    const points = stations.map((s) => stationToVec3(s));
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, Math.max(32, stations.length * 2), radius, 8, false);
  }, [stations, radius]);
  if (!geometry) return null;
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={color} metalness={0.6} roughness={0.35} transparent={opacity < 1} opacity={opacity} />
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
            <meshStandardMaterial color={color} transparent opacity={0.22} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
}

// Hazard corridors as colored bands along the ACTIVE well's own trajectory
// tube, between depth_start_m and depth_end_m -- real data from
// analyzeWell's active_risk_corridors, rendered nowhere in the app before
// this component (found during the visualization audit).
function HazardCorridorBands({ corridors, stations }: { corridors: RiskCorridor[]; stations: SurveyStation[] }) {
  return (
    <>
      {corridors.map((c) => {
        const startPos = positionAtMD(stations, c.depth_start_m);
        const endPos = positionAtMD(stations, c.depth_end_m);
        if (!startPos || !endPos) return null;
        const mid = startPos.clone().lerp(endPos, 0.5);
        const len = startPos.distanceTo(endPos) || 0.1;
        const dir = endPos.clone().sub(startPos).normalize();
        const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
        const color = RISK_COLOR[c.risk_level] || '#94a3b8';
        return (
          <mesh key={c.corridor_id} position={mid} quaternion={quaternion}>
            <cylinderGeometry args={[0.09, 0.09, len, 12, 1, true]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} transparent opacity={0.35} side={THREE.DoubleSide} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
}

function EventMarkers({ events, stations, onHover, onClick }: {
  events: DrillingEvent[]; stations: SurveyStation[];
  onHover: (e: DrillingEvent | null) => void; onClick: (e: DrillingEvent) => void;
}) {
  return (
    <>
      {events.map((evt) => {
        const pos = positionAtMD(stations, evt.depth_start_md_m);
        if (!pos) return null;
        const color = SEVERITY_COLOR[evt.severity] || '#94a3b8';
        return (
          <mesh key={evt.event_id} position={pos}
            onPointerOver={(e) => { e.stopPropagation(); onHover(evt); }}
            onPointerOut={() => onHover(null)}
            onClick={(e) => { e.stopPropagation(); onClick(evt); }}
          >
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} />
          </mesh>
        );
      })}
    </>
  );
}

function Bit({ stations, depth }: { stations: SurveyStation[]; depth: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const targetRef = useRef(new THREE.Vector3());
  useEffect(() => {
    const pos = positionAtMD(stations, depth);
    if (pos) targetRef.current.copy(pos);
  }, [stations, depth]);
  useFrame((_, delta) => {
    if (meshRef.current) meshRef.current.position.lerp(targetRef.current, Math.min(1, delta * 6));
  });
  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.07, 16, 16]} />
      <meshStandardMaterial color="#22d3ee" emissive="#22d3ee" emissiveIntensity={1.3} />
    </mesh>
  );
}

interface CommandScene3DProps {
  activeTrajectory: WellTrajectory | null;
  offsetTrajectory: WellTrajectory | null;
  formations: FormationTop[];
  events: DrillingEvent[];
  corridors: RiskCorridor[];
  depth: number;
  offsetWellName?: string;
  onEventClick: (e: DrillingEvent) => void;
}

const PRESET_META: Record<CameraPreset, { label: string; icon: React.ElementType }> = {
  RIG_FLOOR: { label: 'Rig Floor', icon: Compass },
  CROSS_SECTION: { label: 'Cross-Section', icon: Layers },
  DOWNHOLE_FOLLOW: { label: 'Downhole Follow', icon: Radio },
  PLAN: { label: 'Plan View', icon: MapIcon },
  ORBIT: { label: 'Free Orbit', icon: Eye },
};

export const CommandScene3D: React.FC<CommandScene3DProps> = ({
  activeTrajectory, offsetTrajectory, formations, events, corridors, depth, offsetWellName, onEventClick,
}) => {
  const [preset, setPreset] = useState<CameraPreset>('RIG_FLOOR');
  const [hovered, setHovered] = useState<DrillingEvent | null>(null);
  const [OrbitControlsComp, setOrbitControlsComp] = useState<any>(null);
  const bitPositionRef = useRef(new THREE.Vector3());

  useEffect(() => {
    import('@react-three/drei').then((m) => setOrbitControlsComp(() => m.OrbitControls));
  }, []);

  const stations = activeTrajectory?.stations ?? [];
  const maxTvd = Math.max(...stations.map((s) => s.tvd_m), 1000);
  const extent = Math.max(maxTvd * SCALE * 0.8, 3);

  useEffect(() => {
    const pos = positionAtMD(stations, depth);
    if (pos) bitPositionRef.current.copy(pos);
  }, [stations, depth]);

  if (!activeTrajectory || stations.length < 2) {
    return (
      <div className="w-full h-full bg-[#050709] flex items-center justify-center text-slate-500 font-mono text-xs">
        No real trajectory data for this well.
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[#050709]">
      <Canvas camera={{ position: [extent * 0.9, extent * 0.6, extent * 0.9], fov: 55 }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 15, 10]} intensity={1.3} />
        <hemisphereLight args={['#1e293b', '#0a0d13', 0.4]} />

        <FormationBands formations={formations} extent={extent} />
        <WellboreTube stations={stations} color="#06b6d4" radius={0.045} />
        {offsetTrajectory && offsetTrajectory.stations.length > 1 && (
          <WellboreTube stations={offsetTrajectory.stations} color="#f59e0b" radius={0.035} opacity={0.7} />
        )}
        <HazardCorridorBands corridors={corridors} stations={stations} />
        <EventMarkers events={events} stations={stations} onHover={setHovered} onClick={onEventClick} />
        <Bit stations={stations} depth={depth} />

        <CameraRig preset={preset} bitPosition={bitPositionRef} extent={extent} />
        {preset === 'ORBIT' && OrbitControlsComp && <OrbitControlsComp enableDamping dampingFactor={0.08} />}

        <gridHelper args={[extent * 4, 20, '#1e293b', '#0f172a']} position={[0, 0.01, 0]} />
      </Canvas>

      <div className="absolute top-3 left-3 bg-slate-950/90 border border-slate-800 rounded-lg p-1.5 flex gap-1">
        {CAMERA_PRESET_LIST.map((key) => {
          const meta = PRESET_META[key];
          const Icon = meta.icon;
          const active = preset === key;
          return (
            <button key={key} onClick={() => setPreset(key)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] font-mono transition-colors ${
                active ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {meta.label}
            </button>
          );
        })}
      </div>

      <div className="absolute top-3 right-3 bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-2 text-[11px] font-mono space-y-1">
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-cyan-500" /> Active well</div>
        {offsetTrajectory && <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> {offsetWellName ?? 'Offset well'}</div>}
        {corridors.length > 0 && <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Hazard corridor</div>}
      </div>

      {hovered && (
        <div className="absolute bottom-3 left-3 bg-slate-950/95 border border-rose-500/40 rounded p-2.5 text-xs font-mono max-w-xs pointer-events-none">
          <div className="text-rose-400 font-bold">{hovered.event_type} · {hovered.severity}</div>
          <div className="text-slate-300 mt-1">{hovered.depth_start_md_m.toFixed(0)}m MD · {hovered.formation ?? 'n/a'}</div>
          <div className="text-slate-400 mt-1 leading-snug">{hovered.raw_narrative || hovered.outcome || 'No narrative recorded'}</div>
        </div>
      )}
    </div>
  );
};
