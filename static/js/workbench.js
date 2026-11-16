/*
 * MedStep — Gram Staining Workbench controls.
 *
 * A reagent stays "on the slide" (timer running) until it is rinsed with
 * distilled water or replaced by another reagent. Each finished exposure is
 * recorded as {reagent, seconds}; the list is posted as JSON for server-side
 * grading.
 */
(function () {
  'use strict';

  var configEl = document.getElementById('workbench-config');
  var chemistry = window.MedStepChemistry;
  if (!configEl || !chemistry) { return; }

  var config = JSON.parse(configEl.textContent);
  var MAX_STEPS = 50;
  var MAX_SECONDS = 900;
  var RINSE_SECONDS = 5;
  var FAST_FORWARD_SECONDS = 10;
  var TICK_MS = 100;

  var slide = document.getElementById('bench-slide');
  var cells = slide.querySelector('.ms-cells');
  var wash = slide.querySelector('[data-role="wash"]');
  var timerEl = document.getElementById('exposureTimer');
  var currentEl = document.getElementById('currentReagent');
  var fastForwardBtn = document.getElementById('fastForward');
  var resetBtn = document.getElementById('resetBench');
  var submitBtn = document.getElementById('submitAttempt');
  var stepsInput = document.getElementById('stepsInput');
  var form = document.getElementById('submitForm');
  var logEl = document.getElementById('stepLog');
  var rackButtons = Array.prototype.slice.call(document.querySelectorAll('[data-reagent]'));

  var steps = [];      // finished exposures
  var active = null;   // {reagent, startedAt, bonus} while a reagent is on the slide
  var submitting = false;
  var washTimeout = null;

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------
  function round1(value) { return Math.round(value * 10) / 10; }

  function activeSeconds() {
    if (!active) { return 0; }
    var seconds = (performance.now() - active.startedAt) / 1000 + active.bonus;
    return Math.min(MAX_SECONDS, seconds);
  }

  function stepsIncludingActive() {
    var all = steps.slice();
    if (active) { all.push({ reagent: active.reagent, seconds: activeSeconds() }); }
    return all;
  }

  function stepCount() { return steps.length + (active ? 1 : 0); }

  function label(reagent) { return config.reagents[reagent].label; }
  function color(reagent) { return config.reagents[reagent].color; }

  // ------------------------------------------------------------------
  // Slide liquid ("wash") overlay
  // ------------------------------------------------------------------
  function showWash(reagent) {
    clearTimeout(washTimeout);
    wash.style.fill = color(reagent);
    wash.classList.add('is-active');
  }

  function rinseWash() {
    showWash('water');
    washTimeout = setTimeout(function () { wash.classList.remove('is-active'); }, 700);
  }

  function clearWash() {
    clearTimeout(washTimeout);
    wash.classList.remove('is-active');
  }

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------
  function finishActive() {
    if (!active) { return; }
    steps.push({ reagent: active.reagent, seconds: Math.max(0.1, round1(activeSeconds())) });
    active = null;
  }

  function applyReagent(reagent) {
    if (submitting) { return; }
    if (reagent === 'water') {
      finishActive();
      if (steps.length >= MAX_STEPS) { return render(); }
      steps.push({ reagent: 'water', seconds: RINSE_SECONDS });
      rinseWash();
    } else {
      if (active && active.reagent === reagent) { return; }  // already on the slide
      finishActive();  // switching reagents without rinsing (graded as a missed rinse)
      if (steps.length >= MAX_STEPS) { clearWash(); return render(); }
      active = { reagent: reagent, startedAt: performance.now(), bonus: 0 };
      showWash(reagent);
    }
    render();
  }

  function fastForward() {
    if (!active) { return; }
    active.bonus += FAST_FORWARD_SECONDS;
    render();
  }

  function reset() {
    if (stepCount() && !window.confirm('Clear the slide and start this run over?')) { return; }
    steps = [];
    active = null;
    clearWash();
    render();
  }

  // ------------------------------------------------------------------
  // Rendering
  // ------------------------------------------------------------------
  function logItem(reagent, text, isLive) {
    var li = document.createElement('li');
    var name = document.createElement('span');
    var swatch = document.createElement('span');
    var seconds = document.createElement('span');
    swatch.className = 'ms-swatch';
    swatch.style.background = color(reagent);
    name.appendChild(swatch);
    name.appendChild(document.createTextNode(label(reagent)));
    seconds.className = isLive ? 'fw-semibold text-primary' : 'text-muted';
    seconds.textContent = text;
    li.appendChild(name);
    li.appendChild(seconds);
    return li;
  }

  function renderLog() {
    logEl.textContent = '';
    if (!stepCount()) {
      var empty = document.createElement('li');
      empty.className = 'text-muted';
      empty.textContent = 'No reagents applied yet.';
      logEl.appendChild(empty);
      return;
    }
    steps.forEach(function (step, index) {
      logEl.appendChild(logItem(step.reagent, (index + 1) + '. ' + step.seconds.toFixed(1) + ' s', false));
    });
    if (active) {
      logEl.appendChild(logItem(active.reagent, 'on slide · ' + activeSeconds().toFixed(1) + ' s', true));
    }
    logEl.scrollTop = logEl.scrollHeight;
  }

  function render() {
    var stain = chemistry.simulateStain(stepsIncludingActive(), config);
    if (cells.getAttribute('data-stain') !== stain) { cells.setAttribute('data-stain', stain); }

    timerEl.textContent = activeSeconds().toFixed(1) + ' s';
    currentEl.textContent = active ? label(active.reagent) : 'nothing';

    var full = stepCount() >= MAX_STEPS;
    rackButtons.forEach(function (button) {
      var reagent = button.getAttribute('data-reagent');
      var isActive = !!active && active.reagent === reagent;
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      button.disabled = submitting || (full && !isActive && reagent !== 'water');
    });
    fastForwardBtn.disabled = submitting || !active;
    resetBtn.disabled = submitting || !stepCount();
    submitBtn.disabled = submitting || !stepCount();
    renderLog();
  }

  // ------------------------------------------------------------------
  // Wiring
  // ------------------------------------------------------------------
  rackButtons.forEach(function (button) {
    button.addEventListener('click', function () { applyReagent(button.getAttribute('data-reagent')); });
  });
  fastForwardBtn.addEventListener('click', fastForward);
  resetBtn.addEventListener('click', reset);

  form.addEventListener('submit', function (event) {
    finishActive();
    if (!steps.length) { event.preventDefault(); return render(); }
    stepsInput.value = JSON.stringify(steps);
    submitting = true;
    render();
  });

  window.addEventListener('beforeunload', function (event) {
    if (stepCount() && !submitting) { event.preventDefault(); event.returnValue = ''; }
  });

  setInterval(function () { if (active) { render(); } }, TICK_MS);
  render();
})();
