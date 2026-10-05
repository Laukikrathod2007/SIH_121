// DrillWise scroll-reveal + count-up. Purely additive: assigns classes and
// observes elements at runtime instead of editing the existing markup, so
// every other file on this page stays untouched. Safe to delete this single
// <script> tag to fully disable with zero side effects elsewhere.
(function () {
  'use strict';

  function onReady(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  onReady(function () {
    var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- Section fade-up reveal -------------------------------------------
    var revealTargets = [];
    document.querySelectorAll('#capabilities > .mx-auto > div[id]').forEach(function (el) {
      revealTargets.push(el);
    });
    ['historical-extraction', 'technical-foundation', 'dashboard', 'benchmark-reports'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) revealTargets.push(el);
    });

    if (prefersReduced || !('IntersectionObserver' in window)) {
      // No animation support / explicit user preference: leave everything
      // at full visibility, skip the observer entirely.
    } else {
      revealTargets.forEach(function (el) {
        el.classList.add('dw-reveal');
      });
      var sectionObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              entry.target.classList.add('dw-in-view');
              sectionObserver.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.12, rootMargin: '0px 0px -60px 0px' }
      );
      revealTargets.forEach(function (el) {
        sectionObserver.observe(el);
      });
    }

    // --- Count-up for plain integer / percentage stat numbers -------------
    // Only touches text matching ^\d+%?$ -- anything else (e.g. "98/100",
    // "0.661 AUC") is left exactly as authored, no parsing risk.
    // #dashboard is the aggregate-stats block, now on its own page
    // (benchmarks.html) since the benchmarks content moved off the single
    // combined landing page -- this script tag ships on both pages, so
    // the selector just needs to match wherever that block actually is.
    var statSelectors = [
      '#dashboard .text-4xl',
      '#dashboard .text-5xl',
      '#dashboard .text-2xl.font-bold',
    ];
    var statEls = document.querySelectorAll(statSelectors.join(', '));
    var countTargets = [];
    statEls.forEach(function (el) {
      var raw = el.textContent.trim();
      var match = raw.match(/^(\d+)(%?)$/);
      if (match) {
        countTargets.push({ el: el, value: parseInt(match[1], 10), suffix: match[2] });
      }
    });

    if (prefersReduced || !('IntersectionObserver' in window) || countTargets.length === 0) {
      return;
    }

    function animateCount(target) {
      var el = target.el;
      var end = target.value;
      var suffix = target.suffix;
      var duration = 900;
      var start = null;

      function step(timestamp) {
        if (start === null) start = timestamp;
        var progress = Math.min((timestamp - start) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = Math.round(eased * end);
        el.textContent = current + suffix;
        if (progress < 1) {
          window.requestAnimationFrame(step);
        } else {
          el.textContent = end + suffix;
        }
      }
      window.requestAnimationFrame(step);
    }

    var countObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            var target = countTargets.find(function (t) {
              return t.el === entry.target;
            });
            if (target) animateCount(target);
            countObserver.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );
    countTargets.forEach(function (t) {
      countObserver.observe(t.el);
    });
  });
})();
