import React, { useMemo, useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { SurveyStation, WellTrajectory, FormationTop, TelemetryData } from '../types';
import { Radio, Compass, Layers, Eye } from 'lucide-react';
import { stationToVec3, positionAtMD, TRAJECTORY_SCALE as SCALE } from '../lib/trajectoryGeometry';
import { CameraRig, CameraPreset } from './three/CameraRig';

const RIG_HEIGHT = 3.2; // scene units above the surface (derrick mast height)

const FORMATION_PALETTE = ['#78350f', '#92400e', '#57534e', '#3f3f46', '#1c1917', '#44403c', '#065f46', '#374151'];

// ---------------------------------------------------------------------------
// Procedural derrick -- original geometry (box/cylinder primitives), not
// sourced from any reference asset. A placeholder for a higher-fidelity
// Blender-exported rig model later; functionally real and to-scale now,
// not a photoreal claim.
// ---------------------------------------------------------------------------
function Derrick() {
  const legOffsets: [number, number][] = [
    [0.55, 0.55], [-0.55, 0.55], [0.55, -0.55], [-0.55, -0.55],
  ];
  return (
    <group>
      {/* Base platform */}
      <mesh position={[0, 0.05, 0]}>
        <boxGeometry args={[1.6, 0.1, 1.6]} />
        <meshStandardMaterial color="#3a3f4a" metalness={0.6} roughness={0.5} />
      </mesh>
      {/* Four angled legs converging to the crown block */}
      {legOffsets.map(([x, z], i) => {
        const top = new THREE.Vector3(0, RIG_HEIGHT, 0);
        const bottom = new THREE.Vector3(x, 0.1, z);
        const mid = bottom.clone().lerp(top, 0.5);
        const dir = top.clone().sub(bottom);
        const len = dir.length();
        const quaternion = new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 1, 0), dir.clone().normalize()
        );
        return (
          <mesh key={i} position={mid} quaternion={quaternion}>
            <cylinderGeometry args={[0.04, 0.06, len, 8]} />
            <meshStandardMaterial color="#e0a030" metalness={0.7} roughness={0.4} />
          </mesh>
        );
      })}
      {/* Crown block at the top */}
      <mesh position={[0, RIG_HEIGHT, 0]}>
        <boxGeometry args={[0.5, 0.15, 0.5]} />
        <meshStandardMaterial color="#2a2f38" metalness={0.7} roughness={0.4} />
      </mesh>
      {/* Traveling block / hook, roughly mid-mast */}
      <mesh position={[0, RIG_HEIGHT * 0.7, 0]}>
        <boxGeometry args={[0.22, 0.12, 0.22]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Kelly / top drive line down to the wellhead */}
      <mesh position={[0, RIG_HEIGHT * 0.35, 0]}>
        <cylinderGeometry args={[0.015, 0.015, RIG_HEIGHT * 0.7, 6]} />
        <meshStandardMaterial color="#64748b" metalness={0.8} roughness={0.3} />
      </mesh>
    </group>
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
            <meshStandardMaterial color={color} transparent opacity={0.35} depthWrite={false} />
          </mesh>
        );
      })}
    </>
  );
}

function WellboreTube({ stations }: { stations: SurveyStation[] }) {
  const geometry = useMemo(() => {
    if (stations.length < 2) return null;
    const points = stations.map(stationToVec3);
    const curve = new THREE.CatmullRomCurve3(points);
    return new THREE.TubeGeometry(curve, Math.max(32, stations.length * 2), 0.035, 8, false);
  }, [stations]);
  if (!geometry) return null;
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color="#94a3b8" metalness={0.7} roughness={0.35} />
    </mesh>
  );
}

// Live, real-time bit position -- driven by the actual live telemetry
// stream (real-time simulated physics engine over WebSocket, the same
// `telemetry` object every other live page in this app reads from), not a
// scripted animation. Smoothly interpolates toward each new real depth
// reading rather than snapping, so motion reads as continuous drilling.
//
// Carries its own point light. The scene's surface lights (ambient,
// directional, hemisphere) only reach the derrick near Y=0 -- at real
// drilling depths (thousands of scene units down at TRAJECTORY_SCALE) a
// live/downhole/cross-section camera has nothing lit to look at except
// this one emissive sphere. Without a light that travels with the bit,
// DOWNHOLE_FOLLOW and CROSS_SECTION render as a single glowing dot in an
// otherwise black frame -- confirmed live, not theoretical.
function LiveBit({ stations, measuredDepthM, extent }: { stations: SurveyStation[]; measuredDepthM: number; extent: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const lightRef = useRef<THREE.PointLight>(null);
  const targetRef = useRef(new THREE.Vector3());

  useEffect(() => {
    const pos = positionAtMD(stations, measuredDepthM);
    if (pos) targetRef.current.copy(pos);
  }, [stations, measuredDepthM]);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.position.lerp(targetRef.current, Math.min(1, delta * 4));
      lightRef.current?.position.copy(meshRef.current.position);
    }
  });

  // `distance` must scale with the scene's own extent, not a fixed
  // constant -- a real trajectory's extent (maxTvd * TRAJECTORY_SCALE)
  // can be 10-100+ scene units depending on the well's total depth, and a
  // DOWNHOLE_FOLLOW camera sits ~extent*0.4-0.57 away from the bit
  // (CameraRig.tsx). A fixed distance:6 light (the first attempt at this
  // fix) couldn't reach the camera's own position for any well deeper
  // than a few hundred meters -- confirmed live: still rendered black.
  const lightRange = Math.max(extent * 1.2, 4);

  return (
    <>
      <pointLight ref={lightRef} color="#67e8f9" intensity={extent * 8} distance={lightRange} decay={2} />
      <mesh ref={meshRef}>
        <sphereGeometry args={[Math.max(extent * 0.015, 0.06), 16, 16]} />
        <meshStandardMaterial color="#22d3ee" emissive="#22d3ee" emissiveIntensity={1.2} />
      </mesh>
    </>
  );
}

// ---------------------------------------------------------------------------
// Camera perspective system -- the actual "various perspectives" feature.
// Each preset smoothly lerps position/target every frame rather than
// cutting instantly, so switching feels like moving through the same live
// scene, not loading a different one.
// ---------------------------------------------------------------------------
interface LiveDrillingScene3DProps {
  trajectory: WellTrajectory | null;
  formations: FormationTop[];
  telemetry: TelemetryData | null;
  wellName: string;
}

const PRESET_LABELS: { key: CameraPreset; label: string; icon: React.ElementType }[] = [
  { key: 'RIG_FLOOR', label: 'Rig Floor', icon: Compass },
  { key: 'CROSS_SECTION', label: 'Cross-Section', icon: Layers },
  { key: 'DOWNHOLE_FOLLOW', label: 'Downhole Follow', icon: Radio },
  { key: 'ORBIT', label: 'Free Orbit', icon: Eye },
];

export const LiveDrillingScene3D: React.FC<LiveDrillingScene3DProps> = ({
  trajectory, formations, telemetry, wellName,
}) => {
  const [preset, setPreset] = useState<CameraPreset>('RIG_FLOOR');
  const bitPositionRef = useRef(new THREE.Vector3());
  const [OrbitControlsComp, setOrbitControlsComp] = useState<any>(null);

  useEffect(() => {
    import('@react-three/drei').then((m) => setOrbitControlsComp(() => m.OrbitControls));
  }, []);

  const stations = trajectory?.stations ?? [];
  const maxTvd = Math.max(...stations.map((s) => s.tvd_m), 1000);
  const extent = Math.max(maxTvd * SCALE * 0.7, 3);
  const measuredDepthM = telemetry?.measured_depth_m ?? (stations[0]?.md_m ?? 0);

  useEffect(() => {
    const pos = positionAtMD(stations, measuredDepthM);
    if (pos) bitPositionRef.current.copy(pos);
  }, [stations, measuredDepthM]);

  return (
    <div className="relative w-full h-full bg-[#050709]">
      <Canvas camera={{ position: [extent * 0.9, RIG_HEIGHT * 0.6, extent * 0.9], fov: 55 }}>
        {/* ambientLight/hemisphereLight apply uniformly regardless of depth,
            so they're what keeps the wellbore tube and formation bands
            visible (if dim) at real drilling depths where the directional
            light and the derrick itself are far out of range -- raised
            from the original 0.4/0.4 after confirming DOWNHOLE_FOLLOW/
            CROSS_SECTION rendered as a black frame with only those values
            and no light traveling with the bit (see LiveBit's own light). */}
        <ambientLight intensity={0.55} />
        <directionalLight position={[10, 15, 10]} intensity={1.3} />
        <hemisphereLight args={['#1e293b', '#0a0d13', 0.6]} />

        <Derrick />
        <FormationBands formations={formations} extent={extent} />
        {stations.length > 1 && <WellboreTube stations={stations} />}
        {stations.length > 1 && <LiveBit stations={stations} measuredDepthM={measuredDepthM} extent={extent} />}

        <CameraRig preset={preset} bitPosition={bitPositionRef} extent={extent} rigHeight={RIG_HEIGHT} />
        {preset === 'ORBIT' && OrbitControlsComp && <OrbitControlsComp enableDamping dampingFactor={0.08} />}

        {/* Grid floor for spatial reference */}
        <gridHelper args={[extent * 4, 20, '#1e293b', '#0f172a']} position={[0, 0.01, 0]} />
      </Canvas>

      {/* Perspective switcher -- the actual "multiple perspectives" control */}
      <div className="absolute top-3 left-3 bg-slate-950/90 border border-slate-800 rounded-lg p-1.5 flex gap-1">
        {PRESET_LABELS.map((p) => {
          const Icon = p.icon;
          const active = preset === p.key;
          return (
            <button
              key={p.key}
              onClick={() => setPreset(p.key)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[11px] font-mono transition-colors ${
                active ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {p.label}
            </button>
          );
        })}
      </div>

      <div className="absolute top-3 right-3 bg-slate-950/90 border border-slate-800 rounded-lg px-3 py-2 text-[11px] font-mono text-slate-300">
        <div className="text-cyan-400 font-bold">{wellName}</div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          LIVE · MD {measuredDepthM.toFixed(1)} m
        </div>
      </div>
    </div>
  );
};
