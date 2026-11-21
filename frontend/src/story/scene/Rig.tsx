import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import type { StoryState } from './state';

// A land drilling rig assembled at true scale (metres) from real equipment
// models: the CC0 "Offshore Oil Rig and Platform" pack on 3dassets.dev
// (public/story/rig, manifest.json). Laid out the way a land rig pad is:
// substructure + drill floor + derrick over the well, drawworks behind the
// floor, pipe on racks along the catwalk, mud tanks / pumps / shakers on
// one side, generators and fuel on the other, a flare well away from it.
//
// The whole rig is one group in metres; the scene scales it to km.

const BASE = '/story/rig/';
const PARTS = [
  'derrick-section', 'crown-block', 'travelling-block', 'drawworks', 'rotary-table', 'mud-pump', 'mud-tank',
  'mud-tank-agitated', 'shale-shaker', 'bop-stack', 'pipe-rack', 'pipe-stands', 'generator', 'diesel-tank',
  'floodlight-mast', 'flare-tip', 'cement-unit', 'bunk-cabin',
  // site dressing (other CC0 packs, same source)
  'fuel-tanker', 'flatbed-crane', 'site-office', 'container', 'fence-bay', 'light-tower', 'water-tank',
] as const;
type Part = (typeof PARTS)[number];

// Drill-floor height on the substructure (m). Land rigs of this class
// (1,500-2,000 hp, ~3-4 km wells) stand the floor 7-9 m up.
const FLOOR_Y = 8;
const DERRICK_SECTIONS = 5; // 5 x 8 m ≈ 40 m mast, + crown

function usePart(name: Part) {
  const { scene } = useGLTF(BASE + name + '.glb');
  return scene;
}

/** Clone a part, prep its materials for a dusk exterior, and place it. */
function Place({ name, p, r = 0, s = 1 }: { name: Part; p: [number, number, number]; r?: number; s?: number }) {
  const src = usePart(name);
  const obj = useMemo(() => {
    const o = src.clone(true);
    o.traverse((c) => {
      const m = c as THREE.Mesh;
      if (!m.isMesh) return;
      m.castShadow = true;
      m.receiveShadow = true;
      // Share materials across clones (fewer programs, faster first frame).
      const mat = m.material as THREE.MeshStandardMaterial;
      mat.envMapIntensity = 0.6;
    });
    return o;
  }, [src]);
  return <primitive object={obj} position={p} rotation-y={r} scale={s} />;
}

/** Substructure: the steel box the drill floor stands on. */
function Substructure() {
  const mat = useMemo(() => new THREE.MeshStandardMaterial({ color: '#3d4247', metalness: 0.7, roughness: 0.55 }), []);
  const beam = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  const legs: [number, number][] = [
    [-4.2, -4.2], [4.2, -4.2], [-4.2, 4.2], [4.2, 4.2], [0, -4.2], [0, 4.2],
  ];
  return (
    <group>
      {legs.map(([x, z], i) => (
        <mesh key={i} geometry={beam} material={mat} position={[x, FLOOR_Y / 2, z]} scale={[0.7, FLOOR_Y, 0.7]} castShadow />
      ))}
      {/* cross bracing */}
      {[-4.2, 4.2].map((x) => (
        <mesh key={x} geometry={beam} material={mat} position={[x, FLOOR_Y / 2, 0]} rotation-x={0.95} scale={[0.25, 11, 0.25]} castShadow />
      ))}
      <mesh geometry={beam} material={mat} position={[0, FLOOR_Y - 0.4, 0]} scale={[9.4, 0.8, 9.4]} castShadow receiveShadow />
      {/* Ramp / catwalk to the floor (pipe comes up this V-door side) */}
      <mesh geometry={beam} material={mat} position={[0, FLOOR_Y / 2 - 0.2, 12]} rotation-x={-0.52} scale={[1.6, 0.35, 17]} castShadow receiveShadow />
    </group>
  );
}

/** Gravel pad + cellar, so the rig sits on built ground, not on a field. */
function Pad() {
  const tex = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = c.height = 256;
    const g = c.getContext('2d')!;
    g.fillStyle = '#6d6a62';
    g.fillRect(0, 0, 256, 256);
    let s = 7;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < 9000; i++) {
      const v = 70 + rnd() * 70;
      g.fillStyle = `rgb(${v},${v - 4},${v - 10})`;
      g.fillRect(rnd() * 256, rnd() * 256, 1 + rnd() * 2, 1 + rnd() * 2);
    }
    // tyre tracks
    g.strokeStyle = 'rgba(40,36,30,0.35)';
    g.lineWidth = 6;
    for (let i = 0; i < 5; i++) {
      g.beginPath();
      g.moveTo(rnd() * 256, 0);
      g.bezierCurveTo(rnd() * 256, 90, rnd() * 256, 170, rnd() * 256, 256);
      g.stroke();
    }
    const t = new THREE.CanvasTexture(c);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(6, 6);
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, []);
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[2, 0.05, 6]} receiveShadow>
        <planeGeometry args={[130, 104]} />
        <meshStandardMaterial map={tex} roughness={0.98} color="#9a958a" />
      </mesh>
      {/* Lined mud / reserve pit: dark water in an HDPE-lined pit */}
      <mesh rotation-x={-Math.PI / 2} position={[40, 0.07, -18]} receiveShadow>
        <planeGeometry args={[26, 18]} />
        <meshStandardMaterial color="#1b1f1d" roughness={0.12} metalness={0.2} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2} position={[40, 0.06, -18]}>
        <planeGeometry args={[29, 21]} />
        <meshStandardMaterial color="#2a2e2f" roughness={0.6} />
      </mesh>
      {/* Access road off the pad */}
      <mesh rotation-x={-Math.PI / 2} position={[-6, 0.04, 110]} receiveShadow>
        <planeGeometry args={[8, 120]} />
        <meshStandardMaterial map={tex} color="#8f8a80" roughness={1} />
      </mesh>
    </group>
  );
}

/** Chain-link fence around the pad perimeter (4 m bays). */
function Fence() {
  const bays = useMemo(() => {
    const out: { p: [number, number, number]; r: number }[] = [];
    const x0 = -63;
    const x1 = 67;
    const z0 = -46;
    const z1 = 58;
    for (let x = x0; x < x1; x += 4) {
      out.push({ p: [x + 2, 0, z0], r: 0 });
      if (x + 2 < -10 || x + 2 > -2) out.push({ p: [x + 2, 0, z1], r: 0 }); // gate gap for the road
    }
    for (let z = z0; z < z1; z += 4) {
      out.push({ p: [x0, 0, z + 2], r: Math.PI / 2 });
      out.push({ p: [x1, 0, z + 2], r: Math.PI / 2 });
    }
    return out;
  }, []);
  return (
    <>
      {bays.map((b, i) => (
        <Place key={i} name="fence-bay" p={b.p} r={b.r} />
      ))}
    </>
  );
}

/** Lit flare: a flame and its light, flickering. */
function Flare({ state }: { state: React.MutableRefObject<StoryState> }) {
  const flame = useRef<THREE.Mesh>(null);
  const light = useRef<THREE.PointLight>(null);
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    const f = 0.82 + 0.18 * Math.sin(t * 11) * Math.sin(t * 6.7 + 1.3);
    if (flame.current) flame.current.scale.set(1.4 * f, 4.2 * f, 1.4 * f);
    // km-scale light (see WorkLights): 260 × 1e-6
    if (light.current) light.current.intensity = 260e-6 * f * (0.4 + state.current.night);
  });
  return (
    <group position={[-60, 0, -40]}>
      <mesh position={[0, 7, 0]} castShadow>
        <cylinderGeometry args={[0.35, 0.45, 14, 10]} />
        <meshStandardMaterial color="#4a4f55" metalness={0.6} roughness={0.5} />
      </mesh>
      <Place name="flare-tip" p={[0, 14, 0]} />
      <mesh ref={flame} position={[0, 21, 0]}>
        <sphereGeometry args={[1, 12, 12]} />
        <meshBasicMaterial color="#ff8a2a" transparent opacity={0.85} toneMapped={false} />
      </mesh>
      <pointLight ref={light} position={[0, 22, 0]} color="#ff7a26" distance={0.14} decay={2} />
    </group>
  );
}

/** Floodlights on the mast and pad: sodium-orange work lights at night. */
function WorkLights({ state }: { state: React.MutableRefObject<StoryState> }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(() => {
    const n = state.current.night;
    ref.current?.children.forEach((c) => {
      const l = c as THREE.SpotLight;
      if (l.isSpotLight) l.intensity = (l.userData.base as number) * n;
    });
  });
  // Work lights only start to read as the sun drops; in golden hour they
  // add a warm accent on the floor and pad, not a flood.
  const lights: [number, number, number, number][] = [
    [0, FLOOR_Y + 30, 2, 1800],
    [14, 7, 14, 900],
    [-16, 7, -6, 900],
    [16, 7, -14, 700],
  ];
  return (
    <group ref={ref}>
      {lights.map(([x, y, z, base], i) => {
        const target = new THREE.Object3D();
        target.position.set(x * 0.2, 0, z * 0.2 + 4);
        return (
          <React.Fragment key={i}>
            <primitive object={target} />
            {/* Light range and intensity don't scale with the parent group,
                so they're given in scene units (km): 0.11 = 110 m, and
                intensity ∝ distance² (decay 2) → base × 1e-6. */}
            <spotLight position={[x, y, z]} target={target} color="#ffad5c" angle={0.9} penumbra={0.8} distance={0.11} decay={2} intensity={0} userData={{ base: base * 1e-6 }} />
          </React.Fragment>
        );
      })}
    </group>
  );
}

export function LandRig({ state }: { state: React.MutableRefObject<StoryState> }) {
  // travelling block bobs slowly: the rig is working
  const block = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (block.current) block.current.position.y = FLOOR_Y + 14 + Math.sin(clock.elapsedTime * 0.35) * 4;
  });
  return (
    <group>
      <Pad />
      <Substructure />
      {/* Drill floor with rotary table, then the BOP stack under it in the cellar */}
      <Place name="rotary-table" p={[0, FLOOR_Y, 0]} />
      <Place name="bop-stack" p={[0, 0.2, 0]} />
      {/* Derrick: stacked 8 m sections and the crown block */}
      {Array.from({ length: DERRICK_SECTIONS }, (_, i) => (
        <Place key={i} name="derrick-section" p={[0, FLOOR_Y + 3.6 + i * 8.04, 0]} />
      ))}
      <Place name="crown-block" p={[0, FLOOR_Y + 3.6 + DERRICK_SECTIONS * 8.04, 0]} />
      <group ref={block}>
        <Place name="travelling-block" p={[0, 0, 0]} />
      </group>
      {/* Drawworks behind the floor, pipe setback on the floor */}
      <Place name="drawworks" p={[0, FLOOR_Y, -5.6]} />
      <Place name="pipe-rack" p={[-3.2, FLOOR_Y, 2.4]} r={Math.PI / 2} />
      {/* Catwalk and pipe on racks (V-door side) */}
      <Place name="pipe-stands" p={[-4, 0, 22]} r={Math.PI / 2} />
      <Place name="pipe-stands" p={[4, 0, 22]} r={Math.PI / 2} />
      {/* Mud system along the east side */}
      <Place name="shale-shaker" p={[11, 0, -2]} />
      <Place name="mud-tank" p={[17, 0, -2]} r={Math.PI / 2} />
      <Place name="mud-tank-agitated" p={[21.5, 0, -2]} r={Math.PI / 2} />
      <Place name="mud-tank-agitated" p={[26, 0, -2]} r={Math.PI / 2} />
      <Place name="mud-pump" p={[17, 0, -11]} />
      <Place name="mud-pump" p={[23, 0, -11]} />
      {/* Power and fuel on the west side */}
      <Place name="generator" p={[-14, 0, -8]} />
      <Place name="generator" p={[-14, 0, -12]} />
      <Place name="generator" p={[-14, 0, -16]} />
      <Place name="diesel-tank" p={[-22, 0, -12]} r={Math.PI / 2} />
      <Place name="cement-unit" p={[-12, 0, 8]} />
      {/* Crew cabins and the doghouse */}
      <Place name="bunk-cabin" p={[-28, 0, 14]} />
      <Place name="bunk-cabin" p={[-28, 0, 18]} />
      <Place name="bunk-cabin" p={[-28, 0, 22]} />
      {/* Floodlight masts at the pad corners */}
      <Place name="floodlight-mast" p={[14, 0, 14]} />
      <Place name="floodlight-mast" p={[-16, 0, -6]} />
      <Place name="floodlight-mast" p={[16, 0, -14]} />
      {/* Site: camp, trucks, stores, water, perimeter */}
      <Place name="site-office" p={[-44, 0, 34]} />
      <Place name="site-office" p={[-38, 0, 34]} />
      <Place name="container" p={[-40, 0, -24]} />
      <Place name="container" p={[-40, 0, -30]} />
      <Place name="container" p={[-32, 0, -30]} r={Math.PI / 2} />
      <Place name="fuel-tanker" p={[-24, 0, 40]} r={0.3} />
      <Place name="flatbed-crane" p={[10, 0, 44]} r={-0.4} />
      <Place name="water-tank" p={[30, 0, 6]} />
      <Place name="water-tank" p={[33.5, 0, 6]} />
      <Place name="light-tower" p={[-60, 0, -42]} r={0.8} />
      <Place name="light-tower" p={[63, 0, -42]} r={-0.8} />
      <Place name="light-tower" p={[63, 0, 54]} r={-2.3} />
      <Place name="light-tower" p={[-60, 0, 54]} r={2.3} />
      <Fence />
      <WorkLights state={state} />
      <Flare state={state} />
    </group>
  );
}

PARTS.forEach((p) => useGLTF.preload(BASE + p + '.glb'));
