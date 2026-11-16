"""Gram staining grading engine (pure Python — no database or HTTP).

The learner's run arrives as an ordered list of steps::

    [{"reagent": "crystal_violet", "seconds": 60}, {"reagent": "water", "seconds": 5}, ...]

Grading has two parts:

1. **Chemistry simulation** — replays the steps against the specimen's cell
   wall to decide what colour the cells end up (violet / pink / colorless).
   Gram-positive cells keep the crystal violet–iodine complex unless they are
   over-decolorized; Gram-negative cells lose crystal violet as soon as they
   are decolorized enough. So wrong technique produces a *visibly* wrong stain.
2. **Scoring** — 100 points minus deductions for missing reagents, wrong
   order, timings outside the scenario's targets, skipped rinses and a wrong
   final result.

An attempt passes when the final colour is correct, all four reagents were
applied effectively in the right order, and the score is at least PASS_MARK.
"""

from dataclasses import dataclass, field

CRYSTAL_VIOLET = 'crystal_violet'
IODINE = 'iodine'
DECOLORIZER = 'decolorizer'
SAFRANIN = 'safranin'
WATER = 'water'

REAGENT_LABELS = {
    CRYSTAL_VIOLET: 'Crystal Violet',
    IODINE: "Gram's Iodine",
    DECOLORIZER: '95% Ethanol / Acetone',
    SAFRANIN: 'Safranin',
    WATER: 'Distilled Water Rinse',
}
PROTOCOL = [CRYSTAL_VIOLET, IODINE, DECOLORIZER, SAFRANIN]
STAGE = {reagent: index for index, reagent in enumerate(PROTOCOL)}

PASS_MARK = 70
MAX_STEPS = 50
MAX_SECONDS = 900

# Deductions
MISSING_REAGENT = 25
OUT_OF_ORDER = 20
TIMING_SLIGHT = 5
TIMING_POOR = 10
DECOLORIZER_POOR = 15
MISSED_RINSE = 3
WRONG_RESULT = 20

VIOLET, PINK, COLORLESS = 'violet', 'pink', 'colorless'


class StepValidationError(ValueError):
    """The submitted steps are malformed (tampered with or corrupted)."""


@dataclass
class GradeResult:
    score: int
    is_passed: bool
    outcome_diagnosis: str
    observed_color: str
    expected_color: str
    steps: list
    feedback: list = field(default_factory=list)

    @property
    def is_accurate(self):
        return self.observed_color == self.expected_color


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate_steps(raw_steps):
    """Return a clean copy of the steps or raise StepValidationError."""
    if not isinstance(raw_steps, list):
        raise StepValidationError('Steps must be a list.')
    if len(raw_steps) > MAX_STEPS:
        raise StepValidationError(f'Too many steps (maximum {MAX_STEPS}).')

    clean = []
    for index, step in enumerate(raw_steps, start=1):
        if not isinstance(step, dict):
            raise StepValidationError(f'Step {index} is not an object.')
        reagent = step.get('reagent')
        if reagent not in REAGENT_LABELS:
            raise StepValidationError(f'Step {index} has an unknown reagent.')
        seconds = step.get('seconds')
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
            raise StepValidationError(f'Step {index} has invalid seconds.')
        if not 0 < seconds <= MAX_SECONDS:
            raise StepValidationError(f'Step {index} seconds must be between 0 and {MAX_SECONDS}.')
        clean.append({'reagent': reagent, 'seconds': round(float(seconds), 1)})
    return clean


# --------------------------------------------------------------------------
# Timing helpers
# --------------------------------------------------------------------------

def target_seconds(scenario, reagent):
    return {
        CRYSTAL_VIOLET: scenario.crystal_violet_seconds,
        IODINE: scenario.iodine_seconds,
        DECOLORIZER: scenario.decolorizer_seconds,
        SAFRANIN: scenario.safranin_seconds,
    }[reagent]


def decolorizer_limits(target):
    """(under, over): below `under` fails to decolorize; above `over` strips Gram-positives."""
    return target / 3, target * 2


def is_effective(reagent, seconds, target):
    """Stains / mordant held for under a quarter of the target do not take."""
    if reagent == DECOLORIZER:
        return seconds > 0
    return seconds >= target * 0.25


def rate_timing(reagent, seconds, target):
    """Return (status, deduction, message) for one reagent's total exposure."""
    if reagent == DECOLORIZER:
        under, over = decolorizer_limits(target)
        if seconds < under:
            return 'error', DECOLORIZER_POOR, (
                f'Under-decolorized: {seconds:g}s is far below the {target}s target. '
                'Crystal violet was not washed out of Gram-negative cells.'
            )
        if seconds > over:
            return 'error', DECOLORIZER_POOR, (
                f'Over-decolorized: {seconds:g}s is more than double the {target}s target. '
                'This strips crystal violet from Gram-positive cells.'
            )
        if target * 2 / 3 <= seconds <= target * 4 / 3:
            return 'ok', 0, f'{seconds:g}s — right on the {target}s target.'
        return 'warn', TIMING_SLIGHT, f'{seconds:g}s — acceptable, but aim closer to {target}s.'

    if seconds < target * 0.25:
        return 'error', TIMING_POOR, f'Only {seconds:g}s of a {target}s target — too short to take effect.'
    if target * 0.75 <= seconds <= target * 1.5:
        return 'ok', 0, f'{seconds:g}s — within the {target}s target.'
    if target * 0.5 <= seconds <= target * 2:
        return 'warn', TIMING_SLIGHT, f'{seconds:g}s — acceptable, but aim closer to {target}s.'
    return 'error', TIMING_POOR, f'{seconds:g}s is far from the {target}s target.'


# --------------------------------------------------------------------------
# Chemistry simulation
# --------------------------------------------------------------------------

def simulate_color(scenario, steps):
    """Replay the reagent steps on the specimen's cells and return the final colour."""
    gram_positive = scenario.is_gram_positive
    under, over = decolorizer_limits(scenario.decolorizer_seconds)

    has_violet = False      # crystal violet inside the cells
    has_complex = False     # crystal violet locked in by iodine
    has_pink = False        # safranin counterstain
    decolorized = 0.0       # decolorizer exposure since crystal violet went on

    for step in steps:
        reagent, seconds = step['reagent'], step['seconds']
        if reagent == WATER:
            continue
        target = target_seconds(scenario, reagent)
        effective = is_effective(reagent, seconds, target)

        if reagent == CRYSTAL_VIOLET and effective:
            has_violet, has_complex, decolorized = True, False, 0.0
        elif reagent == IODINE and effective and has_violet:
            has_complex = True
        elif reagent == DECOLORIZER:
            decolorized += seconds
            has_pink = False  # decolorizer also strips any earlier safranin
            if has_violet:
                if gram_positive and has_complex:
                    # Thick peptidoglycan holds the complex unless over-decolorized.
                    if decolorized > over:
                        has_violet = has_complex = False
                elif decolorized >= under:
                    # Gram-negatives (or Gram-positives without mordant) wash out.
                    has_violet = has_complex = False
        elif reagent == SAFRANIN and effective:
            has_pink = True

    if has_violet:
        return VIOLET
    return PINK if has_pink else COLORLESS


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------

def grade_attempt(scenario, raw_steps):
    """Grade one learner run against a GramStainScenario. Returns GradeResult."""
    steps = validate_steps(raw_steps)
    expected = scenario.expected_color
    reagent_steps = [s for s in steps if s['reagent'] != WATER]

    if not reagent_steps:
        return GradeResult(
            score=0, is_passed=False,
            outcome_diagnosis='No Stain Applied: Smear Not Processed',
            observed_color=COLORLESS, expected_color=expected, steps=steps,
            feedback=[{'title': 'No reagents', 'status': 'error',
                       'message': 'No reagents were applied to the slide.'}],
        )

    score = 100
    feedback = []

    # --- 1. Order ---------------------------------------------------------
    out_of_order = any(
        STAGE[later['reagent']] < STAGE[earlier['reagent']]
        for earlier, later in zip(reagent_steps, reagent_steps[1:])
    )
    if out_of_order:
        score -= OUT_OF_ORDER
        sequence = ' → '.join(REAGENT_LABELS[s['reagent']] for s in reagent_steps)
        feedback.append({
            'title': 'Reagent order', 'status': 'error',
            'message': f'Out of order: {sequence}. Correct order: crystal violet → iodine → decolorizer → safranin.',
        })
    else:
        feedback.append({'title': 'Reagent order', 'status': 'ok',
                         'message': 'Reagents applied in the correct order.'})

    # --- 2. Each reagent: presence + timing -------------------------------
    totals = {reagent: 0.0 for reagent in PROTOCOL}
    for step in reagent_steps:
        totals[step['reagent']] += step['seconds']

    missing = []
    for reagent in PROTOCOL:
        label, target, seconds = REAGENT_LABELS[reagent], target_seconds(scenario, reagent), totals[reagent]
        if not seconds or not is_effective(reagent, seconds, target):
            missing.append(reagent)
        if not seconds:
            score -= MISSING_REAGENT
            feedback.append({'title': label, 'status': 'error', 'target': target, 'actual': 0,
                             'message': f'{label} was never applied.'})
            continue
        status, deduction, message = rate_timing(reagent, seconds, target)
        score -= deduction
        feedback.append({'title': label, 'status': status, 'target': target,
                         'actual': round(seconds, 1), 'message': message})

    # --- 3. Rinses --------------------------------------------------------
    missed_rinses = sum(
        1 for current, following in zip(steps, steps[1:] + [None])
        if current['reagent'] != WATER and (following is None or following['reagent'] != WATER)
    )
    if missed_rinses:
        score -= MISSED_RINSE * missed_rinses
        feedback.append({
            'title': 'Rinses', 'status': 'warn',
            'message': f'{missed_rinses} reagent{"s" if missed_rinses != 1 else ""} not rinsed off with '
                       'distilled water before the next step.',
        })
    else:
        feedback.append({'title': 'Rinses', 'status': 'ok',
                         'message': 'Every reagent was rinsed off before the next step.'})

    # --- 4. Result --------------------------------------------------------
    observed = simulate_color(scenario, steps)
    if observed != expected:
        score -= WRONG_RESULT

    diagnosis = diagnose(scenario, observed, missing, out_of_order, totals)
    complete = not missing and not out_of_order
    score = max(0, min(100, round(score)))
    return GradeResult(
        score=score,
        is_passed=observed == expected and complete and score >= PASS_MARK,
        outcome_diagnosis=diagnosis,
        observed_color=observed,
        expected_color=expected,
        steps=steps,
        feedback=feedback,
    )


def diagnose(scenario, observed, missing, out_of_order, totals):
    """Name the outcome the way a lab report would."""
    if out_of_order:
        return 'Procedural Error: Reagents Out of Order'
    if CRYSTAL_VIOLET in missing:
        return 'Procedural Error: Primary Stain Omitted (Uninterpretable Smear)'

    expected = scenario.expected_color
    if observed == expected:
        if not missing:
            return f'Accurate Stain: {scenario.expected_result}'
        omitted = ', '.join(REAGENT_LABELS[r] for r in missing)
        return f'Incomplete Protocol: {omitted} Omitted'

    under, over = decolorizer_limits(scenario.decolorizer_seconds)
    if expected == VIOLET:  # Gram-positive specimen came out wrong
        if IODINE in missing:
            return 'Procedural Error: Mordant Omitted (False Gram-Negative)'
        if totals[DECOLORIZER] > over:
            return 'Procedural Error: Over-decolorized (False Gram-Negative)'
        return 'Procedural Error: Crystal Violet Washed Out (False Gram-Negative)'

    # Gram-negative specimen came out wrong
    if observed == VIOLET:
        if DECOLORIZER in missing:
            return 'Procedural Error: Decolorizer Omitted (False Gram-Positive)'
        return 'Procedural Error: Under-decolorized (False Gram-Positive)'
    return 'Procedural Error: Counterstain Omitted (Cells Colorless)'
