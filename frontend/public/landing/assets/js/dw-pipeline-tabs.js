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

    function activate(tabId) {
      navItems.forEach(function (el) {
        el.classList.toggle('dw-pt-active', el.getAttribute('data-tab') === tabId);
      });
      figs.forEach(function (el) {
        el.classList.toggle('dw-pt-active', el.getAttribute('data-fig-tab') === tabId);
      });
      caps.forEach(function (el) {
        el.classList.toggle('dw-pt-active', el.getAttribute('data-cap-tab') === tabId);
      });
    }

    navItems.forEach(function (el) {
      el.addEventListener('click', function () {
        activate(el.getAttribute('data-tab'));
      });
    });

    activate('1');
  });
})();
