import React, { useCallback, useEffect, useRef, useState } from 'react';

// Opening of /story, in two steps:
//   1. The DrillWise loading animation (public/story/loading_animation.mp4,
//      10 s, 1280x720) plays muted (browsers block autoplay with sound),
//      from start to end. While it plays, the 3D world loads behind it.
//   2. A choice screen in the project's terms (PS 26121): what the next
//      67 seconds show, and how to watch: with sound, without, or straight
//      to the evidence below.
// onStart(sound) hands control to the story.

type Step = 'video' | 'choice' | 'done';

export function Intro({ onStart, ready }: { onStart: (withSound: boolean) => void; ready: boolean }) {
  const [step, setStep] = useState<Step>('video');
  const [fading, setFading] = useState(false);
  const video = useRef<HTMLVideoElement>(null);

  const toChoice = useCallback(() => {
    setFading(true);
    window.setTimeout(() => {
      setStep('choice');
      setFading(false);
    }, 650);
  }, []);

  // The opening plays from start to end. It is muted, which browsers allow
  // to autoplay; if a browser still refuses, retry on the first click or
  // key press instead of skipping it. A stalled network still can't hold
  // the page forever: after the video's length plus a margin, go on.
  const [needTap, setNeedTap] = useState(false);
  useEffect(() => {
    const v = video.current;
    if (!v) return;
    const tryPlay = () =>
      v.play().then(
        () => setNeedTap(false),
        () => setNeedTap(true),
      );
    tryPlay();
    const retry = () => {
      if (v.paused) tryPlay();
    };
    window.addEventListener('pointerdown', retry);
    window.addEventListener('keydown', retry);
    const guard = window.setTimeout(() => {
      if (v.paused || v.readyState < 2) toChoice();
    }, 25000);
    return () => {
      window.removeEventListener('pointerdown', retry);
      window.removeEventListener('keydown', retry);
      window.clearTimeout(guard);
    };
  }, [toChoice]);

  const start = useCallback(
    (withSound: boolean) => {
      setFading(true);
      window.setTimeout(() => {
        setStep('done');
        onStart(withSound);
      }, 600);
    },
    [onStart],
  );

  if (step === 'done') return null;

  return (
    <div className={`intro ${fading ? 'intro-out' : ''} ${step === 'video' ? 'intro-video-step' : 'intro-choice-step'}`}>
      {step === 'video' && (
        <>
          <video
            ref={video}
            className="intro-video"
            src="/story/loading_animation.mp4"
            muted
            playsInline
            preload="auto"
            onEnded={toChoice}
            onError={toChoice}
            aria-label="DrillWise opening animation"
          />
          {needTap && <div className="intro-loading intro-tap">Click anywhere to play</div>}
        </>
      )}

      {step === 'choice' && (
        <div className="intro-choice" role="dialog" aria-labelledby="intro-title">
          <div className="intro-kicker">SIH 2026 · PS 26121 · OIL INDIA LIMITED</div>
          <h1 id="intro-title" className="intro-title">
            BEFORE THE BIT GETS THERE
          </h1>
          <p className="intro-lead">
            Sixty-seven seconds. One active well in Upper Assam, eleven offset wells around it, and one kick in the Kopili that was already in the
            reports. How DrillWise reads the history, finds the wells that matter, and warns the driller ahead of the bit.
          </p>
          <ul className="intro-chapters" aria-label="What you will see">
            <li>
              <b>Problem</b> The history is buried in reports
            </li>
            <li>
              <b>Solution</b> Extract · map · rank · correlate · look ahead
            </li>
            <li>
              <b>Outcome</b> An alert the engineer can act on, and check
            </li>
          </ul>
          <div className="intro-actions">
            <button className="intro-primary" onClick={() => start(true)} disabled={!ready} autoFocus>
              <SoundIcon /> Begin with sound
            </button>
            <button className="intro-secondary" onClick={() => start(false)} disabled={!ready}>
              Watch without sound
            </button>
          </div>
          <a className="intro-evidence" href="#evidence" onClick={() => start(false)}>
            Or skip to the evidence <span aria-hidden>↓</span>
          </a>
          {!ready && <div className="intro-loading">Loading the basin…</div>}
        </div>
      )}
    </div>
  );
}

function SoundIcon() {
  return (
    <svg viewBox="0 0 16 16" width="15" height="15" aria-hidden>
      <path d="M2 6h3l3.5-3v10L5 10H2z" fill="currentColor" />
      <path d="M11 5.5a3.5 3.5 0 0 1 0 5M12.8 3.6a6 6 0 0 1 0 8.8" fill="none" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}
