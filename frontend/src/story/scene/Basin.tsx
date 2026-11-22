import React, { useMemo, useRef } from 'react';
import { useFrame, useLoader } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { VZ_S, VZ_T, basinWells, depthY, getBasin, horizonDepth, surfaceY, type BasinWell } from '../terrain';
import { LandRig } from './Rig';
import type { StoryState } from './state';

// The Upper Assam basin from real data: SRTM-based elevation with
// Sentinel-2 imagery draped on it (a sharper 10 km patch around the active
// well), the wells at their real positions, and the subsurface built from
// the wells' real formation tops. Driven every frame by `state`.

const AMBER = new THREE.Color('#f5a524');
const CYAN = new THREE.Color('#22d3ee');
const SLATE = new THREE.Color('#9aa8b8');
const RED = new THREE.Color('#ef4444');

// ---------------------------------------------------------------------------
// Terrain
// ---------------------------------------------------------------------------
function useTerrainGeometry() {
  return useMemo(() => {
    const b = getBasin();
    const W = b.meta.width_km;
    const H = b.meta.height_km;
    const segX = 640;
    const segZ = Math.round((segX * H) / W);
    const g = new THREE.PlaneGeometry(W, H, segX, segZ);
    g.rotateX(-Math.PI / 2);
    g.translate(b.x0 + W / 2, 0, b.z0 + H / 2);
    const pos = g.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) pos.setY(i, surfaceY(pos.getX(i), pos.getZ(i)));
    g.computeVertexNormals();
    return g;
  }, []);
}

function useTerrainMaterial() {
  const [sat, detail] = useLoader(THREE.TextureLoader, ['/story/basin-sat.jpg', '/story/basin-detail.jpg']);
  return useMemo(() => {
    for (const t of [sat, detail]) {
      t.colorSpace = THREE.SRGBColorSpace;
      t.anisotropy = 16;
      t.generateMipmaps = true;
      t.minFilter = THREE.LinearMipmapLinearFilter;
    }
    const b = getBasin();
    const m = new THREE.MeshStandardMaterial({ map: sat, roughness: 0.92, metalness: 0 });
    const uniforms = {
      uDetail: { value: detail },
      uDetailHalf: { value: b.meta.detail_km / 2 },
      uOrigin: { value: new THREE.Vector2(b.x0, b.z0) },
      uSize: { value: new THREE.Vector2(b.meta.width_km, b.meta.height_km) },
      uContour: { value: 0 },
      uRadius: { value: 0 },
      uRadiusOn: { value: 0 },
      uDim: { value: 0 },
      uTime: { value: 0 },
    };
    m.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, uniforms);
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWorld;')
        .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      shader.fragmentShader = shader.fragmentShader
        .replace(
          '#include <common>',
          `#include <common>
          uniform sampler2D uDetail;
          uniform float uDetailHalf;
          uniform vec2 uOrigin;
          uniform vec2 uSize;
          uniform float uContour;
          uniform float uRadius;
          uniform float uRadiusOn;
          uniform float uDim;
          uniform float uTime;
          varying vec3 vWorld;
          float cH(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
          float cN(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
            return mix(mix(cH(i), cH(i+vec2(1,0)), f.x), mix(cH(i+vec2(0,1)), cH(i+vec2(1,1)), f.x), f.y); }`,
        )
        .replace(
          '#include <map_fragment>',
          `
          // Regional Sentinel-2 mosaic, UV from world position.
          vec2 suv = (vWorld.xz - uOrigin) / uSize;
          vec4 sat = texture2D(map, vec2(suv.x, 1.0 - suv.y));
          // 10 m detail patch around the active well (origin), feathered in.
          vec2 duv = vWorld.xz / (2.0 * uDetailHalf) + 0.5;
          float din = smoothstep(0.0, 0.12, min(min(duv.x, duv.y), min(1.0 - duv.x, 1.0 - duv.y)));
          vec4 det = texture2D(uDetail, vec2(duv.x, 1.0 - duv.y));
          vec4 texel = mix(sat, det, din);
          // Sentinel-2 cloudless is dark and flat (a median composite). Lift
          // it into a natural range: contrast, a touch of saturation, and
          // exposure, before the scene's own sun and shadows go on top.
          texel.rgb = pow(texel.rgb, vec3(0.78)) * 1.6;
          float l = dot(texel.rgb, vec3(0.299, 0.587, 0.114));
          // More saturation and local contrast: fields, villages and river
          // bars read as distinct patches instead of a uniform wash.
          texel.rgb = mix(vec3(l), texel.rgb, 1.1);
          texel.rgb *= 1.0 - uDim;
          // Cloud shadows: soft, kilometre-scale, drifting slowly NW with
          // the wind. Barely there (up to ~12% darker).
          vec2 cp = vWorld.xz * 0.09 + vec2(uTime * 0.018, uTime * 0.011);
          float cshade = cN(cp) * 0.65 + cN(cp * 2.1 + 3.7) * 0.35;
          texel.rgb *= 1.0 - 0.12 * smoothstep(0.55, 0.8, cshade);
          diffuseColor *= texel;`,
        )
        .replace(
          '#include <roughnessmap_fragment>',
          `#include <roughnessmap_fragment>
          // Water (dark, low-green, low-red pixels in the imagery) is glossy.
          float wl = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
          float water = smoothstep(0.12, 0.05, wl) * smoothstep(0.0, 0.03, diffuseColor.b - diffuseColor.r * 0.6);
          roughnessFactor = mix(roughnessFactor, 0.18, water);`,
        )
        .replace(
          '#include <emissivemap_fragment>',
          `#include <emissivemap_fragment>
          // Topographic contours every 25 m of real elevation.
          float hm = vWorld.y / ${VZ_T.toFixed(1)} * 1000.0;
          float cl = abs(fract(hm / 25.0) - 0.5);
          float line = 1.0 - smoothstep(0.0, fwidth(hm / 25.0) * 1.2, cl);
          totalEmissiveRadiance += vec3(0.35, 0.7, 0.78) * line * 0.18 * uContour;
          // Search-radius ring around the active well.
          float d = length(vWorld.xz);
          float ring = 1.0 - smoothstep(0.0, 0.25 + d * 0.004, abs(d - uRadius));
          totalEmissiveRadiance += vec3(0.13, 0.83, 0.93) * (ring * 0.85 + step(d, uRadius) * 0.03) * uRadiusOn;`,
        );
    };
    return { material: m, uniforms };
  }, [sat, detail]);
}

export function Terrain({ state }: { state: React.MutableRefObject<StoryState> }) {
  const geo = useTerrainGeometry();
  const { material, uniforms } = useTerrainMaterial();
  useFrame(() => {
    const s = state.current;
    uniforms.uContour.value = s.contours;
    uniforms.uRadius.value = s.radiusKm;
    uniforms.uRadiusOn.value = s.radiusOn;
    uniforms.uDim.value = s.mapDim;
    uniforms.uTime.value = s.time;
    // Going below ground: the surface becomes a faint veil.
    const veil = 1 - 0.96 * s.cutaway;
    material.transparent = veil < 0.999;
    material.opacity = veil;
    material.depthWrite = veil > 0.6;
  });
  return <mesh geometry={geo} material={material} receiveShadow />;
}

// ---------------------------------------------------------------------------
// Decide: the alert, made visible on the ground. Three thin amber rings
// expand slowly from the rig and fade, like a sonar sweep: a calm, clear
// "this well, now" signal (not a flashing light).
// ---------------------------------------------------------------------------
function AlertRings({ x, y, z, state }: { x: number; y: number; z: number; state: React.MutableRefObject<StoryState> }) {
  const group = useRef<THREE.Group>(null);
  const rings = useMemo(
    () =>
      [0, 1, 2].map(() => {
        const m = new THREE.MeshBasicMaterial({ color: AMBER, transparent: true, opacity: 0, depthWrite: false, toneMapped: false, side: THREE.DoubleSide });
        return { m, geo: new THREE.RingGeometry(0.96, 1, 96) };
      }),
    [],
  );
  useFrame(() => {
    const s = state.current;
    if (!group.current) return;
    group.current.visible = s.alert > 0.01;
    if (!group.current.visible) return;
    group.current.children.forEach((c, i) => {
      const ph = (s.time * 0.28 + i / 3) % 1;
      // 40 m -> 1.4 km radius, fading as it grows
      c.scale.setScalar(0.04 + ph * 1.36);
      rings[i].m.opacity = s.alert * (1 - ph) * (1 - ph) * 0.85;
    });
  });
  return (
    <group ref={group} position={[x, y, z]} rotation-x={-Math.PI / 2}>
      {rings.map((r, i) => (
        <mesh key={i} geometry={r.geo} material={r.m} renderOrder={3} />
      ))}
    </group>
  );
}

// ---------------------------------------------------------------------------
// Offset-well wellhead: the CC0 christmas-tree model (public/story/rig).
// ---------------------------------------------------------------------------
const WELLHEAD_URL = '/story/rig/wellhead.glb';

function useModel(url: string) {
  const { scene } = useGLTF(url);
  return useMemo(() => {
    const s = scene.clone(true);
    s.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) m.castShadow = true;
    });
    return s;
  }, [scene]);
}

// ---------------------------------------------------------------------------
// Offset wells: a wellhead, a site light and a tall beacon of light so each
// well reads from 50 km away. Plus each well's bore below ground.
// ---------------------------------------------------------------------------
function OffsetWell({ well, index, state }: { well: BasinWell; index: number; state: React.MutableRefObject<StoryState> }) {
  const head = useModel(WELLHEAD_URL);
  const glow = glowTexture();
  const beam = useRef<THREE.Mesh>(null);
  const halo = useRef<THREE.Sprite>(null);
  const bore = useRef<THREE.MeshBasicMaterial>(null);
  const y = surfaceY(well.x, well.z);
  const len = (well.td / 1000) * VZ_S;
  useFrame(() => {
    const s = state.current;
    const vis = s.wellVis[well.id] ?? 0;
    const tone = s.wellTone[well.id] ?? 'neutral';
    const c = tone === 'relevant' ? CYAN : tone === 'event' ? AMBER : SLATE;
    const dim = tone === 'dim' ? 0.15 : 1;
    if (beam.current) {
      const m = beam.current.material as THREE.MeshBasicMaterial;
      m.opacity = vis * dim * s.beams * (tone === 'relevant' ? 0.55 : 0.28);
      m.color.copy(c);
      beam.current.scale.y = 0.4 + 0.6 * vis;
    }
    if (halo.current) {
      const m = halo.current.material as THREE.SpriteMaterial;
      m.opacity = vis * dim * (0.4 + 0.5 * s.night);
      m.color.copy(c);
      halo.current.scale.setScalar(0.35 + (tone === 'relevant' ? 0.3 : 0) + Math.sin(s.time * 2 + index) * 0.02);
    }
    if (bore.current) {
      bore.current.opacity = vis * dim * s.bores;
      bore.current.color.copy(c);
    }
  });
  return (
    <group>
      <group position={[well.x, y, well.z]}>
        <primitive object={head} scale={0.001} />
        <sprite ref={halo} position={[0, 0.02, 0]}>
          <spriteMaterial map={glow} transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} />
        </sprite>
        {/* Beacon: a thin vertical shaft of light */}
        <mesh ref={beam} position={[0, 1.5, 0]}>
          <cylinderGeometry args={[0.03, 0.12, 3, 10, 1, true]} />
          <meshBasicMaterial transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} side={THREE.DoubleSide} toneMapped={false} />
        </mesh>
      </group>
      <mesh position={[well.x, y - len / 2, well.z]}>
        <cylinderGeometry args={[0.05, 0.05, len, 8]} />
        <meshBasicMaterial ref={bore} transparent opacity={0} depthWrite={false} toneMapped={false} />
      </mesh>
    </group>
  );
}

export function Wells({ state }: { state: React.MutableRefObject<StoryState> }) {
  const wells = useMemo(() => basinWells(), []);
  const active = wells.find((w) => w.id === getBasin().meta.active)!;
  const activeBore = useRef<THREE.MeshBasicMaterial>(null);
  const beam = useRef<THREE.MeshBasicMaterial>(null);
  const len = (active.td / 1000) * VZ_S;
  const beamMesh = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const s = state.current;
    if (activeBore.current) activeBore.current.opacity = s.bores;
    if (beam.current) beam.current.opacity = s.beams * 0.6;
    // The beacon is a map marker: only exists while the map overlays are on.
    if (beamMesh.current) beamMesh.current.visible = s.beams > 0.01;
  });
  return (
    <group>
      {/* The real land rig, assembled in metres, placed on the ground. */}
      <group position={[active.x, surfaceY(active.x, active.z), active.z]} scale={0.001} rotation-y={0.5}>
        <LandRig state={state} />
      </group>
      <AlertRings x={active.x} y={surfaceY(active.x, active.z) + 0.002} z={active.z} state={state} />
      <mesh ref={beamMesh} position={[active.x, surfaceY(active.x, active.z) + 1.5, active.z]}>
        <cylinderGeometry args={[0.035, 0.14, 3, 10, 1, true]} />
        <meshBasicMaterial ref={beam} color={AMBER} transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      <mesh position={[active.x, surfaceY(active.x, active.z) - len / 2, active.z]}>
        <cylinderGeometry args={[0.06, 0.06, len, 8]} />
        <meshBasicMaterial ref={activeBore} color={AMBER} transparent opacity={0} depthWrite={false} toneMapped={false} />
      </mesh>
      {wells
        .filter((w) => w.id !== active.id)
        .map((w, i) => (
          <OffsetWell key={w.id} well={w} index={i} state={state} />
        ))}
    </group>
  );
}

// ---------------------------------------------------------------------------
// Subsurface: Barail and Kopili horizons from the wells' real tops.
// ---------------------------------------------------------------------------
// The subsurface block: the region around the three correlated wells
// (NHK-003, NHK-002, BGJ-007). Cameras stay outside it, so they look at
// the horizons rather than through them.
const BLOCK = { x0: -4, x1: 18, z0: -30, z1: 16 };

/** Alpha map that fades a sheet out toward its edges. */
let edgeFade: THREE.Texture | null = null;
function edgeFadeTexture() {
  if (edgeFade) return edgeFade;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const img = g.createImageData(128, 128);
  for (let y = 0; y < 128; y++)
    for (let x = 0; x < 128; x++) {
      const e = Math.min(x, y, 127 - x, 127 - y) / 22;
      const v = Math.round(255 * Math.min(1, e * e * (3 - 2 * Math.min(1, e))));
      const i = (y * 128 + x) * 4;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
  g.putImageData(img, 0, 0);
  edgeFade = new THREE.CanvasTexture(c);
  return edgeFade;
}

function horizonGeometry(key: 'barail' | 'kopili', seg = 90) {
  const w = BLOCK.x1 - BLOCK.x0;
  const d = BLOCK.z1 - BLOCK.z0;
  const g = new THREE.PlaneGeometry(w, d, seg, Math.round((seg * d) / w));
  g.rotateX(-Math.PI / 2);
  g.translate((BLOCK.x0 + BLOCK.x1) / 2, 0, (BLOCK.z0 + BLOCK.z1) / 2);
  const pos = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    pos.setY(i, depthY(x, z, horizonDepth(x, z, key)));
  }
  g.computeVertexNormals();
  return g;
}

export function Subsurface({ state }: { state: React.MutableRefObject<StoryState> }) {
  const kopili = useMemo(() => horizonGeometry('kopili'), []);
  const barail = useMemo(() => horizonGeometry('barail'), []);
  const kMat = useRef<THREE.MeshStandardMaterial>(null);
  const bMat = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(() => {
    const s = state.current;
    if (kMat.current) {
      kMat.current.opacity = s.horizon * 0.75;
      kMat.current.emissiveIntensity = 0.2 + 0.4 * s.horizonGlow;
    }
    if (bMat.current) bMat.current.opacity = s.horizon * 0.22;
  });
  return (
    <group>
      <mesh geometry={barail}>
        <meshStandardMaterial ref={bMat} color="#6b6455" roughness={0.9} transparent opacity={0} depthWrite={false} side={THREE.DoubleSide} alphaMap={edgeFadeTexture()} />
      </mesh>
      <mesh geometry={kopili}>
        <meshStandardMaterial ref={kMat} color="#8a4a26" emissive="#c2551e" emissiveIntensity={0.3} roughness={0.85} transparent opacity={0} depthWrite={false} side={THREE.DoubleSide} alphaMap={edgeFadeTexture()} />
      </mesh>
    </group>
  );
}

/**
 * Correlation section ("fence diagram") along NHK-003 → NHK-002 → BGJ-007,
 * coloured by formation, each top interpolated from the wells' real tops.
 */
export function Fence({ state }: { state: React.MutableRefObject<StoryState> }) {
  const { geo, mat } = useMemo(() => {
    const ws = basinWells();
    const byId = Object.fromEntries(ws.map((w) => [w.id, w]));
    const path = ['NHK-003', 'NHK-002', 'BGJ-007'].map((id) => [byId[id].x, byId[id].z] as [number, number]);
    const pts: [number, number][] = [];
    for (let i = 0; i < path.length - 1; i++) {
      const [a, b] = [path[i], path[i + 1]];
      for (let k = 0; k < 80; k++) pts.push([a[0] + ((b[0] - a[0]) * k) / 80, a[1] + ((b[1] - a[1]) * k) / 80]);
    }
    pts.push(path[path.length - 1]);
    const BASE_M = 3400;
    const pos: number[] = [];
    const tops: number[] = [];
    const md: number[] = [];
    const idx: number[] = [];
    pts.forEach(([x, z], i) => {
      pos.push(x, surfaceY(x, z), z, x, depthY(x, z, BASE_M), z);
      const t = [horizonDepth(x, z, 'barail'), horizonDepth(x, z, 'kopili'), horizonDepth(x, z, 'kopiliBase')];
      tops.push(...t, ...t);
      md.push(0, BASE_M);
      if (i > 0) {
        const a = (i - 1) * 2;
        idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('tops', new THREE.Float32BufferAttribute(tops, 3));
    g.setAttribute('md', new THREE.Float32BufferAttribute(md, 1));
    g.setIndex(idx);
    const m = new THREE.ShaderMaterial({
      side: THREE.DoubleSide,
      transparent: true,
      depthWrite: false,
      uniforms: { uOpacity: { value: 0 }, uGlow: { value: 0 } },
      vertexShader: /* glsl */ `
        attribute vec3 tops;
        attribute float md;
        varying vec3 vTops;
        varying float vMd;
        varying vec3 vW;
        void main() {
          vTops = tops; vMd = md;
          vW = (modelMatrix * vec4(position, 1.0)).xyz;
          gl_Position = projectionMatrix * viewMatrix * vec4(vW, 1.0);
        }`,
      fragmentShader: /* glsl */ `
        uniform float uOpacity;
        uniform float uGlow;
        varying vec3 vTops;
        varying float vMd;
        varying vec3 vW;
        float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453); }
        void main() {
          float md = vMd;
          vec3 c; float kop = 0.0;
          if (md < 390.0) c = vec3(0.34,0.29,0.21);
          else if (md < 1169.0) c = vec3(0.47,0.39,0.26);
          else if (md < 1451.0) c = vec3(0.36,0.27,0.23);
          else if (md < vTops.x) c = vec3(0.40,0.37,0.30);
          else if (md < vTops.y) c = vec3(0.16,0.14,0.13);
          else if (md < vTops.z) { c = vec3(0.60,0.30,0.15); kop = 1.0; }
          else c = vec3(0.48,0.47,0.42);
          float bed = smoothstep(0.9, 1.0, abs(sin(md * 0.11 + hash(floor(vW.xz * 2.0)) * 0.6)));
          c *= 0.84 + 0.16 * hash(floor(vec2(vW.x + vW.z, md / 6.0)));
          c *= 1.0 - bed * 0.3;
          float edge = min(min(abs(md - vTops.x), abs(md - vTops.y)), abs(md - vTops.z));
          c = mix(vec3(0.9, 0.85, 0.75), c, smoothstep(0.0, 9.0, edge));
          c += vec3(0.9, 0.35, 0.1) * kop * uGlow * 0.35;
          gl_FragColor = vec4(c, uOpacity);
          #include <colorspace_fragment>
        }`,
    });
    return { geo: g, mat: m };
  }, []);
  useFrame(() => {
    const s = state.current;
    mat.uniforms.uOpacity.value = s.horizon * 0.92;
    mat.uniforms.uGlow.value = s.horizonGlow;
  });
  return <mesh geometry={geo} material={mat} renderOrder={2} />;
}

/** Red lights at each analog well's kick depth. */
export function Events({ state }: { state: React.MutableRefObject<StoryState> }) {
  const tex = glowTexture();
  const points = useMemo(() => {
    const ws = basinWells();
    return [
      { id: 'NHK-003', md: 2663.9 },
      { id: 'BGJ-007', md: 2905.3 },
    ].map((e) => {
      const w = ws.find((x) => x.id === e.id)!;
      return new THREE.Vector3(w.x, depthY(w.x, w.z, e.md), w.z);
    });
  }, []);
  const refs = useRef<(THREE.Sprite | null)[]>([]);
  useFrame(() => {
    const s = state.current;
    refs.current.forEach((r) => {
      if (!r) return;
      r.scale.setScalar(1.3 + Math.sin(s.time * 4) * 0.2);
      (r.material as THREE.SpriteMaterial).opacity = s.events;
    });
  });
  return (
    <group>
      {points.map((p, i) => (
        <sprite key={i} ref={(r) => (refs.current[i] = r)} position={p}>
          <spriteMaterial map={tex} color={RED} transparent opacity={0} depthWrite={false} depthTest={false} blending={THREE.AdditiveBlending} toneMapped={false} />
        </sprite>
      ))}
    </group>
  );
}

/** The active well's bit and the ahead-of-bit risk column below it. */
export function AheadColumn({ state, risk }: { state: React.MutableRefObject<StoryState>; risk: { md: number; kick: number; op: number }[] }) {
  const group = useRef<THREE.Group>(null);
  const segs = useRef<(THREE.MeshBasicMaterial | null)[]>([]);
  const bit = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const s = state.current;
    if (group.current) group.current.visible = s.ahead > 0.001 || s.bit > 0.001;
    segs.current.forEach((m, i) => {
      if (!m) return;
      const r = risk[i];
      const v = Math.max(r.kick, r.op);
      const reveal = Math.min(1, Math.max(0, s.ahead * risk.length - i));
      m.opacity = reveal * (0.25 + 0.75 * v);
      m.color.setRGB(0.95, 0.65 - 0.45 * (r.kick > r.op ? 1 : 0.3) * v, 0.15 * (1 - v));
    });
    if (bit.current) {
      (bit.current.material as THREE.MeshBasicMaterial).opacity = s.bit;
      bit.current.scale.setScalar(1 + Math.sin(s.time * 5) * 0.15);
    }
  });
  const step = ((risk[1].md - risk[0].md) / 1000) * VZ_S;
  return (
    <group ref={group}>
      <mesh ref={bit} position={[0, depthY(0, 0, 2850), 0]}>
        <sphereGeometry args={[0.2, 16, 16]} />
        <meshBasicMaterial color={AMBER} transparent opacity={0} toneMapped={false} depthTest={false} />
      </mesh>
      {risk.map((r, i) => {
        const v = Math.max(r.kick, r.op);
        return (
          <mesh key={r.md} position={[0, depthY(0, 0, r.md + 10), 0]}>
            <cylinderGeometry args={[0.16 + v * 0.5, 0.16 + v * 0.5, step * 0.92, 24, 1, true]} />
            <meshBasicMaterial ref={(m) => (segs.current[i] = m)} transparent opacity={0} depthWrite={false} side={THREE.DoubleSide} blending={THREE.AdditiveBlending} toneMapped={false} />
          </mesh>
        );
      })}
    </group>
  );
}

// ---------------------------------------------------------------------------
// Shared glow texture
// ---------------------------------------------------------------------------
let glowCache: THREE.Texture | null = null;
export function glowTexture(): THREE.Texture {
  if (glowCache) return glowCache;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.15, 'rgba(255,255,255,0.6)');
  grad.addColorStop(0.45, 'rgba(255,255,255,0.12)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  glowCache = new THREE.CanvasTexture(c);
  glowCache.colorSpace = THREE.SRGBColorSpace;
  return glowCache;
}

useGLTF.preload(WELLHEAD_URL);
