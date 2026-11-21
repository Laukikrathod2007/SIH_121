import { ACT, actAt, isSilence, smoothstep } from './timeline';

// The film's soundtrack, synthesized with the Web Audio API (no audio
// files). Every layer is a gain envelope driven by the film clock, so
// pause/seek simply recompute levels.
//
//   Shepard riser  - endlessly rising tone under the cold open, Earth and
//                    rig acts; the tension that never resolves.
//   Pump tick      - the mud pump stroke counter: the film's clock.
//   Rain + wind    - filtered noise on the rig.
//   Sub drone      - the rock. Under the descent and offsets.
//   Hit            - the low impact on cuts to black (title, decision).
//   Resolve        - after the silence: one sustained chord, then a
//                    single, slow, piano-like line under the finale.

type Layer = { gain: GainNode; level: (t: number) => number };

export class FilmAudio {
  private ctx: AudioContext;
  private master: GainNode;
  private layers: Layer[] = [];
  private shepardOsc: { osc: OscillatorNode; gain: GainNode; offset: number }[] = [];
  private lastT = -1;
  private lastTick = -1;
  private firedHits = new Set<number>();
  private firedNotes = new Set<number>();
  private noiseBuffer: AudioBuffer;
  private muted = false;

  constructor() {
    const AC = window.AudioContext || (window as any).webkitAudioContext;
    this.ctx = new AC();
    this.master = this.ctx.createGain();
    this.master.gain.value = 0.85;

    // Gentle bus compression + a long synthetic reverb for space.
    const comp = this.ctx.createDynamicsCompressor();
    comp.threshold.value = -18;
    comp.ratio.value = 3;
    const reverb = this.ctx.createConvolver();
    reverb.buffer = this.impulse(4.5, 2.6);
    const wet = this.ctx.createGain();
    wet.gain.value = 0.32;
    this.master.connect(comp);
    this.master.connect(reverb);
    reverb.connect(wet);
    wet.connect(comp);
    comp.connect(this.ctx.destination);

    this.noiseBuffer = this.makeNoise(4);
    this.buildShepard();
    this.buildRain();
    this.buildDrone();
    this.buildResolve();
  }

  // -------------------------------------------------------------------------
  // Building blocks
  // -------------------------------------------------------------------------
  private impulse(seconds: number, decay: number): AudioBuffer {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
    return buf;
  }

  private makeNoise(seconds: number): AudioBuffer {
    const len = Math.floor(this.ctx.sampleRate * seconds);
    const buf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
    const d = buf.getChannelData(0);
    // Pinkish noise (Paul Kellet's filter).
    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
    for (let i = 0; i < len; i++) {
      const w = Math.random() * 2 - 1;
      b0 = 0.99886 * b0 + w * 0.0555179;
      b1 = 0.99332 * b1 + w * 0.0750759;
      b2 = 0.969 * b2 + w * 0.153852;
      b3 = 0.8665 * b3 + w * 0.3104856;
      b4 = 0.55 * b4 + w * 0.5329522;
      b5 = -0.7616 * b5 - w * 0.016898;
      d[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
      b6 = w * 0.115926;
    }
    return buf;
  }

  private layer(level: (t: number) => number): GainNode {
    const gain = this.ctx.createGain();
    gain.gain.value = 0;
    gain.connect(this.master);
    this.layers.push({ gain, level });
    return gain;
  }

  private buildShepard() {
    // Six octave-spaced sines whose pitch rises continuously; each one's
    // loudness is a bell curve over pitch, so the whole stack seems to rise
    // forever without arriving.
    const bus = this.layer((t) => {
      if (t >= ACT.descent.start) return 0;
      if (actAt(t).id === 'title') return 0;
      return 0.16 * smoothstep(0.2, 4, t) * (1 - smoothstep(ACT.rig.end - 1.5, ACT.rig.end, t));
    });
    const filter = this.ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 1800;
    filter.connect(bus);
    for (let i = 0; i < 6; i++) {
      const osc = this.ctx.createOscillator();
      osc.type = 'sine';
      const gain = this.ctx.createGain();
      gain.gain.value = 0;
      osc.connect(gain);
      gain.connect(filter);
      osc.start();
      this.shepardOsc.push({ osc, gain, offset: i / 6 });
    }
  }

  private buildRain() {
    const bus = this.layer((t) => {
      const a = actAt(t).id;
      if (a === 'rig') return 0.22 * smoothstep(ACT.rig.start, ACT.rig.start + 1.5, t);
      if (a === 'decision' && t < 84.4) return 0.14;
      if (a === 'earth') return 0.04 * smoothstep(ACT.earth.end - 4, ACT.earth.end, t);
      return 0;
    });
    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuffer;
    src.loop = true;
    const hp = this.ctx.createBiquadFilter();
    hp.type = 'highpass';
    hp.frequency.value = 700;
    const lp = this.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 6500;
    src.connect(hp);
    hp.connect(lp);
    lp.connect(bus);
    src.start();

    // Wind: slow-moving bandpassed noise.
    const wind = this.ctx.createBufferSource();
    wind.buffer = this.noiseBuffer;
    wind.loop = true;
    wind.playbackRate.value = 0.5;
    const bp = this.ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = 260;
    bp.Q.value = 0.7;
    const windGain = this.ctx.createGain();
    windGain.gain.value = 0.9;
    const lfo = this.ctx.createOscillator();
    lfo.frequency.value = 0.07;
    const lfoGain = this.ctx.createGain();
    lfoGain.gain.value = 140;
    lfo.connect(lfoGain);
    lfoGain.connect(bp.frequency);
    lfo.start();
    wind.connect(bp);
    bp.connect(windGain);
    windGain.connect(bus);
    wind.start();
  }

  private buildDrone() {
    const bus = this.layer((t) => {
      const a = actAt(t).id;
      if (isSilence(t)) return 0;
      if (a === 'descent') return 0.3 * smoothstep(ACT.descent.start, ACT.descent.start + 3, t);
      if (a === 'offsets') return 0.24;
      if (a === 'decision') return 0.3 * (1 - smoothstep(ACT.decision.start + 6.4, ACT.decision.start + 7.6, t));
      if (a === 'rig') return 0.08 * smoothstep(ACT.rig.start + 6, ACT.rig.end, t);
      return 0;
    });
    const lp = this.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 220;
    lp.connect(bus);
    // Two slightly detuned low saws plus a sub sine: a slow beating mass.
    [36.7, 36.95, 55.0].forEach((f, i) => {
      const o = this.ctx.createOscillator();
      o.type = i === 2 ? 'sine' : 'sawtooth';
      o.frequency.value = f;
      const g = this.ctx.createGain();
      g.gain.value = i === 2 ? 0.6 : 0.35;
      o.connect(g);
      g.connect(lp);
      o.start();
    });
    // Rumble: very low-passed noise, the rock itself.
    const n = this.ctx.createBufferSource();
    n.buffer = this.noiseBuffer;
    n.loop = true;
    n.playbackRate.value = 0.25;
    const nl = this.ctx.createBiquadFilter();
    nl.type = 'lowpass';
    nl.frequency.value = 90;
    const ng = this.ctx.createGain();
    ng.gain.value = 1.6;
    n.connect(nl);
    nl.connect(ng);
    ng.connect(bus);
    n.start();
  }

  private buildResolve() {
    // After the silence: an open fifth that swells in and stays under the
    // finale. Warm, not triumphant.
    const bus = this.layer((t) => {
      const lt = t - ACT.decision.start;
      if (t < ACT.decision.start + 11.2) return 0;
      const inA = smoothstep(11.2, 14.5, lt);
      return 0.12 * inA;
    });
    const lp = this.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 1400;
    lp.connect(bus);
    [110, 164.8, 220, 329.6].forEach((f, i) => {
      const o = this.ctx.createOscillator();
      o.type = i % 2 ? 'triangle' : 'sine';
      o.frequency.value = f;
      o.detune.value = (i - 1.5) * 4;
      const g = this.ctx.createGain();
      g.gain.value = [0.5, 0.35, 0.3, 0.18][i];
      o.connect(g);
      g.connect(lp);
      o.start();
    });
  }

  // -------------------------------------------------------------------------
  // One-shots
  // -------------------------------------------------------------------------
  private tick(when: number, accent: boolean) {
    // Mud pump stroke: a short, damped metallic knock.
    const o = this.ctx.createOscillator();
    o.type = 'triangle';
    o.frequency.setValueAtTime(accent ? 180 : 140, when);
    o.frequency.exponentialRampToValueAtTime(60, when + 0.09);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(accent ? 0.32 : 0.2, when + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 0.16);
    const n = this.ctx.createBufferSource();
    n.buffer = this.noiseBuffer;
    const nf = this.ctx.createBiquadFilter();
    nf.type = 'bandpass';
    nf.frequency.value = 2400;
    nf.Q.value = 3;
    const ng = this.ctx.createGain();
    ng.gain.setValueAtTime(0.08, when);
    ng.gain.exponentialRampToValueAtTime(0.0001, when + 0.05);
    o.connect(g);
    n.connect(nf);
    nf.connect(ng);
    g.connect(this.master);
    ng.connect(this.master);
    o.start(when);
    o.stop(when + 0.2);
    n.start(when, Math.random() * 3, 0.06);
  }

  private hit(when: number, level = 1) {
    // Low impact: pitched-down sine thump plus a burst of filtered noise.
    const o = this.ctx.createOscillator();
    o.type = 'sine';
    o.frequency.setValueAtTime(70, when);
    o.frequency.exponentialRampToValueAtTime(28, when + 1.4);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0, when);
    g.gain.linearRampToValueAtTime(0.9 * level, when + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, when + 3.2);
    o.connect(g);
    g.connect(this.master);
    o.start(when);
    o.stop(when + 3.4);
    const n = this.ctx.createBufferSource();
    n.buffer = this.noiseBuffer;
    const nf = this.ctx.createBiquadFilter();
    nf.type = 'lowpass';
    nf.frequency.value = 400;
    const ng = this.ctx.createGain();
    ng.gain.setValueAtTime(0.5 * level, when);
    ng.gain.exponentialRampToValueAtTime(0.0001, when + 1.2);
    n.connect(nf);
    nf.connect(ng);
    ng.connect(this.master);
    n.start(when, 0, 1.3);
  }

  private note(when: number, freq: number, level = 0.12) {
    // Soft, felt-piano-like note: two partials with a quick attack and a
    // long exponential decay.
    [1, 2.01, 3.0].forEach((m, i) => {
      const o = this.ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = freq * m;
      const g = this.ctx.createGain();
      const l = level * [1, 0.35, 0.12][i];
      g.gain.setValueAtTime(0, when);
      g.gain.linearRampToValueAtTime(l, when + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, when + 5.5 - i);
      o.connect(g);
      g.connect(this.master);
      o.start(when);
      o.stop(when + 6);
    });
  }

  // -------------------------------------------------------------------------
  // Per-frame update
  // -------------------------------------------------------------------------
  update(t: number, playing: boolean, seeked: boolean) {
    const now = this.ctx.currentTime;
    const target = playing && !this.muted ? 1 : 0;
    this.master.gain.setTargetAtTime(target * 0.85, now, playing ? 0.15 : 0.05);

    for (const l of this.layers) l.gain.gain.setTargetAtTime(l.level(t), now, 0.12);

    // Shepard: each voice's pitch position cycles every 10 s, offset per voice.
    const cycle = (t / 10) % 1;
    for (const v of this.shepardOsc) {
      const pos = (cycle + v.offset) % 1;
      const freq = 55 * Math.pow(2, pos * 6);
      v.osc.frequency.setTargetAtTime(freq, now, 0.02);
      const bell = Math.exp(-Math.pow((pos - 0.5) / 0.22, 2));
      v.gain.gain.setTargetAtTime(bell * 0.22, now, 0.05);
    }

    if (seeked) {
      // Don't fire one-shots for everything we skipped over.
      this.lastT = t;
      this.lastTick = Math.floor(t / 0.72);
      for (const h of HITS) if (h <= t) this.firedHits.add(h);
      for (const n of NOTES) if (n.t <= t) this.firedNotes.add(n.t);
      return;
    }
    if (!playing) return;

    // Pump ticks: steady 0.72 s stroke during the rig acts. Accent every 4.
    const a = actAt(t).id;
    const tickOn = (a === 'cold' && t > 2) || a === 'earth' || a === 'rig' || (a === 'decision' && !isSilence(t) && t < ACT.decision.start + 7.6);
    const k = Math.floor(t / 0.72);
    if (k !== this.lastTick) {
      if (tickOn) {
        const vol = a === 'earth' ? 0.5 : 1;
        if (vol > 0.6 || k % 2 === 0) this.tick(now + 0.01, k % 4 === 0);
      }
      this.lastTick = k;
    }

    for (const h of HITS) {
      if (h <= t && h > this.lastT && !this.firedHits.has(h)) {
        this.firedHits.add(h);
        this.hit(now + 0.01, h === ACT.title.start ? 1 : 0.7);
      }
    }
    for (const n of NOTES) {
      if (n.t <= t && n.t > this.lastT && !this.firedNotes.has(n.t)) {
        this.firedNotes.add(n.t);
        this.note(now + 0.01, n.f, n.l);
      }
    }
    this.lastT = t;
  }

  async resume() {
    if (this.ctx.state === 'suspended') await this.ctx.resume();
  }

  setMuted(m: boolean) {
    this.muted = m;
  }

  /** Re-arm one-shots (used on replay). */
  reset() {
    this.firedHits.clear();
    this.firedNotes.clear();
    this.lastT = -1;
  }

  dispose() {
    this.ctx.close().catch(() => undefined);
  }
}

// Low impacts: title card, the cut to the rig floor at the decision, and
// the cut to the loss zone.
const HITS = [ACT.title.start, ACT.decision.start, 84.4];

// The piano line under the finale (A minor, slow, unresolved until last).
const NOTES: { t: number; f: number; l: number }[] = [
  { t: 89.0, f: 220.0, l: 0.1 },
  { t: 92.6, f: 261.6, l: 0.11 },
  { t: 94.6, f: 329.6, l: 0.1 },
  { t: 96.8, f: 293.7, l: 0.1 },
  { t: 99.0, f: 220.0, l: 0.12 },
  { t: 99.02, f: 329.6, l: 0.07 },
];

export const audioSupported = () => typeof window !== 'undefined' && !!(window.AudioContext || (window as any).webkitAudioContext);
