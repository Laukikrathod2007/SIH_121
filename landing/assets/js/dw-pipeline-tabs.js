// Click-to-switch tabs for the Data Extraction pipeline showcase.
// Deliberately click-driven, not scroll-synced -- a sticky scroll-spy
// pattern is easy to get subtly wrong without ever seeing it render, and
// a reliable click interaction beats a possibly-broken scroll one.
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
    var root = document.querySelector('.dw-pipeline-tabs');
    if (!root) return;

    var navItems = root.querySelectorAll('[data-tab]');
    var figs = root.querySelectorAll('[data-fig-tab]');
    var caps = root.querySelectorAll('[data-cap-tab]');
    var nav = navItems.length ? navItems[0].parentElement : null;
    var figureColumn = figs.length ? figs[0].parentElement : null;
    var summary = null;
    var stages = {
      '1': { asset: 'native-text-layer.svg', alt: 'A born-digital drilling report is read directly from its text layer.' },
      '2': { asset: 'native-text-layer.svg', alt: 'A scanned drilling report is read with layout-aware OCR.' },
      '3': { asset: 'structured-field-extract.svg', alt: 'Formation tops, mud weights, events, and NPT are mapped into structured drilling fields.' },
      '4': { asset: 'physics-validation.svg', alt: 'Extracted drilling values are checked against units, depth ranges, and operational limits.' },
      '5': { asset: 'operator-template-learn.svg', alt: 'The operator report layout is learned to speed up the next report.' }
    };

    if (nav) nav.setAttribute('role', 'tablist');
    if (figureColumn) {
      summary = document.createElement('p');
      summary.className = 'dw-pt-active-summary';
      summary.setAttribute('aria-live', 'polite');
      summary.setAttribute('aria-atomic', 'true');
      figureColumn.insertBefore(summary, figureColumn.firstChild);
    }

    navItems.forEach(function (el, index) {
      el.setAttribute('role', 'tab');
      el.setAttribute('aria-controls', 'dw-pipeline-figure-' + el.getAttribute('data-tab'));
      el.setAttribute('tabindex', index === 0 ? '0' : '-1');
    });
    figs.forEach(function (el) {
      var stage = stages[el.getAttribute('data-fig-tab')];
      if (stage) {
        el.innerHTML = '<div class="dw-processor-visual" role="img" aria-label="' + stage.alt + '">' +
          '<img src="assets/images/processor/' + stage.asset + '" alt="" loading="lazy">' +
          '</div>';
      }
      el.id = 'dw-pipeline-figure-' + el.getAttribute('data-fig-tab');
      el.setAttribute('role', 'tabpanel');
      el.setAttribute('tabindex', '0');
    });

    function activate(tabId) {
      navItems.forEach(function (el) {
        var active = el.getAttribute('data-tab') === tabId;
        el.classList.toggle('dw-pt-active', active);
        el.setAttribute('aria-selected', active ? 'true' : 'false');
        el.setAttribute('tabindex', active ? '0' : '-1');
        if (active && summary) {
          var description = el.querySelector('.dw-pt-desc');
          summary.textContent = description ? description.textContent.trim() : '';
        }
      });
      figs.forEach(function (el) {
        var active = el.getAttribute('data-fig-tab') === tabId;
        el.classList.toggle('dw-pt-active', active);
        el.setAttribute('aria-hidden', active ? 'false' : 'true');
      });
      caps.forEach(function (el) {
        var active = el.getAttribute('data-cap-tab') === tabId;
        el.classList.toggle('dw-pt-active', active);
        el.setAttribute('aria-hidden', active ? 'false' : 'true');
      });
    }

    navItems.forEach(function (el) {
      el.addEventListener('click', function () {
        activate(el.getAttribute('data-tab'));
      });
      el.addEventListener('keydown', function (event) {
        var current = Array.prototype.indexOf.call(navItems, el);
        var next = current;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (current + 1) % navItems.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (current - 1 + navItems.length) % navItems.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = navItems.length - 1;
        else return;
        event.preventDefault();
        navItems[next].focus();
        activate(navItems[next].getAttribute('data-tab'));
      });
    });

    activate('1');
  });
})();
