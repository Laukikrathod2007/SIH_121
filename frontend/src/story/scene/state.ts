import * as THREE from 'three';
import { PHASES } from '../phases';
import { basinWells } from '../terrain';

// The story's scene state: one plain object recomputed every frame from
// the story clock. Each phase sets targets for the camera and the scene
// layers; the camera eases between phases, so the world never cuts.
//
// World units are km (x = east, z = south, y = up; terrain height x3).
// The active well NHK-002 sits at the origin, on ground ~0.35 units up.

export type Tone = 'active' | 'relevant' | 'neutral' | 'dim' | 'event';

export interface StoryState {
  time: number;
  night: number;
  contours: number;
  radiusKm: number;
  radiusOn: number;
  mapDim: number;
  cutaway: number;
  horizon: number;
  horizonGlow: number;
  bores: number;
  beams: number;
  events: number;
  ahead: number;
  bit: number;
  paper: number;
  paperOrder: number;
  wellVis: Record<string, number>;
  wellTone: Record<string, Tone>;
  camPos: THREE.Vector3;
  camLook: THREE.Vector3;
  fov: number;
  /** Which world is rendered: the basin, or the inside of the borehole. */
  world: 'surface' | 'hole';
  holeMd: number;
  holeLook: number;
  holeFov: number;
  /** Fade-to-black between the two worlds (0 = clear). */
  dip: number;
  /** Decide: amber alert rings pulsing out from the rig (0..1). */
  alert: number;
  /** Globe opening: 1 = only the Earth is drawn, 0 = only the basin. */
  globe: number;
  /** Progress of the fall toward the Earth (0..1), driving the globe camera. */
  globeT: number;
  /** White-haze flash that hides the globe -> basin handover (0..1). */
  flash: number;
}

export function createState(): StoryState {
  return {
    time: 0,
    night: 0.5,
    contours: 0,
    radiusKm: 0,
    radiusOn: 0,
    mapDim: 0,
    cutaway: 0,
    horizon: 0,
    horizonGlow: 0,
    bores: 0,
    beams: 0,
    events: 0,
    ahead: 0,
    bit: 0,
    paper: 0,
    paperOrder: 0,
    wellVis: {},
    wellTone: {},
    camPos: new THREE.Vector3(-0.9, 0.42, 0.75),
    camLook: new THREE.Vector3(0, 0.38, 0),
    fov: 32,
    world: 'surface',
    holeMd: 0,
    holeLook: 30,
    holeFov: 70,
    dip: 0,
    alert: 0,
    globe: 0,
    globeT: 0,
    flash: 0,
  };
}

const clamp = (x: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));
const ease = (x: number) => {
  const t = clamp(x);
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};
const seg = (p: number, a: number, b: number) => ease((p - a) / (b - a));
const smoothstep = (a: number, b: number, x: number) => {
  const t = clamp((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

/** Where the extract-phase camera sits; Reports lays its page grid facing it. */
export const EXTRACT_EYE = new THREE.Vector3(-13, 7, -13.5);
/** Where it looks: the Naga-Patkai front, ~40 km to the south-east. */
export const EXTRACT_LOOK = new THREE.Vector3(15, 2.3, 14);
/** Centre of the ordered report grid: 9 km down the view line, a little up. */
export const GRID_CENTRE = EXTRACT_EYE.clone()
  .add(EXTRACT_LOOK.clone().sub(EXTRACT_EYE).normalize().multiplyScalar(9))
  .add(new THREE.Vector3(0, 0.5, 0));

/** Camera per phase: [from, to, look-from, look-to, fov-from, fov-to]. */
type Cam = [THREE.Vector3, THREE.Vector3, THREE.Vector3, THREE.Vector3, number, number];
const CAMS: Record<string, Cam> = {
  // Powers-of-ten: from 30 km up over the foothills, a long fall straight
  // toward the rig until the derrick fills the frame (positions in km;
  // the rig is ~50 m tall at the origin, ground at y≈0.354). The path
  // itself is eased in updateState (fast at height, slow at the end).
  // Ends ~55 m from the derrick, just above floor height, the mast
  // filling the frame (fov 26 ≈ a 70 mm lens).
  well: [v(18, 30, 22), v(-0.042, 0.372, 0.036), v(0, 0.36, 0), v(0, 0.381, 0), 40, 26],
  // Pull up and back to the north-west, turning to face the real
  // Naga-Patkai range (bearing 120-150°, ~2 km high at 35-55 km): the rig
  // becomes one point on the plain below a wall of mountains.
  buried: [v(-0.042, 0.372, 0.036), EXTRACT_EYE.clone(), v(0, 0.381, 0), EXTRACT_LOOK.clone(), 26, 38],
  // Hold, drifting slowly, while the reports order themselves against the range.
  extract: [EXTRACT_EYE.clone(), v(-12.6, 6.8, -13.1), EXTRACT_LOOK.clone(), v(15.6, 2.4, 14.6), 38, 37],
  // High oblique from the south over the hills: the whole field.
  nearby: [v(10, 30, 70), v(-6, 34, 64), v(-10, 0, -6), v(-12, 0, -8), 42, 44],
  // Settle lower as the ranking lights the relevant wells.
  relevant: [v(-6, 34, 64), v(4, 14, 42), v(-12, 0, -8), v(4, 0, -6), 44, 38],
  // Under the ground, from outside the subsurface block: the Kopili and
  // the correlation section in view, slightly from above. Starts exactly
  // where "relevant" ends, so the move is one continuous glide; the
  // descent through the surface is shaped in updateState.
  correlate: [v(4, 14, 42), v(-24, -3, 20), v(4, 0, -6), v(7, -8, -5), 38, 36],
  // Starts beside the derrick looking at the drill floor (then cuts into the hole).
  ahead: [v(-0.06, 0.375, 0.05), v(-0.05, 0.372, 0.04), v(0, 0.364, 0), v(0, 0.362, 0), 40, 40],
  // The outcome, a shot of its own: back on the surface beside the rig
  // (alert lights on), a slow crane up and out over the well site, then
  // a long rise toward the Patkai ridges as the confidence panel builds.
  // Path shaped in updateState; these are the start/end anchors.
  decide: [v(-0.11, 0.39, 0.09), v(-9, 5.5, -10), v(0, 0.382, 0), v(22, 3.5, 22), 34, 36],
};

const RELEVANT = new Set(['NHK-003', 'BGJ-007']);
let WELLS: { id: string; d: number }[] | null = null;

export function updateState(s: StoryState, t: number, index: number, p: number) {
  const id = PHASES[index].id;
  s.time = t;
  if (!WELLS) WELLS = basinWells().map((w) => ({ id: w.id, d: Math.hypot(w.x, w.z) }));

  const c = CAMS[id];
  let cp = ease(p);
  s.globe = 0;
  s.flash = 0;
  if (id === 'well') {
    // 13 s opening, in one continuous fall:
    //   0.0-0.6 s  black, then the Earth fades up out of space
    //   0.6-6.2 s  the globe turns to Assam; the camera falls toward it
    //   5.6-6.6 s  the atmosphere fills the frame; a brief white-haze
    //              flash hides the handover to the real basin terrain
    //   6.2-13 s   the basin: 30 km up, the powers-of-ten fall to the rig
    const T = p * 13;
    s.globeT = smoothstep(0.4, 6.2, T) ** 0.9;
    s.globe = T < 6.2 ? 1 : 0;
    s.flash = smoothstep(5.5, 6.2, T) * (1 - smoothstep(6.2, 7.0, T));
    s.dip = 1 - smoothstep(0.1, 0.9, T);
    // Basin fall, as before, over the remaining 6.8 s (from 30 km up,
    // distance shrinking geometrically: 30 km → 3 km → 300 m → 60 m).
    const q = clamp((T - 6.2) / 6.8);
    cp = 1 - Math.pow(1 - q, 3.2);
  }
  if (id === 'correlate') {
    // One slow, even glide (no fast middle): gentle in and out, so the
    // land has time to dissolve while the camera sinks under it.
    cp = smoothstep(0, 1, clamp(p / 0.85));
  }
  s.camPos.copy(c[0]).lerp(c[1], cp);
  if (id === 'correlate') {
    // Arc, not a straight line: swing out to the west on the way down,
    // so the block turns into view instead of the camera diving at it.
    s.camPos.x -= Math.sin(cp * Math.PI) * 6;
  }
  s.camLook.copy(c[2]).lerp(c[3], cp);
  s.fov = lerp(c[4], c[5], cp);

  // ---- the borehole ("ahead"): dip to black from the rig, fall down the
  // hole through every formation, slow into the Kopili, settle on the bit.
  if (id === 'ahead') {
    s.world = p < 0.06 ? 'surface' : 'hole';
    s.dip = p < 0.06 ? seg(p, 0, 0.06) : 1 - seg(p, 0.06, 0.14);
    const fall = clamp((p - 0.06) / 0.86);
    // ease-out cubic: fast through the shallow section, slowing at depth
    const q = 1 - Math.pow(1 - fall, 3);
    // Stops ~8 m above the top of the bottom-hole assembly (bit at
    // 2,850 m, BHA ~15 m long), looking down along it to the bit.
    s.holeMd = lerp(30, 2833, q);
    s.holeLook = lerp(60, 17, smoothstep(0.55, 1, fall));
    s.holeFov = lerp(72, 56, smoothstep(0.4, 1, fall));
  } else if (id === 'decide') {
    // Out of the hole under a short dip, then a real shot for the whole
    // phase (not a static frame): the camera holds on the rig for a beat,
    // cranes up over the site, and rises out over the basin.
    s.world = p < 0.06 ? 'hole' : 'surface';
    s.dip = p < 0.06 ? seg(p, 0, 0.06) : 1 - seg(p, 0.06, 0.16);
    s.holeMd = 2833;
    s.holeLook = 17;
    s.holeFov = 58;
    const q = clamp((p - 0.08) / 0.92);
    // slow start (hold on the rig), steady crane, gentle settle
    const k = q < 0.25 ? 0.12 * smoothstep(0, 0.25, q) : 0.12 + 0.88 * ease((q - 0.25) / 0.75);
    s.camPos.copy(c[0]).lerp(c[1], k);
    s.camPos.y += Math.sin(k * Math.PI) * 0.6;
    s.camLook.copy(c[2]).lerp(c[3], ease(clamp((q - 0.2) / 0.8)));
    s.fov = lerp(c[4], c[5], k);
  } else {
    s.world = 'surface';
    if (id !== 'well') s.dip = 0;
  }

  s.night = id === 'well' ? lerp(0.35, 0.7, p) : 0.75;
  // Topographic contours: a faint survey overlay, only while the radius sweeps.
  s.contours = id === 'nearby' ? 0.35 * seg(p, 0.1, 0.3) * (1 - seg(p, 0.75, 1)) : 0;
  s.radiusOn = id === 'nearby' ? seg(p, 0.05, 0.2) : id === 'relevant' ? 1 - seg(p, 0.6, 1) : 0;
  s.radiusKm = id === 'nearby' ? 60 * seg(p, 0.1, 0.75) : 60;
  // Darken the land a little under data overlays so markers stand out.
  s.mapDim = id === 'relevant' ? 0.2 : id === 'extract' ? 0.15 : 0;
  // Correlation: the land goes to a thin veil and the subsurface shows.
  // It fades back to solid land over the end of the phase, so the cut to
  // the rig (ahead) is from a normal surface view.
  // The land dissolves over a longer, softer window (and starts to thin
  // already at the end of "relevant"), with the strata fading in under it,
  // so there is no moment where the ground pops away.
  s.cutaway =
    id === 'correlate'
      ? smoothstep(0, 0.42, p) * (1 - smoothstep(0.86, 1, p)) * 0.85 + 0.15 * (1 - smoothstep(0.86, 1, p))
      : id === 'relevant'
        ? 0.15 * smoothstep(0.75, 1, p)
        : 0;
  s.horizon = id === 'correlate' ? smoothstep(0.08, 0.5, p) : 0;
  s.horizonGlow = id === 'correlate' ? smoothstep(0.35, 0.65, p) : 0;
  s.beams = id === 'nearby' ? seg(p, 0.15, 0.4) : id === 'relevant' ? 1 : id === 'correlate' ? 1 - seg(p, 0, 0.3) : 0;
  s.bores = id === 'relevant' ? seg(p, 0.4, 0.7) : id === 'correlate' ? 1 : 0;
  s.events = id === 'correlate' ? seg(p, 0.55, 0.75) : 0;
  s.ahead = 0;
  s.bit = 0;
  s.alert = id === 'decide' ? smoothstep(0.1, 0.25, p) : 0;
  s.paper = id === 'buried' ? seg(p, 0.25, 0.55) : id === 'extract' ? 1 - seg(p, 0.75, 1) : 0;
  s.paperOrder = id === 'extract' ? seg(p, 0.1, 0.6) : 0;

  for (const w of WELLS) {
    if (w.d < 0.01) continue; // active well, always on
    let vis = 0;
    let tone: Tone = 'neutral';
    if (id === 'well' || id === 'ahead' || id === 'decide') vis = 0;
    else if (id === 'buried' || id === 'extract') vis = 0.45;
    else if (id === 'nearby') vis = clamp((s.radiusKm - w.d) / 3);
    else {
      vis = 1;
      const pr = id === 'relevant' ? seg(p, 0.25, 0.5) : 1;
      if (RELEVANT.has(w.id)) tone = pr > 0.5 ? 'relevant' : 'neutral';
      else if (w.id === 'NHK-001') tone = pr > 0.5 ? (id === 'relevant' ? 'event' : 'dim') : 'neutral';
      else tone = pr > 0.5 ? 'dim' : 'neutral';
      if (id === 'correlate' && !RELEVANT.has(w.id)) tone = 'dim';
    }
    s.wellVis[w.id] = vis;
    s.wellTone[w.id] = tone;
  }
}
