// Shared, mutable film clock. One object is created per viewing and read
// by the 3D director, the DOM overlay and the audio engine, so all three
// stay on the same frame without going through React state.
export interface FilmClock {
  /** Story time in seconds. */
  t: number;
  /** Whether time is advancing. */
  playing: boolean;
  /** Time step of the latest frame (0 when paused or after a seek). */
  dt: number;
  /** Set by seek(); tells consumers to resync instead of firing one-shots. */
  seeked: boolean;
}

export function createClock(t = 0): FilmClock {
  return { t, playing: false, dt: 0, seeked: true };
}

export function seek(clock: FilmClock, t: number) {
  clock.t = t;
  clock.dt = 0;
  clock.seeked = true;
}
