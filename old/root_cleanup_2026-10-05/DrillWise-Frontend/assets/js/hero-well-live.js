/* Scroll-scrubbed drilling animation for the live-well SVG. */
(function () {
  "use strict";

  var MAX_MD = 4000;
  var START_PROGRESS = 0.62;
  var BREAKOUT_AT_MD = 3100;
  var LOSS_ZONE_AT_MD = 3600;
  var objectEl, pathEl, totalLen, bitInnerG, bitLabel, bitFtEl, alertEl;
  var bhaRoot, holeRoot, lateralHoleEl, cuttingsOutlet, basePoint, baseAngle;
  var pathVertices = [];
  var cuttingsParticles = [], animationStart = 0;
  var currentProgress = START_PROGRESS, targetProgress = START_PROGRESS;
  var autoPlaying = true, frameHandle = 0, initialized = false;
  var wellSection;
  var reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
  function alertFor(md) {
    if (md >= 3300) return "Loss zone 55%";
    if (md >= 2600) return "Breakout risk 70%";
    if (md >= 2480) return "Tight spot detected";
    return "Construction live";
  }
  function svgEl(doc, name) { return doc.createElementNS("http://www.w3.org/2000/svg", name); }
  function getActiveDoc() { return objectEl && objectEl.contentDocument || document; }
  function pointAt(md) {
    if (!pathVertices.length) return pathEl.getPointAtLength(totalLen * clamp(md / MAX_MD, 0, 1));
    var t = clamp(md / MAX_MD, 0, 1) * (pathVertices.length - 1);
    var i = Math.min(Math.floor(t), pathVertices.length - 2), f = t - i;
    var a = pathVertices[i], b = pathVertices[i + 1];
    return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
  }
  function tangentAt(md) {
    var point = pointAt(md);
    var before = pointAt(Math.max(0, md - 12));
    var after = pointAt(Math.min(MAX_MD, md + 12));
    return { point: point, angle: Math.atan2(after.y - before.y, after.x - before.x) * 180 / Math.PI };
  }

  function centerline(fromMD, toMD, step) {
    var points = [];
    if (toMD < fromMD) return points;
    var count = Math.max(2, Math.ceil((toMD - fromMD) / (step || 10)));
    for (var i = 0; i <= count; i++) {
      var md = fromMD + (toMD - fromMD) * i / count;
      var p = pointAt(md); points.push({ md: md, x: p.x, y: p.y });
    }
    return points;
  }

  function tubePath(fromMD, toMD, halfWidth) {
    var points = centerline(fromMD, toMD, 10);
    if (points.length < 2) return "";
    var a = [], b = [];
    points.forEach(function (p, i) {
      var prev = points[Math.max(0, i - 1)], next = points[Math.min(points.length - 1, i + 1)];
      var dx = next.x - prev.x, dy = next.y - prev.y, len = Math.hypot(dx, dy) || 1;
      var nx = -dy / len, ny = dx / len;
      a.push({ x: p.x + nx * halfWidth, y: p.y + ny * halfWidth });
      b.push({ x: p.x - nx * halfWidth, y: p.y - ny * halfWidth });
    });
    return a.concat(b.reverse()).map(function (p, i) {
      return (i ? "L " : "M ") + p.x.toFixed(2) + " " + p.y.toFixed(2);
    }).join(" ") + " Z";
  }

  function addTube(doc, parent, id, fromMD, toMD, radius, fill, stroke, strokeWidth) {
    if (toMD - fromMD < 0.25) return null;
    var d = tubePath(fromMD, toMD, radius);
    if (!d) return null;
    var path = svgEl(doc, "path");
    if (id) path.setAttribute("id", id);
    path.setAttribute("d", d); path.setAttribute("fill", fill); path.setAttribute("stroke", stroke);
    path.setAttribute("stroke-width", String(strokeWidth)); path.setAttribute("stroke-linejoin", "round");
    parent.appendChild(path); return path;
  }

  /* A pipe joint is a short collar across the centerline, oriented to the local tangent. */
  function addJoint(doc, parent, md, across, along, fill, stroke) {
    var p = pointAt(md), t = tangentAt(md), a = t.angle * Math.PI / 180;
    var tx = Math.cos(a), ty = Math.sin(a), nx = -ty, ny = tx;
    var points = [
      { x: p.x + nx * across / 2 + tx * along / 2, y: p.y + ny * across / 2 + ty * along / 2 },
      { x: p.x - nx * across / 2 + tx * along / 2, y: p.y - ny * across / 2 + ty * along / 2 },
      { x: p.x - nx * across / 2 - tx * along / 2, y: p.y - ny * across / 2 - ty * along / 2 },
      { x: p.x + nx * across / 2 - tx * along / 2, y: p.y + ny * across / 2 - ty * along / 2 }
    ];
    var shape = svgEl(doc, "polygon");
    shape.setAttribute("points", points.map(function (v) { return v.x.toFixed(2) + "," + v.y.toFixed(2); }).join(" "));
    shape.setAttribute("fill", fill); shape.setAttribute("stroke", stroke); shape.setAttribute("stroke-width", "0.7");
    parent.appendChild(shape);
  }

  function addComponentGroup(doc, id) {
    var group = svgEl(doc, "g"); group.setAttribute("id", id); bhaRoot.appendChild(group); return group;
  }

  /* Match the live renderer's depth-ordered BHA: 180 ft collars, 5 ft
     stabilizer, 30 ft MWD, 5 ft stabilizer and 210 ft HWDP. Every shell is
     rebuilt from depth samples, so long curved intervals cannot swing outside
     the bore wall as they did when the static group was rigidly rotated. */
  function updateDrillingAssembly(doc, bitMD) {
    bhaRoot.replaceChildren();
    if (lateralHoleEl) {
      if (bitMD > 2500) {
        lateralHoleEl.setAttribute("d", tubePath(2490, bitMD, 16));
        lateralHoleEl.setAttribute("display", "inline");
      } else {
        lateralHoleEl.setAttribute("d", ""); lateralHoleEl.setAttribute("display", "none");
      }
    }

    var collarsBottom = bitMD, collarsTop = Math.max(0, collarsBottom - 180);
    var stab2Bottom = collarsTop, stab2Top = Math.max(0, stab2Bottom - 5);
    var mwdBottom = stab2Top, mwdTop = Math.max(0, mwdBottom - 30);
    var stab1Bottom = mwdTop, stab1Top = Math.max(0, stab1Bottom - 5);
    var hwdpBottom = stab1Top, hwdpTop = Math.max(0, hwdpBottom - 210);

    var pipe = addComponentGroup(doc, "bha-drill-pipe");
    addTube(doc, pipe, null, 0, hwdpTop, 3, "#d1d5db", "#9ca3af", 0.9);
    for (var md = 30; md < hwdpTop; md += 30) addJoint(doc, pipe, md, 8, 4, "#9ca3af", "#6b7280");

    var hwdp = addComponentGroup(doc, "bha-hwdp");
    addTube(doc, hwdp, null, hwdpTop, hwdpBottom, 4, "#b0b8c4", "#6b7280", 0.9);
    for (md = hwdpTop + 15; md < hwdpBottom; md += 30) addTube(doc, hwdp, null, md - 10, md + 10, 6, "#9ca3af", "#4b5563", 0.8);
    for (md = hwdpTop + 30; md < hwdpBottom; md += 30) addJoint(doc, hwdp, md, 8, 4, "#6b7280", "#374151");

    var stab1 = addComponentGroup(doc, "bha-stabilizer-upper");
    var stab1Mid = (stab1Top + stab1Bottom) / 2;
    addTube(doc, stab1, null, stab1Top, stab1Bottom, 3, "#9ca3af", "#6b7280", 0.8);
    addJoint(doc, stab1, stab1Mid, 18, 5, "#6b7280", "#374151");

    var mwd = addComponentGroup(doc, "bha-mwd-lwd");
    addTube(doc, mwd, null, mwdTop, mwdBottom, 5, "#334155", "#475569", 1);
    [mwdTop + (mwdBottom - mwdTop) * 0.25, mwdTop + (mwdBottom - mwdTop) * 0.75].forEach(function (at) {
      var p = pointAt(at), mark = svgEl(doc, "circle");
      mark.setAttribute("cx", p.x.toFixed(2)); mark.setAttribute("cy", p.y.toFixed(2)); mark.setAttribute("r", "1.8");
      mark.setAttribute("fill", "#93c5fd"); mark.setAttribute("stroke", "#0f172a"); mark.setAttribute("stroke-width", "0.7"); mwd.appendChild(mark);
    });

    var stab2 = addComponentGroup(doc, "bha-stabilizer");
    var stab2Mid = (stab2Top + stab2Bottom) / 2;
    addTube(doc, stab2, null, stab2Top, stab2Bottom, 3, "#9ca3af", "#6b7280", 0.8);
    addJoint(doc, stab2, stab2Mid, 18, 5, "#6b7280", "#374151");

    var collars = addComponentGroup(doc, "bha-drill-collars");
    addTube(doc, collars, null, collarsTop, collarsBottom, 5.5, "#4b5563", "#1f2937", 1.1);
    for (md = collarsTop + 30; md < collarsBottom; md += 30) addTube(doc, collars, null, md - 8, md + 8, 7, "#6b7280", "#111827", 0.8);
  }

  function transformAroundPoint(element, targetPoint, targetAngle) {
    element.setAttribute("transform", "translate(" + targetPoint.x.toFixed(2) + " " + targetPoint.y.toFixed(2) + ") " +
      "rotate(" + (targetAngle - baseAngle).toFixed(2) + ") translate(" + (-basePoint.x).toFixed(2) + " " + (-basePoint.y).toFixed(2) + ")");
  }

  function updateCuttings(bitMD) {
    if (!cuttingsParticles.length) return;
    var elapsed = Math.max(0, Date.now() - animationStart), cycle = 7000;
    cuttingsParticles.forEach(function (particle, index) {
      var phase = ((elapsed / cycle) + index / cuttingsParticles.length) % 1;
      var p = pointAt(Math.max(0, bitMD * (1 - phase)));
      particle.setAttribute("cx", p.x.toFixed(2)); particle.setAttribute("cy", p.y.toFixed(2));
    });
  }

  function buildRiskMarker(doc, x, y, color, text) {
    var g = svgEl(doc, "g"), tri = svgEl(doc, "polygon"), leader = svgEl(doc, "polyline");
    tri.setAttribute("points", (x - 11) + "," + (y + 22) + " " + x + "," + y + " " + (x + 11) + "," + (y + 22));
    tri.setAttribute("fill", color); tri.setAttribute("opacity", "0.82");
    leader.setAttribute("points", x + "," + (y + 11) + " " + x + "," + (y + 29) + " " + (x + 36) + "," + (y + 29));
    leader.setAttribute("fill", "none"); leader.setAttribute("stroke", "#888"); leader.setAttribute("stroke-width", "1"); leader.setAttribute("stroke-dasharray", "4 2");
    var bg = svgEl(doc, "rect"); bg.setAttribute("x", x + 32); bg.setAttribute("y", y + 21);
    bg.setAttribute("width", 14 + text.length * 5.6); bg.setAttribute("height", "16"); bg.setAttribute("rx", "4"); bg.setAttribute("fill", "rgba(255,255,255,.88)");
    var label = svgEl(doc, "text"); label.setAttribute("x", x + 36); label.setAttribute("y", y + 34);
    label.setAttribute("font-size", "11"); label.setAttribute("text-anchor", "start"); label.setAttribute("fill", color);
    label.setAttribute("stroke", "white"); label.setAttribute("stroke-width", "3"); label.setAttribute("stroke-linejoin", "round");
    label.setAttribute("style", "paint-order:stroke"); label.textContent = text;
    g.append(tri, leader, bg, label); return g;
  }

  function ensureMarker(doc, id, md, color, text, currentMD) {
    var container = doc.getElementById(id); if (!container) return;
    if (currentMD >= md && !container.childNodes.length) {
      var point = pointAt(md); container.appendChild(buildRiskMarker(doc, point.x, point.y, color, text));
    } else if (currentMD < md && container.childNodes.length) container.replaceChildren();
  }

  function render(progress) {
    var doc = getActiveDoc(), bitMD = progress * MAX_MD;
    var at = tangentAt(bitMD);
    if (bitInnerG) bitInnerG.setAttribute("transform", "translate(" + at.point.x.toFixed(2) + "," + at.point.y.toFixed(2) + ") rotate(" + at.angle.toFixed(2) + ")");
    if (bitLabel) {
      bitLabel.setAttribute("x", (at.point.x + 14).toFixed(2)); bitLabel.setAttribute("y", (at.point.y - 14).toFixed(2));
      bitLabel.textContent = "Bit - " + Math.round(bitMD).toLocaleString() + " ft";
    }
    updateDrillingAssembly(doc, bitMD);
    if (cuttingsOutlet) transformAroundPoint(cuttingsOutlet, at.point, at.angle);
    updateCuttings(bitMD);
    if (bitFtEl) bitFtEl.textContent = Math.round(bitMD).toLocaleString();
    if (alertEl) alertEl.textContent = alertFor(bitMD);
    ensureMarker(doc, "breakout-markers", BREAKOUT_AT_MD, "#9a3412", "Breakout 70%", bitMD);
    ensureMarker(doc, "loss-zone-shapes", LOSS_ZONE_AT_MD, "#a16207", "Loss zone 55%", bitMD);
  }

  function scrollProgress() {
    if (!wellSection) return 0;
    var raw = clamp(-wellSection.getBoundingClientRect().top / Math.max(1, wellSection.offsetHeight * 0.85), 0, 1);
    return START_PROGRESS + raw * (1 - START_PROGRESS);
  }

  function tick() {
    if (!initialized) return;
    if (autoPlaying) {
      /* The live well starts at the 2,500-ft shoe and drills through the
         lateral. Previously this auto phase stopped exactly at 2,480 ft,
         leaving the part that needs to be demonstrated beyond the shoe
         reachable only by scrolling. */
      currentProgress = Math.min(1, currentProgress + 0.00028);
      targetProgress = currentProgress;
      if (currentProgress >= 1) {
        autoPlaying = false;
        targetProgress = 1;
      }
    } else {
      currentProgress += (targetProgress - currentProgress) * 0.045;
    }
    render(currentProgress);
    frameHandle = window.requestAnimationFrame(tick);
  }

  function onScroll() {
    if (reducedMotion) return;
    autoPlaying = false;
    targetProgress = scrollProgress();
  }

  function ready() {
    if (initialized) return;
    var doc = getActiveDoc();
    var pathWrap = doc.getElementById("planned-well-path");
    pathEl = pathWrap && pathWrap.querySelector("path");
    var bitMarker = doc.getElementById("bit-marker");
    bitInnerG = bitMarker && bitMarker.querySelector("g");
    bitLabel = bitMarker && bitMarker.querySelector(":scope > text");
    bhaRoot = doc.getElementById("bha-components");
    holeRoot = doc.getElementById("wellbore-hole-shapes");
    cuttingsOutlet = doc.getElementById("cuttings-outlet");
    var cuttingsRoot = doc.getElementById("cuttings-flow");
    cuttingsParticles = cuttingsRoot ? Array.prototype.slice.call(cuttingsRoot.children).filter(function (child) {
      return child.tagName && child.tagName.toLowerCase() === "circle" && child.querySelector("animateMotion");
    }) : [];
    cuttingsParticles.forEach(function (particle) {
      Array.prototype.slice.call(particle.children).forEach(function (animation) {
        if (animation.tagName.toLowerCase() === "animatemotion") particle.removeChild(animation);
      });
    });
    if (!pathEl || !bitInnerG) { window.setTimeout(ready, 150); return; }
    totalLen = pathEl.getTotalLength();
    var raw = (pathEl.getAttribute("d") || "").match(/[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g) || [];
    pathVertices = [];
    for (var v = 0; v + 1 < raw.length; v += 2) pathVertices.push({ x: Number(raw[v]), y: Number(raw[v + 1]) });
    if (pathVertices.length < 2) pathVertices = [];
    if (holeRoot && !doc.getElementById("dw-active-lateral-hole")) {
      lateralHoleEl = svgEl(doc, "path"); lateralHoleEl.setAttribute("id", "dw-active-lateral-hole");
      lateralHoleEl.setAttribute("fill", "#ecebea"); lateralHoleEl.setAttribute("stroke", "#7c7c7c");
      lateralHoleEl.setAttribute("stroke-width", "1.3"); lateralHoleEl.setAttribute("stroke-linejoin", "round");
      lateralHoleEl.setAttribute("display", "none"); holeRoot.appendChild(lateralHoleEl);
    } else if (holeRoot) lateralHoleEl = doc.getElementById("dw-active-lateral-hole");
    if (!bhaRoot) { window.setTimeout(ready, 150); return; }
    basePoint = pointAt(2500); baseAngle = tangentAt(2500).angle;
    /* Drive the well drawing from the section that actually contains it.
       Using #ahead-of-the-bit (the next section) made scroll depth depend on
       that unrelated panel's height, so the bit could never reach the end of
       the trajectory while the hero was on screen. */
    var wellContainer = document.getElementById("dw-hero-well-container");
    wellSection = (wellContainer && wellContainer.closest("section")) ||
      document.querySelector("[data-twin-workflow]");
    animationStart = Date.now(); initialized = true;
    currentProgress = START_PROGRESS;
    targetProgress = currentProgress;
    if (reducedMotion) render(currentProgress);
    else { window.addEventListener("scroll", onScroll, { passive: true }); frameHandle = window.requestAnimationFrame(tick); }
    if (reducedMotion) window.addEventListener("scroll", function () { targetProgress = scrollProgress(); currentProgress = targetProgress; render(currentProgress); }, { passive: true });
  }

  function init() {
    objectEl = document.getElementById("dw-hero-well-object");
    bitFtEl = document.getElementById("dw-hero-bit-ft"); alertEl = document.getElementById("dw-hero-alert");
    if (objectEl && objectEl.tagName.toLowerCase() === "object") {
      if (objectEl.contentDocument && objectEl.contentDocument.readyState === "complete") ready();
      else objectEl.addEventListener("load", ready);
    } else ready();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
