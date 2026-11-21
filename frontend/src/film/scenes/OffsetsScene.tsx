import React, { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { FALLBACK_MAP_WELLS } from '../../data/fallbackWells';
import { haversineKm } from '../../lib/globeGeometry';
import { contourTexture, glowTexture, STRATA } from '../textures';
import { ACT, clamp, easeInOut, lerp, smoothstep } from '../timeline';
import type { FilmClock } from '../clock';

// The map. The basin seen from above at night: the active well at the
// centre, every nearby well in the dataset at its real position. A search
// radius sweeps out; a fault splits the field; wells across it go dark.
// Then the camera tilts below the surface and the shared formation shows
// as one continuous layer under the wells that matter.
//
// Real data: positions are the NWIS dataset's real lat/lon (projected
// locally, 1 unit = 1 km). The highlighted analogs are the three wells
// with Kopili-hosted events in the dataset (NHK-001 mud loss at 2,658 m,
// NHK-003 kick at 2,664 m, BGJ-007 kick at 2,905 m). The fault line is
// illustrative.

const ACTIVE_ID = 'WELL-NHK-002';
const ANALOGS = new Map<string, number>([
  ['WELL-NHK-001', 2658],
  ['WELL-NHK-003', 2664],
  ['WELL-BGJ-007', 2905],
]);
// Wells shown across the fault (dimmed). The Moran/Hugrijan wells sit to
// the south-west of the active well, across the illustrative fault.
const ACROSS_FAULT = new Set(['WELL-MRN-004', 'WELL-MRN-005', 'WELL-MRN-006', 'WELL-HGJ-010', 'WELL-HGJ-011', 'WELL-HGJ-012']);

const DEPTH_SCALE = 0.009; // 1 km of depth -> 9 units, exaggerated for legibility
const KOPILI = STRATA.find((s) => s.name === 'KOPILI')!;

const active = FALLBACK_MAP_WELLS.find((w) => w.well_id === ACTIVE_ID)!;

function project(lat: number, lon: number): [number, number] {
  const x = haversineKm(active.lat, active.lon, active.lat, lon) * Math.sign(lon - active.lon);
  const z = -haversineKm(active.lat, active.lon, lat, active.lon) * Math.sign(lat - active.lat);
  return [x, z];
}

interface MapWell {
  id: string;
  name: string;
  x: number;
  z: number;
  kind: 'active' | 'analog' | 'fault' | 'other';
  eventMd?: number;
  dist: number;
}

const WELLS: MapWell[] = FALLBACK_MAP_WELLS.map((w) => {
  const [x, z] = project(w.lat, w.lon);
  const kind: MapWell['kind'] =
    w.well_id === ACTIVE_ID ? 'active' : ANALOGS.has(w.well_id) ? 'analog' : ACROSS_FAULT.has(w.well_id) ? 'fault' : 'other';
  return { id: w.well_id, name: w.well_name, x, z, kind, eventMd: ANALOGS.get(w.well_id), dist: Math.hypot(x, z) };
});

// Fault trace: runs roughly N–S, west of the active well, separating the
// Moran and Hugrijan wells (x < -24 km) from the Nahorkatiya/Baghjan side.
const FAULT: [number, number][] = [
  [-8, -52],
  [-13, -26],
  [-12, -2],
  [-17, 22],
  [-14, 50],
];

const COLOR = { active: '#ffb067', analog: '#67e8f9', fault: '#64748b', other: '#94a3b8' };

/** One well: surface light, plus (later) its bore dropping to its event depth. */
function Well({ w, clock }: { w: MapWell; clock: FilmClock }) {
  const glow = glowTexture();
  const head = useRef<THREE.Sprite>(null);
  const halo = useRef<THREE.Sprite>(null);
  const bore = useRef<THREE.Mesh>(null);
  const mark = useRef<THREE.Sprite>(null);
  const color = new THREE.Color(COLOR[w.kind]);
  // The active well's bore ends at its planned Kopili crossing.
  const boreDepth = (w.kind === 'active' ? KOPILI.top : w.eventMd ?? 2800) * DEPTH_SCALE;

  useFrame(() => {
    const lt = clock.t - ACT.offsets.start;
    // The radius sweep reaches a well at roughly the time it passes it.
    const reached = smoothstep(w.dist / 13, w.dist / 13 + 0.5, lt - 0.6);
    const faultDim = w.kind === 'fault' ? 1 - 0.8 * smoothstep(7.4, 9.4, lt) : 1;
    const otherDim = w.kind === 'other' ? 1 - 0.55 * smoothstep(12.2, 13.8, lt) : 1;
    const focus = w.kind === 'analog' ? 1 + 0.6 * smoothstep(12.2, 13.8, lt) : 1;
    const base = w.kind === 'active' ? 1 : reached;
    const o = base * faultDim * otherDim;

    const pulse = w.kind === 'active' ? 0.8 + Math.sin(clock.t * 2.2) * 0.2 : 1;
    if (head.current) {
      head.current.scale.setScalar((w.kind === 'active' ? 1.6 : 1.0) * focus);
      (head.current.material as THREE.SpriteMaterial).opacity = o;
    }
    if (halo.current) {
      halo.current.scale.setScalar((w.kind === 'active' ? 7 : 4.2) * pulse * focus);
      (halo.current.material as THREE.SpriteMaterial).opacity = 0.45 * o * pulse;
    }
    // Bores grow down once the camera has gone below the surface.
    const grow = w.kind === 'active' || w.kind === 'analog' ? easeInOut(clamp((lt - 12.6) / 3.2)) : 0;
    if (bore.current) {
      bore.current.scale.y = Math.max(0.0001, grow);
      bore.current.position.y = (-boreDepth * grow) / 2;
      (bore.current.material as THREE.MeshBasicMaterial).opacity = 0.75 * grow;
    }
    if (mark.current) {
      // The event in each analog well, and the active well's planned
      // crossing into the same formation, light up at their depths.
      const m = w.kind === 'analog' || w.kind === 'active' ? smoothstep(15.4, 16.4, lt) : 0;
      mark.current.position.y = -boreDepth;
      mark.current.scale.setScalar((w.kind === 'active' ? 3.4 : 4.2) + Math.sin(clock.t * 3) * 0.5);
      (mark.current.material as THREE.SpriteMaterial).opacity = m;
    }
  });

  return (
    <group position={[w.x, 0, w.z]}>
      <sprite ref={halo} position={[0, 0.2, 0]}>
        <spriteMaterial map={glow} color={color} transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} />
      </sprite>
      <sprite ref={head} position={[0, 0.2, 0]}>
        <spriteMaterial map={glow} color={'#ffffff'} transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} />
      </sprite>
      <mesh ref={bore} scale={[1, 0.0001, 1]}>
        <cylinderGeometry args={[0.22, 0.22, boreDepth, 10]} />
        <meshBasicMaterial color={color} transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} fog={false} />
      </mesh>
      <sprite ref={mark}>
        <spriteMaterial map={glow} color="#ff7a3d" transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} fog={false} />
      </sprite>
    </group>
  );
}

/** Search radius: a thin ring sweeping outward from the active well. */
function RadiusSweep({ clock }: { clock: FilmClock }) {
  const ring = useRef<THREE.Mesh>(null);
  const fill = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const lt = clock.t - ACT.offsets.start;
    const r = lerp(0.5, 60, easeInOut(clamp((lt - 0.6) / 4.8)));
    ring.current?.scale.setScalar(r);
    fill.current?.scale.setScalar(r);
    const o = smoothstep(0.4, 1.2, lt) * (1 - 0.6 * smoothstep(12, 14, lt));
    if (ring.current) (ring.current.material as THREE.MeshBasicMaterial).opacity = 0.7 * o;
    if (fill.current) (fill.current.material as THREE.MeshBasicMaterial).opacity = 0.05 * o;
  });
  return (
    <group rotation-x={-Math.PI / 2} position={[0, 0.05, 0]}>
      <mesh ref={ring}>
        <ringGeometry args={[0.985, 1, 160]} />
        <meshBasicMaterial color="#67e8f9" transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <mesh ref={fill}>
        <circleGeometry args={[1, 96]} />
        <meshBasicMaterial color="#67e8f9" transparent opacity={0} blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
    </group>
  );
}

/** The fault: a red line drawn across the field, then a curtain dropping from it. */
function Fault({ clock }: { clock: FilmClock }) {
  const { line, curtain } = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3(FAULT.map(([x, z]) => new THREE.Vector3(x, 0.1, z)));
    const pts = curve.getPoints(120);
    const lg = new THREE.BufferGeometry().setFromPoints(pts);
    const line = new THREE.Line(lg, new THREE.LineBasicMaterial({ color: '#ff5a3c', transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false }));
    // Curtain: a vertical ribbon under the trace, fading with depth.
    const verts: number[] = [];
    const uvs: number[] = [];
    const depth = 32;
    pts.forEach((p, i) => {
      verts.push(p.x, 0, p.z, p.x, -depth, p.z);
      uvs.push(i / (pts.length - 1), 1, i / (pts.length - 1), 0);
    });
    const idx: number[] = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const a = i * 2;
      idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
    const cg = new THREE.BufferGeometry();
    cg.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
    cg.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    cg.setIndex(idx);
    const c = document.createElement('canvas');
    c.width = 4;
    c.height = 128;
    const g = c.getContext('2d')!;
    const grad = g.createLinearGradient(0, 0, 0, 128);
    grad.addColorStop(0, 'rgba(255,90,60,0.55)');
    grad.addColorStop(1, 'rgba(255,90,60,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 4, 128);
    const tex = new THREE.CanvasTexture(c);
    const curtain = new THREE.Mesh(
      cg,
      new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: 0, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    return { line, curtain, count: pts.length };
  }, []);
  useFrame(() => {
    const lt = clock.t - ACT.offsets.start;
    const draw = easeInOut(clamp((lt - 6.6) / 1.6));
    line.geometry.setDrawRange(0, Math.floor(draw * 121));
    (line.material as THREE.LineBasicMaterial).opacity = 0.95 * smoothstep(6.6, 7.0, lt);
    (curtain.material as THREE.MeshBasicMaterial).opacity = 0.7 * smoothstep(12.6, 15, lt);
  });
  return (
    <>
      <primitive object={line} />
      <primitive object={curtain} />
    </>
  );
}

/**
 * The shared formation below the map, on the active well's side of the
 * fault: a translucent Kopili layer that the analog bores pierce.
 */
function KopiliLayer({ clock }: { clock: FilmClock }) {
  const ref = useRef<THREE.Mesh>(null);
  const geo = useMemo(() => {
    // A gently undulating sheet clipped to the east side of the fault.
    const g = new THREE.PlaneGeometry(130, 130, 80, 80);
    g.rotateX(-Math.PI / 2);
    const pos = g.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      pos.setY(i, -KOPILI.top * DEPTH_SCALE + Math.sin(x * 0.08) * 0.6 + Math.cos(z * 0.06) * 0.8 + x * 0.004);
    }
    g.computeVertexNormals();
    return g;
  }, []);
  // Clip the sheet to the active side of the fault with a plane through it.
  const clip = useMemo(() => {
    const [ax, az] = FAULT[0];
    const [bx, bz] = FAULT[FAULT.length - 1];
    const dir = new THREE.Vector3(bx - ax, 0, bz - az).normalize();
    const normal = new THREE.Vector3(dir.z, 0, -dir.x);
    // Keep the side containing the active well (origin).
    const p = new THREE.Plane().setFromNormalAndCoplanarPoint(normal, new THREE.Vector3(ax, 0, az));
    if (p.distanceToPoint(new THREE.Vector3(0, 0, 0)) < 0) p.negate();
    return [p];
  }, []);
  useFrame(() => {
    const lt = clock.t - ACT.offsets.start;
    if (ref.current) (ref.current.material as THREE.MeshBasicMaterial).opacity = 0.16 * smoothstep(13.6, 16.2, lt);
  });
  return (
    <mesh ref={ref} geometry={geo}>
      <meshBasicMaterial color="#c8683c" transparent opacity={0} side={THREE.DoubleSide} depthWrite={false} clippingPlanes={clip} blending={THREE.AdditiveBlending} fog={false} />
    </mesh>
  );
}

export function OffsetsScene({ clock }: { clock: FilmClock }) {
  const { camera, gl, scene } = useThree();
  const map = contourTexture();

  React.useEffect(() => {
    gl.localClippingEnabled = true;
    scene.fog = new THREE.FogExp2('#020407', 0.0065);
    return () => {
      gl.localClippingEnabled = false;
      scene.fog = null;
    };
  }, [gl, scene]);

  useFrame(() => {
    const lt = clock.t - ACT.offsets.start;
    const pc = camera as THREE.PerspectiveCamera;
    // 1. Top-down, slowly rotating, as the radius sweeps and the fault cuts.
    // 2. Tilt down to a low oblique, then drop the eye below the surface
    //    so the shared formation and the analog bores are seen side-on.
    // Field centre for the framing: between the active well and the
    // analogs, so all three plus the fault fit the frame.
    const tilt = easeInOut(clamp((lt - 11.6) / 4.6));
    const rot = lerp(0.25, -0.2, clamp(lt / 19));
    const cx = lerp(-6, 5, tilt);
    const cz = lerp(4, -2, tilt);
    const height = lerp(118, -14, tilt);
    const dist = lerp(8, 70, tilt);
    camera.position.set(cx + Math.sin(rot) * dist, height, cz + Math.cos(rot) * dist);
    camera.up.set(0, 1, 0);
    camera.lookAt(cx, lerp(0, -20, tilt), cz);
    pc.fov = lerp(44, 38, tilt);
    pc.near = 0.1;
    pc.updateProjectionMatrix();
  });

  return (
    <>
      <color attach="background" args={['#020407']} />
      <ambientLight intensity={0.4} />
      <mesh rotation-x={-Math.PI / 2} position={[0, -0.05, 0]}>
        <planeGeometry args={[260, 260]} />
        <meshBasicMaterial map={map} transparent opacity={0.9} depthWrite={false} />
      </mesh>
      <RadiusSweep clock={clock} />
      <Fault clock={clock} />
      <KopiliLayer clock={clock} />
      {WELLS.map((w) => (
        <Well key={w.id} w={w} clock={clock} />
      ))}
    </>
  );
}
