import React, { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { PHASES, PHASE_STARTS, TOTAL_DURATION, phaseAt } from './phases';
import { Hud } from './Hud';
import { Intro } from './Intro';
import { StorySound, soundSupported } from './sound';
import type { WorldClock } from './scene/World';
import { POINTER } from './pointer';
import './story.css';

// DrillWise product story: 8 phases, ~74 s, over one continuous real-time
// 3D world of the Upper Assam basin (scene/). Layout follows a product
// keynote: nav, status strip, full-bleed scene, message on the left,
// product UI on the right, transport bar with a phase rail. Every number
// shown comes from the NWIS backend's output for the demo scenario.
// The dramatic cinematic stays separate at /film.

const World = lazy(() => import('./scene/World'));

const prefersReducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const webglOk = () => {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
};

function useStoryClock(paused: boolean) {
  const [t, setT] = useState(0);
  // Starts paused: the intro (video, then the choice screen) starts it.
  const [playing, setPlaying] = useState(false);
  void paused;
  const tRef = useRef(0);
  const playingRef = useRef(playing);
  playingRef.current = playing;
  useEffect(() => {
    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      if (playingRef.current) {
        tRef.current = Math.min(TOTAL_DURATION, tRef.current + dt);
        if (tRef.current >= TOTAL_DURATION) setPlaying(false);
        setT(tRef.current);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);
  const seekTo = useCallback((v: number) => {
    tRef.current = Math.max(0, Math.min(TOTAL_DURATION, v));
    setT(tRef.current);
  }, []);
  return { t, playing, setPlaying, seekTo };
}

const STAGE_LABEL = { problem: 'The problem', solution: 'The solution', outcome: 'The outcome' } as const;
const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s) % 60).padStart(2, '0')}`;

export const StoryPage: React.FC = () => {
  const reduced = useMemo(prefersReducedMotion, []);
  const canRender = useMemo(webglOk, []);
  const { t, playing, setPlaying, seekTo } = useStoryClock(reduced);
  const playingRef = useRef(playing);
  playingRef.current = playing;
  const { index, p } = phaseAt(t);
  const phase = PHASES[index];
  const vp = reduced ? 1 : p;
  const [lowPower, setLowPower] = useState(() => (navigator.hardwareConcurrency ?? 8) <= 4);

  // Shared clock for the 3D world (read every frame, no React re-render).
  const worldClock = useRef<WorldClock>({ t: 0, index: 0, p: 0 });
  worldClock.current = { t, index, p: vp };

  // ---- intro: loading animation, then the choice screen
  const devFrame = import.meta.env.DEV && new URLSearchParams(window.location.search).has('t');
  const [introDone, setIntroDone] = useState(devFrame);
  const [worldReady, setWorldReady] = useState(false);
  // Start building the 3D world only once the opening video is playing
  // (or after 1.5 s), so its downloads and shader compiles never stall the
  // video's first frames. The world still has the rest of the 10 s video
  // to load, hidden behind it.
  const [worldGo, setWorldGo] = useState(devFrame);
  useEffect(() => {
    if (worldGo) return;
    const go = () => setWorldGo(true);
    const t = window.setTimeout(go, 1500);
    const v = document.querySelector<HTMLVideoElement>('.intro-video');
    v?.addEventListener('playing', go, { once: true });
    return () => {
      window.clearTimeout(t);
      v?.removeEventListener('playing', go);
    };
  }, [worldGo]);
  useEffect(() => {
    // The 3D world flags the document once it has drawn; poll for it.
    const id = window.setInterval(() => {
      if (document.documentElement.dataset.storyRendered) {
        setWorldReady(true);
        window.clearInterval(id);
      }
    }, 300);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    const q = new URLSearchParams(window.location.search).get('t');
    if (q === null) return;
    seekTo(Number(q) || 0);
    setPlaying(false);
  }, [seekTo, setPlaying]);

  // ---- sound
  const sound = useRef<StorySound | null>(null);
  const [soundOn, setSoundOn] = useState(false);
  useEffect(() => sound.current?.setPlaying(playing), [playing]);

  // Stop when nobody is watching: tab hidden, window blurred, or the story
  // scrolled out of view. The story pauses, and the music fades out.
  // Coming back resumes both, softly.
  const stageRef = useRef<HTMLElement>(null);
  const wasPlaying = useRef(false);
  useEffect(() => {
    let inView = true;
    // Focus is tracked from blur/focus events only: hasFocus() is false
    // on load in some setups (embedded previews, a second monitor), which
    // would pause a story someone is actually watching.
    let focused = true;
    const watched = () => !document.hidden && focused && inView;
    let last = true;
    const onBlur = () => {
      focused = false;
      update();
    };
    const onFocus = () => {
      focused = true;
      update();
    };
    const update = () => {
      const w = watched();
      if (w === last) return;
      last = w;
      sound.current?.setVisible(w);
      if (!w) {
        wasPlaying.current = playingRef.current;
        setPlaying(false);
      } else if (wasPlaying.current) {
        setPlaying(true);
      }
    };
    const io = new IntersectionObserver(
      ([e]) => {
        inView = e.intersectionRatio > 0.35;
        update();
      },
      { threshold: [0, 0.35, 1] },
    );
    if (stageRef.current) io.observe(stageRef.current);
    document.addEventListener('visibilitychange', update);
    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    return () => {
      io.disconnect();
      document.removeEventListener('visibilitychange', update);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
    };
  }, [setPlaying]);
  // The score follows the story clock, and its colour follows the phase.
  useEffect(() => {
    sound.current?.setTime(t);
  }, [t]);
  useEffect(() => sound.current?.setPhase(index), [index]);
  useEffect(() => () => sound.current?.dispose(), []);
  const toggleSound = useCallback(async () => {
    if (!soundSupported()) return;
    if (!sound.current) {
      sound.current = new StorySound();
      sound.current.setPhase(index);
    }
    const next = !soundOn;
    await sound.current.setEnabled(next);
    sound.current.setPlaying(playing);
    setSoundOn(next);
  }, [soundOn, index, playing]);

  // ---- transport
  const goto = useCallback(
    (i: number) => {
      const k = Math.max(0, Math.min(PHASES.length - 1, i));
      seekTo(PHASE_STARTS[k] + 0.001);
      if (!reduced) setPlaying(true);
    },
    [seekTo, setPlaying, reduced],
  );
  const ended = t >= TOTAL_DURATION;
  const togglePlay = useCallback(() => {
    if (ended) {
      seekTo(0);
      setPlaying(true);
    } else setPlaying(!playing);
  }, [ended, playing, seekTo, setPlaying]);
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goto(index + 1);
      else if (e.key === 'ArrowLeft') goto(index - 1);
      else if (e.key === ' ') {
        e.preventDefault();
        togglePlay();
      }
    };
    window.addEventListener('keydown', on);
    return () => window.removeEventListener('keydown', on);
  }, [goto, index, togglePlay]);

  // A quick base fade; the per-line reveal itself is CSS.
  const textIn = reduced ? 1 : Math.min(1, (t - PHASE_STARTS[index]) / 0.35);

  // Cursor parallax: the pointer position (-1..1) is shared with the camera
  // (a few metres of drift) and the overlay (a few pixels), eased, so the
  // frame feels alive under the hand without anything visibly moving.
  useEffect(() => {
    if (reduced) return;
    const el = stageRef.current;
    if (!el) return;
    let raf = 0;
    const on = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      POINTER.x = ((e.clientX - r.left) / r.width) * 2 - 1;
      POINTER.y = ((e.clientY - r.top) / r.height) * 2 - 1;
      if (!raf)
        raf = requestAnimationFrame(() => {
          raf = 0;
          el.style.setProperty('--mx', POINTER.x.toFixed(3));
          el.style.setProperty('--my', POINTER.y.toFixed(3));
        });
    };
    const off = () => {
      POINTER.x = 0;
      POINTER.y = 0;
      el.style.setProperty('--mx', '0');
      el.style.setProperty('--my', '0');
    };
    el.addEventListener('pointermove', on);
    el.addEventListener('pointerleave', off);
    return () => {
      cancelAnimationFrame(raf);
      el.removeEventListener('pointermove', on);
      el.removeEventListener('pointerleave', off);
    };
  }, [reduced]);

  const beginStory = useCallback(
    async (withSound: boolean) => {
      setIntroDone(true);
      if (withSound && soundSupported()) {
        if (!sound.current) {
          sound.current = new StorySound();
          sound.current.setPhase(0);
        }
        await sound.current.setEnabled(true);
        sound.current.setPlaying(true);
        setSoundOn(true);
      }
      seekTo(0);
      if (!reduced) setPlaying(true);
    },
    [reduced, seekTo, setPlaying],
  );

  return (
    <div className="story-root">
      {!introDone && <Intro onStart={beginStory} ready={worldReady || !canRender} />}
      <header className="story-nav">
        <a href="/" className="story-brand" aria-label="DrillWise home">
          <img src="/brand/drillwise-logo-horizontal.png" alt="DrillWise" />
        </a>
        <nav className="story-links" aria-label="Sections">
          <a href="#evidence">Why</a>
          <a href="#how">How it works</a>
          <a href="#honesty">Real vs simulated</a>
          <a href="/film">The film</a>
        </nav>
        <a className="story-console" href="/app/command-center">
          Open command center <span aria-hidden>↗</span>
        </a>
      </header>

      <div className="story-status">
        <span>
          Demo scenario <i>·</i> real terrain and Sentinel-2 imagery of Upper Assam <i>·</i> wells, formations and scores from the live NWIS backend
        </span>
        <span className="story-status-right">
          WELL NHK-002 <i>·</i> 2,850 m MD <i>·</i> {mmss(t)} / {mmss(TOTAL_DURATION)}
        </span>
      </div>

      <section className="story-stage-area" ref={stageRef}>
        {canRender && worldGo ? (
          <Suspense fallback={<div className="story-canvas story-canvas-loading" />}>
            <World clock={worldClock} lowPower={lowPower} />
          </Suspense>
        ) : (
          <div className="story-canvas story-canvas-loading" />
        )}
        <div className="story-scrim" />

        {/* Keyed per phase so each line re-runs its staggered reveal (story.css). */}
        <div key={phase.id} className="story-copy" aria-live="polite" style={{ opacity: Math.max(0.001, textIn) }}>
          <div className={`story-stage story-stage-${phase.stage}`}>{STAGE_LABEL[phase.stage]}</div>
          <div className="story-kicker">{phase.kicker}</div>
          <h1 className="story-title">{phase.title}</h1>
          <p className="story-body">{phase.body}</p>
          {phase.facts && (
            <dl className="story-facts">
              {phase.facts.map((f) => (
                <div key={f.label}>
                  <dt>{f.label}</dt>
                  <dd>{f.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {phase.where && (
            <div className="story-where">
              In the product · <strong>{phase.where}</strong>
            </div>
          )}
        </div>

        <Hud id={phase.id} p={vp} />

        <footer className="story-transport">
          <button className="story-btn" onClick={togglePlay} aria-label={playing ? 'Pause' : ended ? 'Replay' : 'Play'}>
            {playing ? <PauseIcon /> : ended ? <ReplayIcon /> : <PlayIcon />}
          </button>
          <button className="story-btn" onClick={() => goto(index - 1)} aria-label="Previous phase" disabled={index === 0}>
            <ChevronIcon dir="left" />
          </button>
          <ol className="story-rail">
            {PHASES.map((ph, i) => {
              const fill = i < index ? 1 : i === index ? p : 0;
              return (
                <li key={ph.id} className={`${i === index ? 'is-active' : ''} story-rail-${ph.stage}`}>
                  <button onClick={() => goto(i)} aria-current={i === index ? 'step' : undefined}>
                    <span className="story-rail-bar">
                      <span style={{ width: `${fill * 100}%` }} />
                    </span>
                    <span className="story-rail-label">{ph.label}</span>
                  </button>
                </li>
              );
            })}
          </ol>
          <button className="story-btn" onClick={() => goto(index + 1)} aria-label="Next phase" disabled={index === PHASES.length - 1}>
            <ChevronIcon dir="right" />
          </button>
          <button className={`story-btn ${soundOn ? 'is-on' : ''}`} onClick={toggleSound} aria-label={soundOn ? 'Sound off' : 'Sound on'} aria-pressed={soundOn}>
            <SoundIcon on={soundOn} />
          </button>
          <label className="story-lite" title="Turn off shadows and post-processing on slower devices">
            <input type="checkbox" checked={lowPower} onChange={(e) => setLowPower(e.target.checked)} /> Lite
          </label>
          <a className="story-skip" href="#evidence">
            Skip to the evidence <span aria-hidden>↓</span>
          </a>
        </footer>
      </section>

      <Evidence />
    </div>
  );
};

function Evidence() {
  return (
    <div className="story-below">
      <section id="evidence" className="story-section">
        <h2>Check every claim in the product</h2>
        <div className="story-grid">
          {[
            ['Extraction', 'Upload a drilling report and watch it become structured events, each linked to its source page.', '/app/documents', 'Document Ingestion'],
            ['Nearby wells', 'Pick a radius. See every offset well on a 2D map or the 3D globe.', '/app/offset-map', 'Offset Map'],
            ['Relevance ranking', 'Five-factor offset ranking with every component score shown.', '/app/wells', 'Nearby Wells'],
            ['Knowledge search', 'Search events, lessons learned and mitigations across all wells.', '/app/knowledge', 'Historical Search'],
            ['Correlation', 'Align wells by formation and depth.', '/app/correlation', 'Geological Correlation'],
            ['Ahead-of-bit alerts', 'Risk projected along the planned path, with recommendations and four-pillar confidence.', '/app/command-center', 'Command Center'],
          ].map(([h, d, href, link]) => (
            <a key={h} className="story-card" href={href}>
              <h3>{h}</h3>
              <p>{d}</p>
              <span>
                {link} <span aria-hidden>↗</span>
              </span>
            </a>
          ))}
        </div>
      </section>
      <section id="how" className="story-section story-how">
        <h2>How it works</h2>
        <ol>
          <li>
            <strong>Ingest.</strong> Reports are parsed (native text or OCR), entities extracted with drilling-domain rules, every value physics-checked.
          </li>
          <li>
            <strong>Connect.</strong> Events are tied to wells, depths and formations, so they can be searched and correlated.
          </li>
          <li>
            <strong>Rank.</strong> Offset wells are scored on distance, formation, depth, trajectory and hazard history.
          </li>
          <li>
            <strong>Project.</strong> Offset-well history is mapped onto the active well’s path ahead of the bit.
          </li>
          <li>
            <strong>Advise.</strong> Alerts carry a recommendation, the supporting evidence and four-pillar confidence.
          </li>
        </ol>
      </section>
      <section id="honesty" className="story-section story-honesty">
        <h2>What is real, and what is simulated</h2>
        <p>
          The story uses the NWIS demo dataset. Well locations, formation tops, the ranking and the risk engine are real code and real output on that data. The
          landscape is real: SRTM-based elevation and Sentinel-2 satellite imagery of the Upper Assam basin and the surrounding Himalaya and Patkai ranges,
          with height exaggerated 3× and depth below ground drawn 3×. The rig is assembled from real drilling-equipment models at true scale, but it is a
          representative rig, not a model of the actual NHK-002 site. Inside the borehole, the formations and their depths are NHK-002’s real tops; the
          rock textures are matched to each lithology, not core photographs from this well. The drilling events and daily drilling reports are a synthetic testbed (each
          report is labelled as such); the pipeline has also been run on 14 real Equinor Volve field documents. Live rig telemetry in the app is a physics
          simulation, not an eRTMAC feed.
        </p>
      </section>
      <footer className="story-foot">
        <span>DrillWise · eRTMAC-NWIS · SIH 26121 · Oil India Limited</span>
        <a href="/app">Open the app ↗</a>
      </footer>
      <p className="story-credits">
        Imagery:{' '}
        <a href="https://s2maps.eu" target="_blank" rel="noreferrer">
          Sentinel-2 cloudless
        </a>{' '}
        by EOX IT Services GmbH (contains modified Copernicus Sentinel data 2016 &amp; 2017), CC BY 4.0. Elevation: AWS Terrain Tiles (Mapzen; sources incl.
        SRTM, NASA/USGS). Rig equipment: “Offshore Oil Rig and Platform” and related packs, 3dassets.dev, CC0. Rock textures: Poly Haven, CC0. Music:{' '}
        <a href="https://www.scottbuckley.com.au" target="_blank" rel="noreferrer">
          ‘Aphelion’ by Scott Buckley
        </a>{' '}
        (www.scottbuckley.com.au), released under{' '}
        <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">
          CC BY 4.0
        </a>
        ; edited for length. Earth day and night maps: the project’s globe textures (public/earth).
      </p>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden>
      <path d="M4 2.5v11l9-5.5z" fill="currentColor" />
    </svg>
  );
}
function PauseIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden>
      <rect x="3.5" y="2.5" width="3" height="11" fill="currentColor" />
      <rect x="9.5" y="2.5" width="3" height="11" fill="currentColor" />
    </svg>
  );
}
function ReplayIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden>
      <path d="M8 3a5 5 0 1 1-4.6 3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M2.5 2.5v4h4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}
function ChevronIcon({ dir }: { dir: 'left' | 'right' }) {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden>
      <path d={dir === 'left' ? 'M10 3 5 8l5 5' : 'M6 3l5 5-5 5'} fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}
function SoundIcon({ on }: { on: boolean }) {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden>
      <path d="M2 6h3l3.5-3v10L5 10H2z" fill="currentColor" />
      {on ? <path d="M11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.6a6 6 0 0 1 0 8.8" fill="none" stroke="currentColor" strokeWidth="1.3" /> : <path d="M11 6l4 4M15 6l-4 4" stroke="currentColor" strokeWidth="1.3" />}
    </svg>
  );
}

export default StoryPage;
