import React from 'react';
import { CUES, EVIDENCE_CARD, KOPILI_TOP_MD, bitMd, blackout, cueOpacity, isSilence, showDepthHud, smoothstep, type Cue } from './timeline';
import { formationAt } from './textures';

// Everything drawn over the 3D picture: letterbox, black frames, text,
// the depth readout and the evidence document. Pure function of `t`.

const LETTERBOX_RATIO = 2.39;

function CueText({ cue, t }: { cue: Cue; t: number }) {
  const o = cueOpacity(t, cue.start, cue.end, cue.style === 'title' ? 0.6 : 0.9);
  if (o <= 0.001) return null;
  // Lines drift up a few pixels as they appear: slow, never bouncy.
  const rise = (1 - smoothstep(cue.start, cue.start + 2.2, t)) * 6;
  const base: React.CSSProperties = { opacity: o, transform: `translateY(${rise}px)` };

  switch (cue.style) {
    case 'line':
      return (
        <div className="film-cue film-cue-line" style={base}>
          {cue.text}
        </div>
      );
    case 'hud':
      return (
        <div className="film-cue film-cue-hud" style={base}>
          {cue.text}
        </div>
      );
    case 'title':
      return (
        <div className="film-cue film-cue-title" style={{ opacity: o, letterSpacing: `${0.42 + smoothstep(cue.start, cue.end, t) * 0.12}em` }}>
          {cue.text}
        </div>
      );
    case 'alert':
      return (
        <div className="film-cue film-cue-alert" style={base}>
          <div className="film-alert-head">
            <span className="film-alert-dot" />
            {cue.text}
          </div>
          {cue.sub && <div className="film-alert-sub">{cue.sub}</div>}
        </div>
      );
    case 'decision':
      return (
        <div className="film-cue film-cue-decision" style={base}>
          {cue.text}
        </div>
      );
    case 'quote':
      return (
        <div className="film-cue film-cue-quote" style={base}>
          <div>{cue.text}</div>
          {cue.sub && <div className="film-quote-sub">{cue.sub}</div>}
        </div>
      );
    case 'brand':
      return (
        <div className="film-cue film-cue-brand" style={{ opacity: o }}>
          <img src="/brand/drillwise-icon-mark.png" alt="" className="film-brand-mark" />
          <span>{cue.text}</span>
        </div>
      );
    case 'tagline':
      return (
        <div className="film-cue film-cue-tagline" style={base}>
          {cue.text}
        </div>
      );
    case 'note':
      return (
        <div className="film-cue film-cue-note" style={{ opacity: o * 0.8 }}>
          {cue.text}
        </div>
      );
  }
}

/** The offset well's own report, as the system surfaced it. */
function EvidenceCard({ t }: { t: number }) {
  const o = cueOpacity(t, EVIDENCE_CARD.start, EVIDENCE_CARD.end, 1.0);
  if (o <= 0.001) return null;
  // The highlighted sentence "writes in" as if the system is finding it.
  const hl = smoothstep(EVIDENCE_CARD.start + 1.2, EVIDENCE_CARD.start + 2.6, t);
  const slide = (1 - smoothstep(EVIDENCE_CARD.start, EVIDENCE_CARD.start + 1.6, t)) * 18;
  return (
    <div className="film-evidence" style={{ opacity: o, transform: `translateX(${slide}px)` }}>
      <div className="film-evidence-tag">OFFSET WELL REPORT · SOURCE PDF · PAGE 2 OF 3</div>
      <div className="film-evidence-head">
        <div>Daily Drilling Report · BGJ-007</div>
        <div className="film-evidence-meta">Baghjan field · 26.9 km from the active well</div>
      </div>
      <div className="film-evidence-body">
        <span className="film-evidence-label">OPERATIONS / INCIDENT</span>
        <p>
          <mark style={{ backgroundSize: `${hl * 100}% 100%` }}>
            Kick at 2905.3 m MD (Kopili). Pit gain of 25 bbls observed while drilling Kopili.
          </mark>{' '}
          Shut in BOP. SICP 249 psi, SIDPP 541 psi. Killed using Driller’s Method in 2.7 hrs.
        </p>
        <span className="film-evidence-label">LESSON LEARNED</span>
        <p>Weighted up mud to kill weight. Well killed successfully; drilling resumed.</p>
      </div>
      <div className="film-evidence-foot">Synthetic demo document · NWIS testbed</div>
    </div>
  );
}

function DepthReadout({ t }: { t: number }) {
  if (!showDepthHud(t)) return null;
  const md = bitMd(t);
  const f = formationAt(md);
  const near = md > KOPILI_TOP_MD - 60;
  const silent = isSilence(t);
  return (
    <div className={`film-depth ${near ? 'film-depth-near' : ''} ${silent ? 'film-depth-silent' : ''}`}>
      <div className="film-depth-label">BIT DEPTH · MD</div>
      <div className="film-depth-value">
        {md.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}
        <span> m</span>
      </div>
      <div className="film-depth-formation">{f.name}</div>
    </div>
  );
}

export function Overlay({ t, width, height }: { t: number; width: number; height: number }) {
  const bar = Math.max(0, (height - width / LETTERBOX_RATIO) / 2);
  const black = blackout(t);
  return (
    <div className="film-overlay">
      <div className="film-black" style={{ opacity: black }} />
      <div className="film-frame" style={{ top: bar, bottom: bar }}>
        <DepthReadout t={t} />
        <EvidenceCard t={t} />
        {CUES.map((c, i) => (
          <CueText key={i} cue={c} t={t} />
        ))}
      </div>
      <div className="film-bar" style={{ top: 0, height: bar }} />
      <div className="film-bar" style={{ bottom: 0, height: bar }} />
    </div>
  );
}
