import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { FilmCanvas } from './FilmCanvas';
import { Overlay } from './Overlay';
import { FilmAudio, audioSupported } from './audio';
import { createClock, seek } from './clock';
import { END_CARD_AT, clamp, smoothstep } from './timeline';
import './film.css';

// "The Well Remembers": the DrillWise cinematic. Auto-plays as one
// continuous ~105 s real-time film, rendered in the browser from the
// project's own 3D assets and well data. Story and claims guardrails:
// story/DRILLWISE_FILM_TREATMENT.md.
//
// Browsers only allow audio after a user gesture, so the film opens on a
// start gate; it also lets weaker devices choose a lighter render.

function webglAvailable(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}

const prefersReducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function useViewport() {
  const [size, setSize] = useState(() => ({ w: window.innerWidth, h: window.innerHeight }));
  useEffect(() => {
    const on = () => setSize({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener('resize', on);
    return () => window.removeEventListener('resize', on);
  }, []);
  return size;
}

type Phase = 'gate' | 'playing' | 'ended';

export const FilmPage: React.FC = () => {
  const clock = useMemo(() => createClock(0), []);
  const audio = useRef<FilmAudio | null>(null);
  const [phase, setPhase] = useState<Phase>('gate');
  const [t, setT] = useState(0);
  const [paused, setPaused] = useState(false);
  const [muted, setMuted] = useState(false);
  const [ready, setReady] = useState(false);
  const [lowPower, setLowPower] = useState(() => (navigator.hardwareConcurrency ?? 8) <= 4);
  const [controlsVisible, setControlsVisible] = useState(true);
  const hideTimer = useRef<number>();
  const { w, h } = useViewport();
  const canRender = useMemo(webglAvailable, []);
  const reduced = useMemo(prefersReducedMotion, []);

  // Dev-only frame inspection: /film?t=52 opens paused on that frame (no
  // gate, no audio), for checking shots without watching from the start.
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    const q = new URLSearchParams(window.location.search).get('t');
    if (q === null) return;
    seek(clock, Number(q) || 0);
    clock.playing = false;
    setPaused(true);
    setPhase(Number(q) >= END_CARD_AT ? 'ended' : 'playing');
  }, [clock]);

  // UI clock: mirrors the render-loop clock into React at display rate, and
  // drives the audio from the same value.
  useEffect(() => {
    let raf = 0;
    const loop = () => {
      audio.current?.update(clock.t, clock.playing, clock.seeked);
      clock.seeked = false;
      setT(clock.t);
      if (clock.t >= END_CARD_AT && phase === 'playing') setPhase('ended');
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [clock, phase]);

  useEffect(() => () => audio.current?.dispose(), []);

  const start = useCallback(async () => {
    if (audioSupported() && !audio.current) audio.current = new FilmAudio();
    await audio.current?.resume();
    audio.current?.setMuted(muted);
    seek(clock, 0);
    audio.current?.reset();
    clock.playing = true;
    setPaused(false);
    setPhase('playing');
  }, [clock, muted]);

  const togglePause = useCallback(() => {
    if (phase !== 'playing') return;
    clock.playing = !clock.playing;
    setPaused(!clock.playing);
  }, [clock, phase]);

  const skip = useCallback(() => {
    seek(clock, END_CARD_AT);
    clock.playing = true;
    setPaused(false);
    setPhase('ended');
  }, [clock]);

  const replay = useCallback(() => {
    seek(clock, 0);
    audio.current?.reset();
    clock.playing = true;
    setPaused(false);
    setPhase('playing');
  }, [clock]);

  const toggleMute = useCallback(() => {
    setMuted((m) => {
      audio.current?.setMuted(!m);
      return !m;
    });
  }, []);

  // Keyboard: space = pause, M = mute, Esc = skip, F = fullscreen.
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (phase === 'gate') {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          start();
        }
        return;
      }
      if (e.key === ' ') {
        e.preventDefault();
        togglePause();
      } else if (e.key.toLowerCase() === 'm') toggleMute();
      else if (e.key === 'Escape' && phase === 'playing') skip();
      else if (e.key.toLowerCase() === 'f') {
        if (document.fullscreenElement) document.exitFullscreen();
        else document.documentElement.requestFullscreen?.().catch(() => undefined);
      }
    };
    window.addEventListener('keydown', on);
    return () => window.removeEventListener('keydown', on);
  }, [phase, start, togglePause, toggleMute, skip]);

  // Controls fade out while the film plays; any mouse movement brings them back.
  const poke = useCallback(() => {
    setControlsVisible(true);
    window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(() => setControlsVisible(false), 2200);
  }, []);
  useEffect(() => {
    if (phase === 'playing') poke();
    return () => window.clearTimeout(hideTimer.current);
  }, [phase, poke]);

  const progress = clamp(t / END_CARD_AT);
  const endO = phase === 'ended' ? smoothstep(END_CARD_AT - 0.5, END_CARD_AT + 1.2, t) : 0;

  if (!canRender || reduced) {
    return <StillVersion reason={!canRender ? 'webgl' : 'motion'} />;
  }

  return (
    <div className={`film-root ${phase === 'playing' && !controlsVisible && !paused ? 'film-hide-cursor' : ''}`} onMouseMove={poke}>
      {phase !== 'gate' && <FilmCanvas clock={clock} lowPower={lowPower} onReady={() => setReady(true)} />}
      {phase !== 'gate' && <Overlay t={t} width={w} height={h} />}

      {phase === 'gate' && (
        <div className="film-gate">
          <div className="film-gate-inner">
            <div className="film-gate-kicker">DRILLWISE · A SHORT FILM</div>
            <h1 className="film-gate-title">THE WELL REMEMBERS</h1>
            <p className="film-gate-line">About 100 seconds. Best with sound, in a dark room.</p>
            <button className="film-gate-play" onClick={start} autoFocus>
              <span className="film-play-icon" aria-hidden /> Play
            </button>
            <div className="film-gate-options">
              <label>
                <input type="checkbox" checked={lowPower} onChange={(e) => setLowPower(e.target.checked)} /> Lighter rendering (slower devices)
              </label>
              <a href="/app">Skip to the app</a>
            </div>
          </div>
        </div>
      )}

      {phase === 'playing' && (
        <div className={`film-controls ${controlsVisible || paused ? '' : 'film-controls-hidden'}`}>
          <button onClick={togglePause} aria-label={paused ? 'Play' : 'Pause'}>
            {paused ? 'Play' : 'Pause'}
          </button>
          <button onClick={toggleMute} aria-label={muted ? 'Unmute' : 'Mute'}>
            {muted ? 'Sound off' : 'Sound on'}
          </button>
          <div className="film-progress" aria-hidden>
            <div style={{ width: `${progress * 100}%` }} />
          </div>
          <button onClick={skip} className="film-skip">
            Skip
          </button>
        </div>
      )}

      {phase === 'playing' && !ready && <div className="film-loading">Loading</div>}

      {phase === 'ended' && (
        <div className="film-end" style={{ opacity: endO, pointerEvents: endO > 0.5 ? 'auto' : 'none' }}>
          <a className="film-end-primary" href="/app/command-center">
            Open the command center
          </a>
          <a className="film-end-secondary" href="/">
            About DrillWise
          </a>
          <button className="film-end-secondary" onClick={replay}>
            Watch again
          </button>
        </div>
      )}
    </div>
  );
};

/** Shown when WebGL is unavailable or the viewer prefers reduced motion. */
function StillVersion({ reason }: { reason: 'webgl' | 'motion' }) {
  return (
    <div className="film-root film-still">
      <div className="film-still-inner">
        <div className="film-gate-kicker">DRILLWISE</div>
        <h1 className="film-gate-title">THE WELL REMEMBERS</h1>
        <p>Every drilling decision is made blind, about rock that someone has already drilled.</p>
        <p>
          At 2,905 m in the Kopili, an offset well once took a kick. DrillWise finds that report, ranks which nearby wells
          truly share her rock, and warns the engineer before her bit gets there.
        </p>
        <p className="film-still-tagline">Every well that came before is still talking.</p>
        <a className="film-end-primary" href="/app/command-center">
          Open the command center
        </a>
        <p className="film-still-note">
          {reason === 'webgl'
            ? 'This device can’t show the 3D film (WebGL unavailable).'
            : 'Showing the still version because your system asks for reduced motion.'}
        </p>
      </div>
    </div>
  );
}

export default FilmPage;
