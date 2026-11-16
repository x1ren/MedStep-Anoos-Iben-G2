/*
 * MedStep — Gram stain chemistry (browser copy of simulator/grading.py
 * `simulate_color`). Drives the live cell colour on the workbench; the
 * server re-grades every submission, so this is for feedback only.
 * Kept in sync by simulator/tests/test_js_chemistry_parity.py.
 */
(function (root) {
  'use strict';

  function isEffective(reagent, seconds, target) {
    // Stains / mordant held for under a quarter of the target do not take.
    return reagent === 'decolorizer' ? seconds > 0 : seconds >= target * 0.25;
  }

  /**
   * Replay reagent steps on the specimen's cells.
   * @param {Array<{reagent: string, seconds: number}>} steps
   * @param {{gramType: string, targets: Object, decolorizerLimits: {under: number, over: number}}} config
   * @returns {'unstained'|'violet'|'pink'|'colorless'}
   */
  function simulateStain(steps, config) {
    var gramPositive = config.gramType === 'gram_positive';
    var under = config.decolorizerLimits.under;
    var over = config.decolorizerLimits.over;

    var hasViolet = false;   // crystal violet inside the cells
    var hasComplex = false;  // crystal violet locked in by iodine
    var hasPink = false;     // safranin counterstain
    var everStained = false; // used only to show "unstained" before any dye
    var decolorized = 0;     // decolorizer exposure since crystal violet

    steps.forEach(function (step) {
      var reagent = step.reagent;
      var seconds = step.seconds;
      if (reagent === 'water') { return; }
      var effective = isEffective(reagent, seconds, config.targets[reagent]);

      if (reagent === 'crystal_violet' && effective) {
        hasViolet = true; hasComplex = false; decolorized = 0; everStained = true;
      } else if (reagent === 'iodine' && effective && hasViolet) {
        hasComplex = true;
      } else if (reagent === 'decolorizer') {
        decolorized += seconds;
        hasPink = false;
        if (hasViolet) {
          if (gramPositive && hasComplex) {
            if (decolorized > over) { hasViolet = hasComplex = false; }
          } else if (decolorized >= under) {
            hasViolet = hasComplex = false;
          }
        }
      } else if (reagent === 'safranin' && effective) {
        hasPink = true; everStained = true;
      }
    });

    if (hasViolet) { return 'violet'; }
    if (hasPink) { return 'pink'; }
    return everStained ? 'colorless' : 'unstained';
  }

  var api = { simulateStain: simulateStain, isEffective: isEffective };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;            // Node (parity tests)
  } else {
    root.MedStepChemistry = api;     // Browser
  }
})(this);
