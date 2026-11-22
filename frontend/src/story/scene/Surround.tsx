import React, { useMemo, useRef } from 'react';
import { useFrame, useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { VZ_T, getBasin } from '../terrain';
import type { StoryState } from './state';

// The real horizon around the basin: 445 x 398 km of SRTM-based elevation
// and Sentinel-2 imagery (scripts/fetch-basin.py "wide"), from the Eastern
// Himalaya of Arunachal Pradesh (5-6.6 km peaks, ~100-250 km north) to the
// Naga-Patkai hills (south-east). It sits just under the detailed basin
// mesh, so the basin has no edges: past it, the land simply continues to
// the real mountains. Its edges fade into the sky.

// 320 x 320 cells over 445 x 398 km (~1.3 km per cell, finer than the
// 512-px height map's useful detail once smoothed). ~103k vertices.
const SEG = 320;

async function loadWideHeight(url: string) {
  const img = new Image();
  img.src = url;
  await img.decode();
  const c = document.createElement('canvas');
  c.width = img.width;
  c.height = img.height;
  const g = c.getContext('2d', { willReadFrequently: true })!;
  g.drawImage(img, 0, 0);
  const px = g.getImageData(0, 0, c.width, c.height).data;
  const W = c.width;
  const H = c.height;
  const raw = new Float32Array(W * H);
  for (let i = 0; i < raw.length; i++) raw[i] = (px[i * 4] * 256 + px[i * 4 + 1]) / 65535;
  // Light separable [1 2 1] blur, once: removes single-pixel spikes so the
  // ranges don't break up into steps, without flattening the ridgelines.
  const tmp = new Float32Array(W * H);
  const out = new Float32Array(W * H);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      tmp[i] = (raw[y * W + Math.max(0, x - 1)] + 2 * raw[i] + raw[y * W + Math.min(W - 1, x + 1)]) / 4;
    }
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      out[i] = (tmp[Math.max(0, y - 1) * W + x] + 2 * tmp[i] + tmp[Math.min(H - 1, y + 1) * W + x]) / 4;
    }
  return { data: out, w: W, h: H };
}

let wide: { data: Float32Array; w: number; h: number } | null = null;
let widePromise: Promise<void> | null = null;

export function SurroundGate({ children }: { children: React.ReactNode }) {
  if (!wide) {
    widePromise ??= loadWideHeight('/story/wide-height.png').then((r) => {
      wide = r;
    });
    throw widePromise;
  }
  return <>{children}</>;
}

export function Surround({ state }: { state: React.MutableRefObject<StoryState> }) {
  const sat = useLoader(THREE.TextureLoader, '/story/wide-sat.jpg');
  const { geo, mat } = useMemo(() => {
    const b = getBasin();
    const W = b.meta as unknown as { wide: { width_km: number; height_km: number; u: number; v: number; elev_max_m: number } };
    const m = W.wide;
    const x0 = -m.u * m.width_km;
    const z0 = -m.v * m.height_km;
    const g = new THREE.PlaneGeometry(m.width_km, m.height_km, SEG, SEG);
    g.rotateX(-Math.PI / 2);
    g.translate(x0 + m.width_km / 2, 0, z0 + m.height_km / 2);
    const pos = g.attributes.position as THREE.BufferAttribute;
    const h = wide!;
    // Inside the detailed basin, sink the surround well below it so the
    // two never z-fight; feather back up over the last few km.
    const bx0 = b.x0;
    const bz0 = b.z0;
    const bx1 = b.x0 + b.meta.width_km;
    const bz1 = b.z0 + b.meta.height_km;
    // Height: bilinear over a once-smoothed grid (h is blurred in
    // loadWideHeight). Nearest-pixel sampling at this mesh spacing made the
    // ranges stair-stepped and spiky ("breaking" up close); this keeps the
    // real ridgelines but removes the aliasing, at one sample per vertex.
    const sample = (u: number, v: number) => {
      const fx = Math.min(h.w - 1.001, Math.max(0, u * (h.w - 1)));
      const fy = Math.min(h.h - 1.001, Math.max(0, v * (h.h - 1)));
      const ix = Math.floor(fx);
      const iy = Math.floor(fy);
      const tx = fx - ix;
      const ty = fy - iy;
      const d = h.data;
      const i0 = iy * h.w + ix;
      return (d[i0] * (1 - tx) + d[i0 + 1] * tx) * (1 - ty) + (d[i0 + h.w] * (1 - tx) + d[i0 + h.w + 1] * tx) * ty;
    };
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const u = (x - x0) / m.width_km;
      const v = (z - z0) / m.height_km;
      let y = ((sample(u, v) * m.elev_max_m) / 1000) * VZ_T;
      const inside = Math.min(x - bx0, bx1 - x, z - bz0, bz1 - z);
      // Inside the detailed basin, sink well below it (no z-fighting). The
      // old 0.25-unit drop was too shallow over the 3x-exaggerated foothills
      // at the basin's south-east edge, which is where the two surfaces
      // crossed and flickered.
      if (inside > 0) y -= Math.min(1, inside / 3) * 0.9;
      pos.setY(i, y);
    }
    g.computeVertexNormals();
    sat.colorSpace = THREE.SRGBColorSpace;
    sat.anisotropy = 8;
    const mat = new THREE.MeshStandardMaterial({ map: sat, roughness: 0.95 });
    mat.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vW;\nvarying vec3 vWN;')
        .replace(
          '#include <worldpos_vertex>',
          '#include <worldpos_vertex>\nvW = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvWN = normalize(mat3(modelMatrix) * objectNormal);',
        );
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vW;\nvarying vec3 vWN;')
        .replace(
          '#include <map_fragment>',
          `vec4 texel = texture2D(map, vMapUv);
         texel.rgb = pow(texel.rgb, vec3(0.78)) * 1.6;
         float l = dot(texel.rgb, vec3(0.299, 0.587, 0.114));
         texel.rgb = mix(vec3(l), texel.rgb, 1.15);
         // Relief: steep slopes a little darker (soil and shadowed forest),
         // so ridgelines read from far away.
         float steep = 1.0 - clamp(vWN.y, 0.0, 1.0);
         texel.rgb *= mix(1.0, 0.78, smoothstep(0.08, 0.45, steep));
         // Real snow line of the Eastern Himalaya (~4,600 m): above it,
         // gentle slopes hold snow, steep faces stay rock.
         float elevM = vW.y / ${VZ_T.toFixed(1)} * 1000.0;
         float snow = smoothstep(4300.0, 5200.0, elevM) * (1.0 - smoothstep(0.35, 0.7, steep));
         texel.rgb = mix(texel.rgb, vec3(0.86, 0.9, 0.95), snow * 0.85);
         // Mid-mountain ridges (Patkai, 1.5-2.5 km): a faint cool haze lift.
         texel.rgb = mix(texel.rgb, vec3(0.62, 0.7, 0.78), smoothstep(1200.0, 2600.0, elevM) * 0.12);
         diffuseColor *= texel;`,
        );
    };
    return { geo: g, mat };
  }, [sat]);
  const ref = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const veil = 1 - 0.96 * state.current.cutaway;
    mat.transparent = veil < 0.999;
    mat.opacity = veil;
  });
  return <mesh ref={ref} geometry={geo} material={mat} receiveShadow />;
}
