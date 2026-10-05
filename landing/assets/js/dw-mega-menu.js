// Desktop "Modules" mega-menu. The original markup here was extracted from
// a server-rendered React page built on Radix UI menu primitives; after two
// rounds of CSS patches on that inherited structure still left every click
// landing on the wrong destination (the panel's grid was overflowing its
// real container -- which also included a decorative image column eating
// into the width -- so clicks were resolving to whatever sat physically
// next to the spilled-over menu instead of the item actually under the
// cursor), the panel was rebuilt from scratch as plain, self-contained
// markup with inline styles and no Tailwind-class dependency at all. This
// just does a simple show/hide on two fixed ids.
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
    var trigger = document.getElementById('dw-modules-trigger');
    var panel = document.getElementById('dw-modules-panel');

    if (trigger && panel) {
      var closeTimer = null;
      var chevron = trigger.querySelector('svg');
      trigger.setAttribute('aria-controls', 'dw-modules-panel');
      trigger.setAttribute('aria-expanded', 'false');

      function isOpen() {
        return panel.style.display === 'block';
      }

      function open() {
        clearTimeout(closeTimer);
        panel.style.display = 'block';
        trigger.setAttribute('aria-expanded', 'true');
        if (chevron) chevron.style.transform = 'rotate(180deg)';
      }

      function close() {
        panel.style.display = 'none';
        trigger.setAttribute('aria-expanded', 'false');
        if (chevron) chevron.style.transform = '';
      }

      function scheduleClose() {
        clearTimeout(closeTimer);
        closeTimer = setTimeout(close, 150);
      }

      trigger.addEventListener('mouseenter', open);
      trigger.addEventListener('mouseleave', scheduleClose);
      panel.addEventListener('mouseenter', function () {
        clearTimeout(closeTimer);
      });
      panel.addEventListener('mouseleave', scheduleClose);

      panel.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', close);
      });

      trigger.addEventListener('focus', open);
      trigger.addEventListener('click', function (e) {
        e.preventDefault();
        if (isOpen()) {
          close();
        } else {
          open();
        }
      });

      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && isOpen()) {
          close();
          trigger.focus();
        }
      });

      document.addEventListener('click', function (e) {
        if (!trigger.contains(e.target) && !panel.contains(e.target)) {
          close();
        }
      });
    }

    // Mobile slide-down menu: same lost-React-interactivity problem as the
    // desktop mega-menu above, fixed the same way -- plain DOM events
    // driving a class the CSS (.dw-mobile-nav-open) already knows how to
    // animate.
    var mobileWrapper = document.querySelector('.z-navbar-mobile-menu');
    var mobileToggle = document.querySelector('[aria-label="Open menu"]');
    if (mobileWrapper && mobileToggle) {
      function openMobile() {
        mobileWrapper.classList.add('dw-mobile-nav-open');
        mobileToggle.setAttribute('aria-expanded', 'true');
        mobileToggle.setAttribute('aria-label', 'Close menu');
      }
      function closeMobile() {
        mobileWrapper.classList.remove('dw-mobile-nav-open');
        mobileToggle.setAttribute('aria-expanded', 'false');
        mobileToggle.setAttribute('aria-label', 'Open menu');
      }
      mobileToggle.addEventListener('click', function () {
        if (mobileWrapper.classList.contains('dw-mobile-nav-open')) {
          closeMobile();
        } else {
          openMobile();
        }
      });
      mobileWrapper.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', closeMobile);
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeMobile();
      });
    }
  });
})();
