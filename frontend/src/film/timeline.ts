// Master timeline for the DrillWise cinematic ("The Well Remembers").
// Everything in the film (camera, scene, text, sound) is a pure function of
// one clock value `t` in seconds, so pausing, skipping and replaying are all
// just "set t". Story and treatment: story/DRILLWISE_FILM_TREATMENT.md.

export type ActId = 'cold' | 'earth' | 'rig' | 'title' | 'descent' | 'offsets' | 'decision' | 'finale';

export interface Act {
  id: ActId;
  start: number;
  end: number;
}

export const ACTS: Act[] = [
  { id: 'cold', start: 0, end: 8 },
  { id: 'earth', start: 8, end: 21 },
  { id: 'rig', start: 21, end: 35 },
  { id: 'title', start: 35, end: 39 },
  { id: 'descent', start: 39, end: 58 },
  { id: 'offsets', start: 58, end: 77 },
  { id: 'decision', start: 77, end: 92 },
  { id: 'finale', start: 92, end: Number.POSITIVE_INFINITY },
];

export const ACT: Record<ActId, Act> = Object.fromEntries(ACTS.map((a) => [a.id, a])) as Record<ActId, Act>;

/** Time at which the end card (CTAs) is fully shown. Skip jumps here. */
export const END_CARD_AT = 104;

export function actAt(t: number): Act {
  for (const a of ACTS) if (t >= a.start && t < a.end) return a;
  return ACT.finale;
}

// ---------------------------------------------------------------------------
// Easing helpers
// ---------------------------------------------------------------------------
export const clamp = (x: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));
export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
export const smoothstep = (e0: number, e1: number, x: number) => {
  const p = clamp((x - e0) / (e1 - e0));
  return p * p * (3 - 2 * p);
};
export const easeInOut = (p: number) => {
  const x = clamp(p);
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
};
export const easeOut = (p: number) => 1 - Math.pow(1 - clamp(p), 3);

/** Fade-in / hold / fade-out envelope for a cue between start and end. */
export function cueOpacity(t: number, start: number, end: number, fade = 0.9): number {
  if (t < start || t > end) return 0;
  return Math.min(smoothstep(start, start + fade, t), end === Number.POSITIVE_INFINITY ? 1 : 1 - smoothstep(end - fade, end, t));
}

// ---------------------------------------------------------------------------
// Shots: which 3D world is on screen. Acts carry the story; shots carry the
// picture. The decision act cuts between two worlds (the rig floor, then
// the loss zone below it), so the two lists are kept separate.
// ---------------------------------------------------------------------------
export type SceneId = 'earth' | 'rig' | 'descent' | 'offsets' | 'none';

export interface Shot {
  scene: SceneId;
  start: number;
  end: number;
  /** Variant inside a scene, e.g. the rig at the start vs. at the decision. */
  variant: 'intro' | 'decision' | 'finale';
}

export const SHOTS: Shot[] = [
  { scene: 'none', start: 0, end: 8, variant: 'intro' },
  { scene: 'earth', start: 8, end: 21, variant: 'intro' },
  { scene: 'rig', start: 21, end: 35, variant: 'intro' },
  { scene: 'none', start: 35, end: 39, variant: 'intro' },
  { scene: 'descent', start: 39, end: 58, variant: 'intro' },
  { scene: 'offsets', start: 58, end: 77, variant: 'intro' },
  { scene: 'rig', start: 77, end: 84.4, variant: 'decision' },
  { scene: 'descent', start: 84.4, end: 92, variant: 'decision' },
  { scene: 'earth', start: 92, end: Number.POSITIVE_INFINITY, variant: 'finale' },
];

export function shotAt(t: number): Shot {
  for (const s of SHOTS) if (t >= s.start && t < s.end) return s;
  return SHOTS[SHOTS.length - 1];
}

/**
 * Black-frame opacity. Every shot opens from black (hard cut, short fade
 * up) and closes with a brief cut to black. That is how the film moves
 * between its worlds (NOW, BELOW, the map) instead of cross-dissolving.
 */
export function blackout(t: number): number {
  const s = shotAt(t);
  if (s.scene === 'none') return 1;
  const lt = t - s.start;
  const fadeIn = 1 - smoothstep(0.15, s.variant === 'decision' ? 0.6 : 1.8, lt);
  const fadeOut = s.end === Number.POSITIVE_INFINITY ? 0 : smoothstep(s.end - 0.35, s.end, t);
  return Math.max(fadeIn, fadeOut);
}

// ---------------------------------------------------------------------------
// Story depth. The bit's measured depth is the film's clock on screen.
// Numbers are story elements (illustrative), not live telemetry.
// ---------------------------------------------------------------------------
/** Depth of the offset-well kick the film is built around (BGJ-007 DDR). */
export const LOSS_ZONE_MD = 2905;
export const MD_START = 2812.4;

export function bitMd(t: number): number {
  if (t < ACT.rig.start) return MD_START;
  if (t < ACT.descent.start) return MD_START + (t - ACT.rig.start) * 0.03;
  const descentStartMd = MD_START + (ACT.descent.start - ACT.rig.start) * 0.03;
  const descentEndMd = 2846.2;
  if (t < ACT.offsets.start) {
    const p = easeInOut((t - ACT.descent.start) / (ACT.descent.end - ACT.descent.start));
    return lerp(descentStartMd, descentEndMd, p);
  }
  const offsetsEndMd = descentEndMd + (ACT.offsets.end - ACT.offsets.start) * 0.05;
  if (t < ACT.offsets.end) return descentEndMd + (t - ACT.offsets.start) * 0.05;
  // Decision: the bit closes on the Kopili top while we're on the rig
  // floor, then creeps across it (KOPILI_TOP_MD) during the held silence.
  const lt = Math.min(t, ACT.finale.start) - ACT.decision.start;
  if (lt < 7.4) return lerp(offsetsEndMd, 2898.2, easeInOut(lt / 7.4));
  if (lt < 9.0) return lerp(2898.2, 2901.0, (lt - 7.4) / 1.6);
  return 2901.0 + (lt - 9.0) * 0.8;
}

/** Top of the Kopili in the film's active well (illustrative). */
export const KOPILI_TOP_MD = 2900;

/**
 * Depth of the camera during the descent act. The camera falls from just
 * below the surface down to the bit, through every formation above it,
 * slowing hard as it arrives.
 */
export function descentCamMd(t: number): number {
  const p = clamp((t - ACT.descent.start) / (ACT.descent.end - ACT.descent.start));
  // Fast through the shallow section, decelerating into the bit.
  const q = 1 - Math.pow(1 - smoothstep(0, 0.82, p), 2.4);
  return lerp(12, bitMd(t) - 14, q);
}

/** The held breath at the loss zone: the soundtrack drops out. */
export function isSilence(t: number): boolean {
  const lt = t - ACT.decision.start;
  return lt >= 7.6 && lt < 11.2;
}

// ---------------------------------------------------------------------------
// Text cues
// ---------------------------------------------------------------------------
export type CueStyle = 'line' | 'hud' | 'title' | 'alert' | 'decision' | 'quote' | 'brand' | 'tagline' | 'note';

export interface Cue {
  start: number;
  end: number;
  style: CueStyle;
  text: string;
  sub?: string;
}

const INF = Number.POSITIVE_INFINITY;

export const CUES: Cue[] = [
  // COLD OPEN
  { start: 1.2, end: 5.1, style: 'line', text: 'Every drilling decision is made blind.' },
  { start: 5.0, end: 7.7, style: 'line', text: 'About rock that someone has already drilled.' },

  // EARTH
  { start: 10.6, end: 16.2, style: 'hud', text: 'UPPER ASSAM BASIN  ·  NAHORKATIYA  ·  27.26° N  95.29° E' },
  { start: 14.2, end: 20.4, style: 'line', text: 'Night shift. An active well, almost three kilometres down.' },

  // RIG
  { start: 23.2, end: 28.6, style: 'line', text: 'Below her, the bit is entering rock she has never seen.' },
  { start: 29.0, end: 34.4, style: 'line', text: 'Someone has. It’s written in a report no one has time to find.' },

  // TITLE
  { start: 35.5, end: 38.8, style: 'title', text: 'THE WELL REMEMBERS' },

  // DESCENT
  { start: 41.2, end: 46.4, style: 'line', text: 'Every layer has a history.' },
  {
    start: 51.0,
    end: 57.6,
    style: 'alert',
    text: 'AHEAD OF BIT  ·  KOPILI TOP  ·  ≈ 2,900 m',
    sub: 'Kicks and losses recorded in this formation in 3 offset wells.',
  },

  // OFFSETS
  { start: 59.6, end: 64.6, style: 'line', text: 'Nearby is not the same as relevant.' },
  { start: 65.0, end: 70.2, style: 'line', text: 'Some sit across a fault. Their pressure history doesn’t apply to her.' },
  { start: 70.6, end: 73.7, style: 'line', text: 'Different depths. The same formation. The rock connects them.' },
  { start: 73.9, end: 76.7, style: 'line', text: 'It has happened here before.' },

  // DECISION
  { start: 78.2, end: 83.6, style: 'decision', text: '“Weight up before Kopili. Line up the choke. We drill through it prepared.”' },
  { start: 85.0, end: 88.0, style: 'hud', text: 'ENTERING KOPILI' },
  { start: 88.4, end: 91.7, style: 'line', text: 'Pit volume steady. The well holds.' },

  // FINALE
  { start: 93.0, end: 97.9, style: 'quote', text: '“I wrote it down that night. I always hoped someone would read it.”', sub: 'The offset well’s driller.' },
  { start: 98.6, end: INF, style: 'brand', text: 'DrillWise' },
  { start: 100.0, end: INF, style: 'tagline', text: 'Every well that came before is still talking.' },
  { start: 101.6, end: INF, style: 'note', text: 'Illustrative scenario. Wells, events and the report shown come from the NWIS demo dataset (synthetic events, real well-data formats).' },
];

/** The offset-well "evidence" document beat (DOM card over the 3D map). */
export const EVIDENCE_CARD = { start: 71.0, end: 76.6 };

/** Whether the depth readout is on screen. */
export function showDepthHud(t: number): boolean {
  const a = actAt(t).id;
  return a === 'rig' || a === 'descent' || a === 'decision';
}
