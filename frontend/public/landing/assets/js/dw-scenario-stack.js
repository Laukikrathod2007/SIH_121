// Warm DrillWise port of PetroInnovate's animated depth-log and scenario-panel
// patterns. All readings are explicitly simulated for this landing-page demo.
(function () {
  'use strict';

  function init() {
    var panel = document.querySelector('.dw-live-log');
    if (!panel) return;

    var buttons = panel.querySelectorAll('[data-scenario]');
    var status = panel.querySelector('#dw-live-log-status');
    var eventLabel = panel.querySelector('.dw-log-event-label');
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var tick = 0;
    var scenarioKey = 'drilling';
    var scenarios = {
      drilling: { status: 'SCENARIO 01 / STEADY DRILLING', event: 'ROP · STABLE', phase: 0.15, swing: 1 },
      loss: { status: 'SCENARIO 02 / LOSS-ZONE RESPONSE', event: 'LOSS ZONE · MITIGATION', phase: 1.45, swing: 1.35 },
      stuck: { status: 'SCENARIO 03 / STUCK-PIPE PREVENTION', event: 'TORQUE RISE · WATCH', phase: 2.35, swing: 1.55 },
      kick: { status: 'SCENARIO 04 / KICK & INFLUX WATCH', event: 'FLOW BALANCE · CHECK', phase: 3.2, swing: 1.4 },
      formation: { status: 'SCENARIO 05 / FORMATION CORRELATION', event: 'TIPAM TOP · OFFSET MATCH', phase: 4.1, swing: 0.85 },
      calibration: { status: 'SCENARIO 06 / TWIN CALIBRATION', event: 'TRAJECTORY · ALIGNED', phase: 5.2, swing: 0.7 }
    };

    function selectScenario(key, button) {
      var scenario = scenarios[key];
      if (!scenario) return;
      scenarioKey = key;
      panel.setAttribute('data-scenario', key);
      buttons.forEach(function (item) {
        var active = item === button;
        item.classList.toggle('is-active', active);
        item.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      if (status) status.textContent = scenario.status;
      if (eventLabel) eventLabel.textContent = scenario.event;
      drawLogs();
    }

    function setValue(id, value) {
      var node = panel.querySelector('#' + id);
      if (node && node.firstChild) node.firstChild.nodeValue = value + ' ';
    }

    function drawLogs() {
      var scenario = scenarios[scenarioKey];
      var phase = scenario.phase + tick * 0.095;
      var swing = scenario.swing;
      panel.querySelectorAll('[data-log]').forEach(function (path, channelIndex) {
        var points = 42;
        var d = '';
        for (var i = 0; i < points; i += 1) {
          var y = 8 + i * (154 / (points - 1));
          var wave = Math.sin(i * (0.24 + channelIndex * 0.012) + phase + channelIndex * 0.91) * 0.23;
          var detail = Math.sin(i * 0.57 + phase * 1.55 + channelIndex) * 0.08;
          var x = 12 + (0.5 + (wave + detail) * swing) * 116;
          d += (i ? ' L ' : 'M ') + x.toFixed(1) + ' ' + y.toFixed(1);
        }
        path.setAttribute('d', d);
      });
    }

    function updateTelemetry() {
      if (document.hidden) return;
      tick += 1;
      setValue('dw-live-log-depth', (3202.6 + Math.sin(tick * 0.08) * 2.4).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }));
      setValue('dw-log-rop', (34.2 + Math.sin(tick * 0.31) * 1.1).toFixed(1));
      setValue('dw-log-torque', Math.round(8420 + Math.sin(tick * 0.22) * 145).toLocaleString('en-US'));
      setValue('dw-log-wob', (16.2 + Math.sin(tick * 0.27 + 1) * 0.35).toFixed(1));
      setValue('dw-log-spp', Math.round(2840 + Math.sin(tick * 0.19 + 0.5) * 22).toLocaleString('en-US'));
      setValue('dw-log-ecd', (12.4 + Math.sin(tick * 0.17 + 0.4) * 0.12).toFixed(2));
      setValue('dw-log-vibration', (0.39 + Math.sin(tick * 0.39) * 0.04).toFixed(2));
      drawLogs();
    }

    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        selectScenario(button.getAttribute('data-scenario'), button);
      });
    });

    drawLogs();
    if (!reducedMotion) window.setInterval(updateTelemetry, 1200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
