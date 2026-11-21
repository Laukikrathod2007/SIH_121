// The story's score: a recorded orchestral piece, cut to the story's 67 s
// and kept in sync with the story clock.
//
//   public/story/score.mp3 - "Lightless Dawn", Kevin MacLeod
//   (incompetech.com), licensed under Creative Commons: By Attribution 4.0
//   (https://creativecommons.org/licenses/by/4.0/). Edited for length:
//   its quiet opening, its build and its climax, crossfaded to 67 s
//   (scripts/build-score.ps1). Credited on the page.
//
// Behaviour: soft fades on every start/stop (never a hard cut), quiet
// overall (a bed under the story, not over it), follows pause/seek, and
// is silenced whenever the page isn't being watched (tab hidden, window
// blurred, or the story scrolled out of view) - see StoryPage.

/**
 * Per phase [low-pass Hz, level]: well, buried (problem: distant, held
 * back), extract, nearby, relevant, correlate (solution: opening up),
 * ahead (the descent: full), decide (resolution: full, a touch softer).
 */
const PHASE_TONE: [number, number][] = [
  [1800, 0.8],
  [1400, 0.72],
  [4200, 0.88],
  [7000, 0.95],
  [9000, 1],
  [9000, 1],
  [16000, 1],
  [16000, 0.92],
];

export class StorySound {
  private ctx: AudioContext;
  private audio: HTMLAudioElement;
  private gain: GainNode;
  private enabled = false;
  private playing = false;
  private visible = true;
  private ready = false;
  private tone: BiquadFilterNode;
  private mood: GainNode;
  private phase = -1;

  constructor() {
    const AC = window.AudioContext || (window as any).webkitAudioContext;
    this.ctx = new AC();
    this.audio = new Audio('/story/score.mp3');
    this.audio.preload = 'auto';
    this.audio.crossOrigin = 'anonymous';
    this.audio.addEventListener('canplaythrough', () => (this.ready = true), { once: true });
    const src = this.ctx.createMediaElementSource(this.audio);
    // A gentle low-shelf trim keeps the low strings warm but not boomy.
    const shelf = this.ctx.createBiquadFilter();
    shelf.type = 'lowshelf';
    shelf.frequency.value = 120;
    shelf.gain.value = -2;
    // Follows the story (setPhase): muffled and distant while the problem
    // is told, opening to the full orchestra as the solution arrives.
    this.tone = this.ctx.createBiquadFilter();
    this.tone.type = 'lowpass';
    this.tone.Q.value = 0.5;
    this.tone.frequency.value = PHASE_TONE[0][0];
    this.mood = this.ctx.createGain();
    this.mood.gain.value = PHASE_TONE[0][1];
    this.gain = this.ctx.createGain();
    this.gain.gain.value = 0;
    src.connect(shelf);
    shelf.connect(this.tone);
    this.tone.connect(this.mood);
    this.mood.connect(this.gain);
    this.gain.connect(this.ctx.destination);
  }

  /** Target volume: soft, under the story. */
  private level() {
    return this.enabled && this.playing && this.visible ? 0.55 : 0;
  }

  private apply(fade = 0.8) {
    const now = this.ctx.currentTime;
    const target = this.level();
    this.gain.gain.cancelScheduledValues(now);
    this.gain.gain.setValueAtTime(this.gain.gain.value, now);
    this.gain.gain.linearRampToValueAtTime(target, now + fade);
    if (target > 0) {
      if (this.ctx.state === 'suspended') this.ctx.resume().catch(() => undefined);
      if (this.audio.paused) this.audio.play().catch(() => undefined);
    } else {
      // Pause after the fade, so stopping never clicks.
      window.setTimeout(() => {
        if (this.level() === 0 && !this.audio.paused) this.audio.pause();
      }, fade * 1000 + 30);
    }
  }

  /** Called with the story time every frame; keeps the music in sync. */
  setTime(t: number) {
    if (!this.enabled || !this.ready) return;
    if (this.level() > 0 && Math.abs(this.audio.currentTime - t) > 0.4) this.audio.currentTime = t;
  }

  async setEnabled(on: boolean) {
    this.enabled = on;
    if (on && this.ctx.state === 'suspended') await this.ctx.resume();
    this.apply(on ? 1.2 : 0.5);
  }

  setPlaying(playing: boolean) {
    this.playing = playing;
    this.apply(playing ? 0.9 : 0.6);
  }

  /** The page is (or isn't) being watched. */
  setVisible(visible: boolean) {
    if (visible === this.visible) return;
    this.visible = visible;
    this.apply(visible ? 1.6 : 0.4);
  }

  /** Shape the score to the phase: filter cutoff and level glide over ~2.5 s. */
  setPhase(i: number) {
    if (i === this.phase) return;
    this.phase = i;
    const [hz, lvl] = PHASE_TONE[Math.max(0, Math.min(PHASE_TONE.length - 1, i))];
    const now = this.ctx.currentTime;
    this.tone.frequency.cancelScheduledValues(now);
    this.tone.frequency.setTargetAtTime(hz, now, 0.8);
    this.mood.gain.cancelScheduledValues(now);
    this.mood.gain.setTargetAtTime(lvl, now, 0.8);
  }

  dispose() {
    this.audio.pause();
    this.audio.src = '';
    this.ctx.close().catch(() => undefined);
  }
}

export const soundSupported = () => typeof window !== 'undefined' && !!(window.AudioContext || (window as any).webkitAudioContext);
