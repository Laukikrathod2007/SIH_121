import * as THREE from 'three';

// Procedural canvas textures for the film. Generated in the browser at
// load time so the film ships no extra image assets.

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return [c, c.getContext('2d') as CanvasRenderingContext2D];
}

// Deterministic PRNG so every viewing renders the same rock.
export function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const cache = new Map<string, THREE.Texture>();
function cached<T extends THREE.Texture>(key: string, make: () => T): T {
  const hit = cache.get(key);
  if (hit) return hit as T;
  const tex = make();
  cache.set(key, tex);
  return tex;
}

/** Soft round glow, used for light halos, well markers and dust motes. */
export function glowTexture(): THREE.Texture {
  return cached('glow', () => {
    const [c, g] = canvas(128, 128);
    const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, 'rgba(255,255,255,1)');
    grad.addColorStop(0.18, 'rgba(255,255,255,0.55)');
    grad.addColorStop(0.45, 'rgba(255,255,255,0.12)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 128, 128);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  });
}

/** Irregular soft puff for steam. */
export function smokeTexture(): THREE.Texture {
  return cached('smoke', () => {
    const [c, g] = canvas(128, 128);
    const rnd = mulberry32(7);
    for (let i = 0; i < 26; i++) {
      const x = 64 + (rnd() - 0.5) * 50;
      const y = 64 + (rnd() - 0.5) * 50;
      const r = 18 + rnd() * 30;
      const grad = g.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, 'rgba(255,255,255,0.09)');
      grad.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = grad;
      g.fillRect(0, 0, 128, 128);
    }
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  });
}

/** Small tiling grain used as a bump map so rock reads as rock up close. */
export function grainTexture(): THREE.Texture {
  return cached('grain', () => {
    const size = 256;
    const [c, g] = canvas(size, size);
    const img = g.createImageData(size, size);
    const rnd = mulberry32(11);
    for (let i = 0; i < size * size; i++) {
      const v = Math.floor(90 + rnd() * 120);
      img.data[i * 4] = v;
      img.data[i * 4 + 1] = v;
      img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    // A few streaks so it reads as bedding, not static.
    for (let i = 0; i < 40; i++) {
      g.fillStyle = `rgba(0,0,0,${0.08 + rnd() * 0.12})`;
      g.fillRect(0, rnd() * size, size, 1 + rnd() * 2);
    }
    const tex = new THREE.CanvasTexture(c);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    return tex;
  });
}

// ---------------------------------------------------------------------------
// Stratigraphic column for the film's active well. Formation names and
// their order follow the Upper Assam column used in the NWIS dataset;
// the depths are illustrative.
// ---------------------------------------------------------------------------
export interface Stratum {
  name: string;
  top: number; // m MD
  base: number;
  color: string;
  grain: number; // 0 = clay/shale, 1 = coarse sand
}

export const COLUMN_BASE_M = 3200;

export const STRATA: Stratum[] = [
  { name: 'ALLUVIUM', top: 0, base: 420, color: '#3a3125', grain: 0.6 },
  { name: 'DHEKIAJULI', top: 420, base: 980, color: '#4a3c2b', grain: 0.7 },
  { name: 'NAMSANG', top: 980, base: 1180, color: '#5b4731', grain: 0.8 },
  { name: 'GIRUJAN CLAY', top: 1180, base: 1720, color: '#4c3532', grain: 0.15 },
  { name: 'TIPAM SANDSTONE', top: 1720, base: 2180, color: '#6d5b3b', grain: 0.95 },
  { name: 'BARAIL COAL-SHALE', top: 2180, base: 2560, color: '#211d1b', grain: 0.2 },
  { name: 'BARAIL SANDSTONE', top: 2560, base: 2900, color: '#5a5241', grain: 0.85 },
  { name: 'KOPILI', top: 2900, base: 3060, color: '#363130', grain: 0.1 },
  { name: 'SYLHET LIMESTONE', top: 3060, base: 3200, color: '#7a776a', grain: 0.4 },
];

export function formationAt(md: number): Stratum {
  for (const s of STRATA) if (md >= s.top && md < s.base) return s;
  return STRATA[STRATA.length - 1];
}

function shade(hex: string, k: number): string {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.min(255, Math.max(0, Math.round(((n >> 16) & 255) * k)));
  const gg = Math.min(255, Math.max(0, Math.round(((n >> 8) & 255) * k)));
  const b = Math.min(255, Math.max(0, Math.round((n & 255) * k)));
  return `rgb(${r},${gg},${b})`;
}

/**
 * A depth range of the column as one tall texture: canvas top = topMd,
 * bottom = baseMd. Bedding lines, grain and formation names are painted
 * in, so the names read as part of the rock rather than as overlay text.
 * The film uses a coarse texture for the fall through the shallow section
 * and a detailed one around the bit.
 */
export function strataTexture(topMd = 0, baseMd = COLUMN_BASE_M): THREE.Texture {
  return cached(`strata-${topMd}-${baseMd}`, () => {
    const W = 1024;
    const H = 4096;
    const [c, g] = canvas(W, H);
    const rnd = mulberry32(42 + topMd);
    const y = (md: number) => ((md - topMd) / (baseMd - topMd)) * H;
    const pxPerM = H / (baseMd - topMd);

    for (const s of STRATA) {
      if (s.base <= topMd || s.top >= baseMd) continue;
      const y0 = Math.max(0, y(s.top));
      const y1 = Math.min(H, y(s.base));
      g.fillStyle = s.color;
      g.fillRect(0, y0, W, y1 - y0);

      // Thin bedding bands with slight waviness, ~ one per 1-2 m of rock.
      const bands = Math.floor(((y1 - y0) / pxPerM) * (s.grain > 0.5 ? 0.7 : 1.4)) + 4;
      for (let i = 0; i < bands; i++) {
        const by = y0 + rnd() * (y1 - y0);
        const k = 0.75 + rnd() * 0.5;
        g.strokeStyle = shade(s.color, k);
        g.globalAlpha = 0.35 + rnd() * 0.4;
        g.lineWidth = 0.6 + rnd() * (s.grain > 0.5 ? 2.5 : 1.2);
        g.beginPath();
        const amp = 1 + rnd() * 3;
        const freq = 0.004 + rnd() * 0.01;
        const ph = rnd() * 10;
        for (let x = 0; x <= W; x += 16) {
          const yy = by + Math.sin(x * freq + ph) * amp;
          if (x === 0) g.moveTo(x, yy);
          else g.lineTo(x, yy);
        }
        g.stroke();
      }
      g.globalAlpha = 1;

      // Grains / nodules.
      const dots = Math.floor(((y1 - y0) * W) / (s.grain > 0.5 ? 260 : 900));
      for (let i = 0; i < dots; i++) {
        g.fillStyle = shade(s.color, 0.55 + rnd() * 0.9);
        g.globalAlpha = 0.25 + rnd() * 0.4;
        const r = s.grain > 0.5 ? 0.6 + rnd() * 1.8 : 0.4 + rnd() * 0.9;
        g.fillRect(rnd() * W, y0 + rnd() * (y1 - y0), r, r);
      }
      g.globalAlpha = 1;

      // Coal stringers in the coal-shale.
      if (s.name.includes('COAL')) {
        for (let i = 0; i < 16; i++) {
          g.fillStyle = 'rgba(5,5,6,0.85)';
          g.fillRect(0, y0 + rnd() * (y1 - y0), W, 1 + rnd() * 3);
        }
      }

      if (s.top >= topMd) {
        // Sharp, slightly darker contact at the top of each formation.
        g.fillStyle = 'rgba(0,0,0,0.55)';
        g.fillRect(0, y0, W, Math.max(2, pxPerM * 0.3));

        // Etched name, repeated around the circumference.
        const fs = Math.round(Math.min(40, Math.max(13, pxPerM * 3)));
        g.font = `600 ${fs}px "JetBrains Mono", monospace`;
        g.fillStyle = 'rgba(235,225,205,0.12)';
        for (let x = 30; x < W; x += 512) g.fillText(s.name, x, y0 + fs * 1.5);
      }
    }

    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = THREE.RepeatWrapping;
    tex.anisotropy = 8;
    return tex;
  });
}

/** Dark topographic contour map for the offset-wells shot. */
export function contourTexture(): THREE.Texture {
  return cached('contour', () => {
    const S = 1024;
    const [c, g] = canvas(S, S);
    const img = g.createImageData(S, S);
    for (let j = 0; j < S; j++) {
      for (let i = 0; i < S; i++) {
        const x = i / S;
        const y = j / S;
        const f =
          Math.sin(x * 9.1 + Math.sin(y * 4.3) * 1.4) * 0.5 +
          Math.sin(y * 7.7 + Math.cos(x * 5.1) * 1.2) * 0.4 +
          Math.sin((x + y) * 15.3) * 0.12;
        const band = Math.abs(((f * 6) % 1 + 1) % 1 - 0.5);
        const line = band > 0.47 ? 1 : 0;
        const idx = (j * S + i) * 4;
        const base = 9 + f * 3;
        img.data[idx] = base + line * 30;
        img.data[idx + 1] = base + 3 + line * 62;
        img.data[idx + 2] = base + 7 + line * 72;
        img.data[idx + 3] = 255;
      }
    }
    g.putImageData(img, 0, 0);
    // Fade to the scene's background toward the edges, so the map has no
    // visible border: it dissolves into the dark.
    const fade = g.createRadialGradient(S / 2, S / 2, S * 0.18, S / 2, S / 2, S * 0.5);
    fade.addColorStop(0, 'rgba(2,4,7,0)');
    fade.addColorStop(1, 'rgba(2,4,7,1)');
    g.fillStyle = fade;
    g.fillRect(0, 0, S, S);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return tex;
  });
}

/** Vertical fade for the correlation sheet (opaque centre, clear edges). */
export function sheetTexture(): THREE.Texture {
  return cached('sheet', () => {
    const [c, g] = canvas(256, 256);
    const grad = g.createRadialGradient(128, 128, 10, 128, 128, 128);
    grad.addColorStop(0, 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.6, 'rgba(255,255,255,0.35)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 256);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  });
}
