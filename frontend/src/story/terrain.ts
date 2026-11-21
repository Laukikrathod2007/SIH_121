// The Upper Assam basin from real data (scripts/fetch-basin.py):
//   public/story/basin-height.png  AWS Terrain Tiles elevation (SRTM-based)
//   public/story/basin-sat.jpg     Sentinel-2 cloudless 2016 imagery (EOX, CC BY 4.0)
//   public/story/basin.json        bounds, elevation range, well positions
//
// Scene units are kilometres: x = east, y = up, z = -north, with the
// active well NHK-002 at the origin. Elevation is exaggerated VZ_T times
// so the low relief of the valley reads; depth below ground is drawn VZ_S
// times so 3 km of rock fits under a ~120 km wide basin.

export const VZ_T = 3;
export const VZ_S = 3;

export interface BasinMeta {
  width_km: number;
  height_km: number;
  detail_km: number;
  elev_min_m: number;
  elev_max_m: number;
  active: string;
  wells: Record<string, { u: number; v: number; lat: number; lon: number }>;
  credits: { imagery: string; elevation: string };
}

export interface Basin {
  meta: BasinMeta;
  /** Elevation grid, metres, row-major, (gw x gh). */
  elev: Float32Array;
  gw: number;
  gh: number;
  /** World x/z of the image's left/top edge (km). */
  x0: number;
  z0: number;
}

let basin: Basin | null = null;

async function loadImage(url: string): Promise<HTMLImageElement> {
  const img = new Image();
  img.decoding = 'async';
  img.src = url;
  await img.decode();
  return img;
}

/** Load and decode the basin assets once. */
export async function loadBasin(): Promise<Basin> {
  if (basin) return basin;
  const [meta, hImg] = await Promise.all([
    fetch('/story/basin.json').then((r) => r.json() as Promise<BasinMeta>),
    loadImage('/story/basin-height.png'),
  ]);
  // 16-bit elevation packed as R = high byte, G = low byte (see the build
  // script), so canvas's 8-bit decode loses nothing.
  const c = document.createElement('canvas');
  c.width = hImg.width;
  c.height = hImg.height;
  const g = c.getContext('2d', { willReadFrequently: true })!;
  g.drawImage(hImg, 0, 0);
  const px = g.getImageData(0, 0, c.width, c.height).data;
  const elev = new Float32Array(c.width * c.height);
  const range = meta.elev_max_m - meta.elev_min_m;
  for (let i = 0; i < elev.length; i++) elev[i] = meta.elev_min_m + ((px[i * 4] * 256 + px[i * 4 + 1]) / 65535) * range;
  const a = meta.wells[meta.active];
  basin = {
    meta,
    elev,
    gw: c.width,
    gh: c.height,
    x0: -a.u * meta.width_km,
    z0: -a.v * meta.height_km,
  };
  return basin;
}

export function getBasin(): Basin {
  if (!basin) throw new Error('basin not loaded');
  return basin;
}

/** Elevation in metres at world (x, z) km, bilinear. */
export function elevationM(x: number, z: number): number {
  const b = getBasin();
  const u = ((x - b.x0) / b.meta.width_km) * (b.gw - 1);
  const v = ((z - b.z0) / b.meta.height_km) * (b.gh - 1);
  const ix = Math.max(0, Math.min(b.gw - 2, Math.floor(u)));
  const iy = Math.max(0, Math.min(b.gh - 2, Math.floor(v)));
  const fx = Math.min(1, Math.max(0, u - ix));
  const fy = Math.min(1, Math.max(0, v - iy));
  const e = b.elev;
  const i = iy * b.gw + ix;
  return (e[i] * (1 - fx) + e[i + 1] * fx) * (1 - fy) + (e[i + b.gw] * (1 - fx) + e[i + b.gw + 1] * fx) * fy;
}

/** Scene height (units) of the ground at world (x, z). */
export function surfaceY(x: number, z: number): number {
  return (elevationM(x, z) / 1000) * VZ_T;
}

// ---------------------------------------------------------------------------
// Wells and formation tops (NWIS backend, demo dataset)
// ---------------------------------------------------------------------------
export interface BasinWell {
  id: string;
  x: number;
  z: number;
  td: number; // total depth, m MD
}

const TD: Record<string, number> = {
  'NHK-001': 2820, 'NHK-002': 3244, 'NHK-003': 3461, 'MRN-004': 3108, 'MRN-005': 3490, 'MRN-006': 2949,
  'BGJ-007': 3064, 'BGJ-008': 3296, 'BGJ-009': 3160, 'HGJ-010': 2882, 'HGJ-011': 2843, 'HGJ-012': 2838,
};

export function basinWells(): BasinWell[] {
  const b = getBasin();
  return Object.entries(b.meta.wells).map(([id, w]) => ({
    id,
    x: b.x0 + w.u * b.meta.width_km,
    z: b.z0 + w.v * b.meta.height_km,
    td: TD[id] ?? 3000,
  }));
}

/** Formation tops (m MD) from /api/v2/formations for the wells that have them. */
export const TOPS: Record<string, { barail: number; kopili: number; kopiliBase: number }> = {
  'NHK-002': { barail: 2135, kopili: 2674, kopiliBase: 3128 },
  'NHK-003': { barail: 2125, kopili: 2597, kopiliBase: 3044 },
  'BGJ-007': { barail: 2263, kopili: 2767, kopiliBase: 3064 },
  'NHK-001': { barail: 2259, kopili: 2573, kopiliBase: 2820 },
};

/** Inverse-distance-weighted depth (m) of a horizon at world (x, z). */
export function horizonDepth(x: number, z: number, key: 'barail' | 'kopili' | 'kopiliBase'): number {
  let ws = 0;
  let vs = 0;
  for (const w of basinWells()) {
    const t = TOPS[w.id];
    if (!t) continue;
    const wt = 1 / ((x - w.x) ** 2 + (z - w.z) ** 2 + 4);
    ws += wt;
    vs += wt * t[key];
  }
  return vs / ws;
}

/** Scene y of a point mdM metres below the ground at (x, z). */
export function depthY(x: number, z: number, mdM: number): number {
  return surfaceY(x, z) - (mdM / 1000) * VZ_S;
}
