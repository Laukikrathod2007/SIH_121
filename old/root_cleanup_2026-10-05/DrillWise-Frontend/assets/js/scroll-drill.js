/*
 * DrillWise scroll-linked wellbore visualizer.
 *
 * Rebuilt (not ported) from the scroll->depth mechanism observed in the
 * petroinnovate reference site: a single rAF loop reads window.scrollY,
 * smooths it, eases it, and maps it to a "bit depth" plus a set of
 * casing-string reveal fractions. Recolored to the DrillWise
 * cream/graphite/orange palette instead of petroinnovate's dark/cyan one.
 */
(function () {
  "use strict";

  var MAX_DEPTH = 22500;
  var START_DEPTH = 0;
  var HERO_PHASE_THRESHOLD = 0.12;
  var SMOOTHING = 0.12;

  var CASING = [
    { id: "conductor",    label: "36\"",       topFt: 0,     shoeFt: 1200,  halfWidth: 22,   revealAt: 0,    revealWindow: 0.02 },
    { id: "surface",      label: "20\"",       topFt: 0,     shoeFt: 4800,  halfWidth: 17.5, revealAt: 0,    revealWindow: 0.04 },
    { id: "intermediate", label: "13⅜\"", topFt: 0,     shoeFt: 11200, halfWidth: 13,   revealAt: 0.02, revealWindow: 0.08 },
    { id: "production",   label: "9⅝\"",  topFt: 0,     shoeFt: 18000, halfWidth: 9,    revealAt: 0.36, revealWindow: 0.14 },
    { id: "liner",        label: "7\" liner",  topFt: 17500, shoeFt: 22000, halfWidth: 6.5,  revealAt: 0.72, revealWindow: 0.12 }
  ];

  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function easeInOutCubic(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function fmt(n) { return Math.round(n).toLocaleString(); }

  var state = {
    progress: 0,
    smooth: 0,
    bitFt: START_DEPTH,
    velocity: 0,
    phase: "hero",
    casingReveal: CASING.map(function () { return 0; })
  };

  var lastT = 0;
  var lastY = 0;
  var started = false;
  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // --- SVG geometry ---------------------------------------------------
  // Wider viewBox than the panel's rendered width so casing tubes read as
  // visible nested pipes instead of hairlines once scaled down.
  var VB_W = 220;
  var VB_H = 760;
  var CX = VB_W / 2;
  var TOP_Y = 44;
  var BOTTOM_Y = 736;
  var HALFWIDTH_SCALE = 1.55; // inches -> px at viewBox scale

  function depthToY(ft) {
    return TOP_Y + clamp01(ft / MAX_DEPTH) * (BOTTOM_Y - TOP_Y);
  }

  // --- DOM refs ---------------------------------------------------------
  var els = {};

  function cacheEls() {
    els.rulerDot = document.getElementById("dw-ruler-dot");
    els.hudScr = document.getElementById("dw-hud-scr");
    els.hudPh = document.getElementById("dw-hud-ph");
    els.hudBit = document.getElementById("dw-hud-bit");
    els.hudTvd = document.getElementById("dw-hud-tvd");
    els.hudV = document.getElementById("dw-hud-v");
    els.bitGroup = document.getElementById("dw-bit-group");
    els.bitLabel = document.getElementById("dw-bit-label");
    els.drillString = document.getElementById("dw-drillstring");
    els.holeGuide = document.getElementById("dw-hole-guide");
    els.casingLayer = document.getElementById("dw-casing-layer");
    return !!(els.bitGroup && els.casingLayer);
  }

  function buildCasingElements() {
    els.casingLayer.innerHTML = "";
    els.casingEls = CASING.map(function (c) {
      var halfPx = c.halfWidth * HALFWIDTH_SCALE;
      var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("data-casing", c.id);
      g.setAttribute("opacity", "0");

      var left = document.createElementNS("http://www.w3.org/2000/svg", "line");
      var right = document.createElementNS("http://www.w3.org/2000/svg", "line");
      left.setAttribute("x1", CX - halfPx);
      left.setAttribute("x2", CX - halfPx);
      right.setAttribute("x1", CX + halfPx);
      right.setAttribute("x2", CX + halfPx);
      [left, right].forEach(function (line) {
        line.setAttribute("stroke", "#8a8580");
        line.setAttribute("stroke-width", "3.4");
        line.setAttribute("stroke-linecap", "round");
      });

      var shoe = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      shoe.setAttribute("r", "3.2");
      shoe.setAttribute("fill", "#c96a12");

      g.appendChild(left);
      g.appendChild(right);
      g.appendChild(shoe);
      els.casingLayer.appendChild(g);
      return { def: c, g: g, left: left, right: right, shoe: shoe, halfPx: halfPx };
    });
  }

  function render() {
    var pct = (state.smooth * 100).toFixed(1);

    if (els.rulerDot) els.rulerDot.style.top = pct + "%";
    if (els.hudScr) els.hudScr.textContent = pct + "%";
    if (els.hudPh) els.hudPh.textContent = state.phase.toUpperCase();
    if (els.hudBit) els.hudBit.textContent = fmt(state.bitFt) + " FT";
    if (els.hudTvd) els.hudTvd.textContent = fmt(state.bitFt) + " FT";
    if (els.hudV) els.hudV.textContent = state.velocity.toFixed(2);

    var bitY = depthToY(state.bitFt);
    if (els.bitGroup) {
      els.bitGroup.setAttribute("transform", "translate(" + CX + "," + bitY + ")");
    }
    if (els.bitLabel) {
      els.bitLabel.textContent = fmt(state.bitFt) + " ft";
    }
    if (els.drillString) {
      els.drillString.setAttribute("y1", TOP_Y);
      els.drillString.setAttribute("y2", bitY);
    }

    if (els.casingEls) {
      els.casingEls.forEach(function (c, i) {
        var reveal = state.casingReveal[i];
        var visible = reveal > 0.001;
        c.g.setAttribute("opacity", Math.min(1, reveal * 1.4).toFixed(2));
        if (!visible) return;
        var bottomFt = c.def.topFt + (c.def.shoeFt - c.def.topFt) * reveal;
        var topY = depthToY(c.def.topFt);
        var bottomY = depthToY(bottomFt);

        c.left.setAttribute("y1", topY);
        c.left.setAttribute("y2", bottomY);
        c.right.setAttribute("y1", topY);
        c.right.setAttribute("y2", bottomY);

        var atShoe = reveal > 0.97;
        c.shoe.setAttribute("cx", CX);
        c.shoe.setAttribute("cy", bottomY);
        c.shoe.setAttribute("opacity", atShoe ? "1" : "0.9");
        c.shoe.setAttribute("r", atShoe ? "3.2" : "2.4");
      });
    }
  }

  function tick() {
    var docH = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    var y = window.scrollY;
    var now = performance.now();
    var dt = Math.max(1, now - lastT);
    var vel = Math.abs(y - lastY) / dt;

    state.velocity = state.velocity * 0.82 + vel * 0.18;
    lastY = y;
    lastT = now;

    var raw = clamp01(y / docH);
    state.progress = raw;
    state.smooth += (raw - state.smooth) * SMOOTHING;

    var eased = easeInOutCubic(state.smooth);
    state.bitFt = START_DEPTH + eased * (MAX_DEPTH - START_DEPTH);
    state.phase = state.smooth < HERO_PHASE_THRESHOLD ? "hero" : "construction";

    for (var i = 0; i < CASING.length; i++) {
      var c = CASING[i];
      state.casingReveal[i] = clamp01((state.smooth - c.revealAt) / c.revealWindow);
    }

    render();
    requestAnimationFrame(tick);
  }

  function start() {
    if (started) return;
    if (!cacheEls()) return;
    started = true;
    buildCasingElements();
    lastT = performance.now();
    lastY = window.scrollY;

    if (reducedMotion) {
      state.progress = 1;
      state.smooth = 1;
      state.bitFt = MAX_DEPTH;
      state.phase = "construction";
      state.casingReveal = CASING.map(function (c) { return c.revealAt < HERO_PHASE_THRESHOLD ? 1 : 0; });
      render();
      return;
    }
    requestAnimationFrame(tick);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
