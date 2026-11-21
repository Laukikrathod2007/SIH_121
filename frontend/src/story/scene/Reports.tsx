import React, { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { DDRS, KEY_DDR } from '../phases';
import { EXTRACT_EYE, GRID_CENTRE, type StoryState } from './state';

// The 39 daily drilling reports (one per real DDR in the demo set), as
// physical pages in the scene.
//   buried  : they drift in over the basin as a loose, overlapping cloud,
//             the one that matters lost among them.
//   extract : the cloud orders itself into a neat grid ("the archive,
//             read"), each page tagged with its event, and the key page
//             (BGJ-007, kick at 2,905.3 m) lifts out and lights up.

// Pages are drawn at "billboard" size over the basin (scene units = km).
const W = 0.34;
const H = 0.44;

const EVENT_COLOR: Record<string, string> = {
  KICK: '#ef4444',
  MUD_LOSS: '#f59e0b',
  STUCK_PIPE: '#a78bfa',
  WELLBORE_INSTABILITY: '#60a5fa',
  CEMENTING_FAILURE: '#94a3b8',
  TORQUE_SPIKE: '#34d399',
};

function pageTexture(well: string, md: number, type: string, key: boolean, extracted: boolean): THREE.Texture {
  const c = document.createElement('canvas');
  c.width = 256;
  c.height = 332;
  const g = c.getContext('2d')!;
  g.fillStyle = '#e9e4d8';
  g.fillRect(0, 0, 256, 332);
  g.fillStyle = '#1f2937';
  g.font = '600 15px Inter, sans-serif';
  g.fillText('OIL INDIA LIMITED', 16, 26);
  g.font = '500 12px Inter, sans-serif';
  g.fillStyle = '#4b5563';
  g.fillText(`Daily Drilling Report · ${well}`, 16, 46);
  g.fillRect(16, 56, 224, 1);
  // body lines, slightly irregular, like a typed report
  let seed = Math.floor(md * 7);
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 17; i++) {
    const y = 76 + i * 13;
    g.fillStyle = 'rgba(55,65,81,0.42)';
    g.fillRect(16, y, 120 + rnd() * 100, 4);
  }
  if (extracted) {
    // the extracted event, stamped on the page
    g.fillStyle = EVENT_COLOR[type] ?? '#94a3b8';
    g.fillRect(0, 300, 256, 32);
    g.fillStyle = '#0b0f14';
    g.font = '700 13px "JetBrains Mono", monospace';
    g.fillText(`${type.replace('_', ' ')} · ${md.toFixed(1)} m`, 12, 321);
  }
  if (key) {
    g.strokeStyle = '#f59e0b';
    g.lineWidth = 6;
    g.strokeRect(3, 3, 250, 326);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

export function Reports({ state }: { state: React.MutableRefObject<StoryState> }) {
  // A camera-facing frame at the grid: right, up, and toward the camera.
  const frame = useMemo(() => {
    const toCam = EXTRACT_EYE.clone().sub(GRID_CENTRE).normalize();
    const right = new THREE.Vector3(0, 1, 0).cross(toCam).normalize();
    const up = toCam.clone().cross(right).normalize();
    const o = new THREE.Object3D();
    o.position.copy(GRID_CENTRE);
    o.lookAt(EXTRACT_EYE);
    const at = (r: number, u: number, c: number) => GRID_CENTRE.clone().addScaledVector(right, r).addScaledVector(up, u).addScaledVector(toCam, c);
    return { at, q: o.quaternion.clone(), light: at(0, 1, 2.5) };
  }, []);

  const pages = useMemo(() => {
    let seed = 99;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    return DDRS.map(([well, md, type], i) => {
      const key = i === KEY_DDR;
      // Loose cloud around the grid, scattered in depth along the view.
      const cloud = frame.at((rnd() - 0.5) * 7, (rnd() - 0.5) * 3.2, (rnd() - 0.5) * 5);
      const cloudRot = new THREE.Euler((rnd() - 0.5) * 1.4, (rnd() - 0.5) * 2.4, (rnd() - 0.5) * 0.9);
      // Ordered grid facing the camera (the extracted state).
      const col = i % 13;
      const row = Math.floor(i / 13);
      const grid = frame.at((col - 6) * 0.4, (1 - row) * 0.52, 0);
      return {
        well,
        md,
        type,
        key,
        cloud,
        cloudRot,
        grid,
        texRaw: pageTexture(well, md, type, false, false),
        texDone: pageTexture(well, md, type, key, true),
        drift: rnd() * Math.PI * 2,
      };
    });
  }, [frame]);

  const meshes = useRef<(THREE.Mesh | null)[]>([]);
  const group = useRef<THREE.Group>(null);
  const tmpQ = useMemo(() => new THREE.Quaternion(), []);
  const gridQ = frame.q;
  // The key page lifts toward the camera, a little left of centre.
  const keyAt = useMemo(() => frame.at(-0.7, 0.2, 3.6), [frame]);

  useFrame(() => {
    const s = state.current;
    if (group.current) group.current.visible = s.paper > 0.001;
    if (s.paper <= 0.001) return;
    pages.forEach((pg, i) => {
      const m = meshes.current[i];
      if (!m) return;
      const order = Math.min(1, Math.max(0, s.paperOrder * 1.25 - (i / pages.length) * 0.25));
      // drift while loose
      const bob = Math.sin(s.time * 0.6 + pg.drift) * 0.08 * (1 - order);
      m.position.copy(pg.cloud).lerp(pg.grid, order);
      m.position.y += bob;
      // The key page lifts out toward the camera once the archive is read.
      if (pg.key) {
        const lift = Math.min(1, Math.max(0, (s.paperOrder - 0.7) / 0.3));
        m.position.lerp(keyAt, lift);
        m.scale.setScalar(1 + lift * 1.2);
      }
      tmpQ.setFromEuler(new THREE.Euler(pg.cloudRot.x + Math.sin(s.time * 0.4 + pg.drift) * 0.05, pg.cloudRot.y, pg.cloudRot.z));
      m.quaternion.copy(tmpQ).slerp(gridQ, order);
      const mat = m.material as THREE.MeshStandardMaterial;
      mat.map = order > 0.5 ? pg.texDone : pg.texRaw;
      mat.opacity = s.paper * (order > 0.5 && !pg.key ? 0.8 : 1);
      mat.emissiveIntensity = pg.key && order > 0.7 ? 0.5 : 0.08;
    });
  });

  return (
    <group ref={group}>
      {/* A cool fill light so the pages read against the dusk sky */}
      <pointLight position={frame.light} intensity={18} distance={14} color="#dbe7f3" />
      {pages.map((pg, i) => (
        <mesh key={i} ref={(r) => (meshes.current[i] = r)} castShadow>
          <planeGeometry args={[W, H]} />
          <meshStandardMaterial map={pg.texRaw} side={THREE.DoubleSide} transparent roughness={0.9} emissive="#fff3dd" emissiveMap={pg.texDone} emissiveIntensity={0.08} />
        </mesh>
      ))}
    </group>
  );
}
