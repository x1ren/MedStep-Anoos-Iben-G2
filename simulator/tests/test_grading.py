from django.test import SimpleTestCase

from simulator.grading import (
    PASS_MARK,
    StepValidationError,
    grade_attempt,
    simulate_color,
    validate_steps,
)
from simulator.models import GramStainScenario


def scenario(gram='gram_positive', shape='cocci', decolorizer=15):
    """Unsaved scenario — grading never touches the database."""
    return GramStainScenario(
        title='Test', specimen_name='Test organism', gram_type=gram, cell_shape=shape,
        crystal_violet_seconds=60, iodine_seconds=60,
        decolorizer_seconds=decolorizer, safranin_seconds=45,
    )


GRAM_POS = scenario('gram_positive', 'cocci')
GRAM_NEG = scenario('gram_negative', 'bacilli')
CHALLENGE = scenario('gram_positive', 'bacilli', decolorizer=10)


def run(cv=60, iodine=60, decol=15, safranin=45, rinse=True, order=None):
    """Build a step list; pass None to skip a reagent."""
    timings = {'crystal_violet': cv, 'iodine': iodine, 'decolorizer': decol, 'safranin': safranin}
    steps = []
    for reagent in order or ['crystal_violet', 'iodine', 'decolorizer', 'safranin']:
        if timings[reagent] is None:
            continue
        steps.append({'reagent': reagent, 'seconds': timings[reagent]})
        if rinse:
            steps.append({'reagent': 'water', 'seconds': 5})
    return steps


def statuses(result):
    return {item['title']: item['status'] for item in result.feedback}


class PerfectRunTests(SimpleTestCase):
    def test_gram_positive_perfect(self):
        result = grade_attempt(GRAM_POS, run())
        self.assertEqual(result.score, 100)
        self.assertTrue(result.is_passed)
        self.assertEqual(result.observed_color, 'violet')
        self.assertEqual(result.outcome_diagnosis, 'Accurate Stain: Gram-Positive Cocci (Violet)')
        self.assertTrue(all(s == 'ok' for s in statuses(result).values()))

    def test_gram_negative_perfect(self):
        result = grade_attempt(GRAM_NEG, run())
        self.assertEqual(result.score, 100)
        self.assertTrue(result.is_passed)
        self.assertEqual(result.observed_color, 'pink')
        self.assertEqual(result.outcome_diagnosis, 'Accurate Stain: Gram-Negative Bacilli (Pink)')


class DecolorizerTests(SimpleTestCase):
    def test_over_decolorized_gram_positive_looks_gram_negative(self):
        result = grade_attempt(GRAM_POS, run(decol=35))
        self.assertEqual(result.observed_color, 'pink')
        self.assertEqual(result.outcome_diagnosis,
                         'Procedural Error: Over-decolorized (False Gram-Negative)')
        self.assertFalse(result.is_passed)
        self.assertEqual(result.score, 100 - 15 - 20)
        self.assertEqual(statuses(result)['95% Ethanol / Acetone'], 'error')

    def test_over_decolorizing_gram_negative_still_pink_but_penalised(self):
        result = grade_attempt(GRAM_NEG, run(decol=35))
        self.assertEqual(result.observed_color, 'pink')
        self.assertTrue(result.outcome_diagnosis.startswith('Accurate Stain'))
        self.assertTrue(result.is_passed)
        self.assertEqual(result.score, 85)

    def test_under_decolorized_gram_negative_looks_gram_positive(self):
        result = grade_attempt(GRAM_NEG, run(decol=3))
        self.assertEqual(result.observed_color, 'violet')
        self.assertEqual(result.outcome_diagnosis,
                         'Procedural Error: Under-decolorized (False Gram-Positive)')
        self.assertFalse(result.is_passed)

    def test_short_decolorizing_does_not_hurt_gram_positive_colour(self):
        result = grade_attempt(GRAM_POS, run(decol=3))
        self.assertEqual(result.observed_color, 'violet')
        self.assertEqual(result.score, 85)  # timing penalty only

    def test_repeated_decolorizer_applications_accumulate(self):
        steps = run(decol=None)
        steps[4:4] = [{'reagent': 'decolorizer', 'seconds': 20}, {'reagent': 'water', 'seconds': 5},
                      {'reagent': 'decolorizer', 'seconds': 15}, {'reagent': 'water', 'seconds': 5}]
        result = grade_attempt(GRAM_POS, steps)
        self.assertEqual(result.observed_color, 'pink')
        self.assertIn('Over-decolorized', result.outcome_diagnosis)

    def test_challenge_window_is_tighter(self):
        self.assertIn('Over-decolorized', grade_attempt(CHALLENGE, run(decol=25)).outcome_diagnosis)
        self.assertEqual(grade_attempt(GRAM_POS, run(decol=25)).observed_color, 'violet')
        ok = grade_attempt(CHALLENGE, run(decol=10))
        self.assertEqual(ok.outcome_diagnosis, 'Accurate Stain: Gram-Positive Bacilli (Violet)')
        self.assertEqual(ok.score, 100)

    def test_acceptable_but_not_ideal_timing_warns(self):
        result = grade_attempt(GRAM_POS, run(decol=25))
        self.assertEqual(statuses(result)['95% Ethanol / Acetone'], 'warn')
        self.assertEqual(result.score, 95)


class MissingReagentTests(SimpleTestCase):
    def test_no_iodine_gram_positive_washes_out(self):
        result = grade_attempt(GRAM_POS, run(iodine=None))
        self.assertEqual(result.observed_color, 'pink')
        self.assertEqual(result.outcome_diagnosis,
                         'Procedural Error: Mordant Omitted (False Gram-Negative)')
        self.assertEqual(result.score, 100 - 25 - 20)
        self.assertFalse(result.is_passed)

    def test_no_decolorizer_gram_negative_stays_violet(self):
        result = grade_attempt(GRAM_NEG, run(decol=None))
        self.assertEqual(result.observed_color, 'violet')
        self.assertEqual(result.outcome_diagnosis,
                         'Procedural Error: Decolorizer Omitted (False Gram-Positive)')

    def test_no_safranin_gram_positive_correct_colour_but_incomplete(self):
        result = grade_attempt(GRAM_POS, run(safranin=None))
        self.assertEqual(result.observed_color, 'violet')
        self.assertEqual(result.outcome_diagnosis, 'Incomplete Protocol: Safranin Omitted')
        self.assertEqual(result.score, 75)
        self.assertFalse(result.is_passed)  # protocol incomplete

    def test_no_safranin_gram_negative_colorless(self):
        result = grade_attempt(GRAM_NEG, run(safranin=None))
        self.assertEqual(result.observed_color, 'colorless')
        self.assertEqual(result.outcome_diagnosis,
                         'Procedural Error: Counterstain Omitted (Cells Colorless)')

    def test_no_crystal_violet(self):
        result = grade_attempt(GRAM_POS, run(cv=None))
        self.assertEqual(result.observed_color, 'pink')
        self.assertEqual(result.outcome_diagnosis,
                         'Procedural Error: Primary Stain Omitted (Uninterpretable Smear)')
        self.assertFalse(result.is_passed)

    def test_too_short_crystal_violet_does_not_take(self):
        result = grade_attempt(GRAM_POS, run(cv=5))
        self.assertIn('Primary Stain Omitted', result.outcome_diagnosis)
        self.assertEqual(statuses(result)['Crystal Violet'], 'error')

    def test_nothing_but_water(self):
        result = grade_attempt(GRAM_POS, [{'reagent': 'water', 'seconds': 5}])
        self.assertEqual(result.score, 0)
        self.assertEqual(result.outcome_diagnosis, 'No Stain Applied: Smear Not Processed')

    def test_empty_run(self):
        self.assertEqual(grade_attempt(GRAM_POS, []).score, 0)


class OrderAndRinseTests(SimpleTestCase):
    def test_safranin_before_decolorizer(self):
        steps = run(order=['crystal_violet', 'iodine', 'safranin', 'decolorizer'])
        result = grade_attempt(GRAM_NEG, steps)
        self.assertEqual(result.outcome_diagnosis, 'Procedural Error: Reagents Out of Order')
        self.assertEqual(result.observed_color, 'colorless')  # decolorizer stripped the safranin
        self.assertEqual(statuses(result)['Reagent order'], 'error')
        self.assertFalse(result.is_passed)

    def test_iodine_before_crystal_violet_gives_no_mordant(self):
        steps = run(order=['iodine', 'crystal_violet', 'decolorizer', 'safranin'])
        result = grade_attempt(GRAM_POS, steps)
        self.assertEqual(result.observed_color, 'pink')
        self.assertIn('Out of Order', result.outcome_diagnosis)

    def test_repeating_a_reagent_in_place_is_not_out_of_order(self):
        steps = run()
        steps[0:0] = [{'reagent': 'crystal_violet', 'seconds': 30}, {'reagent': 'water', 'seconds': 5}]
        steps[2]['seconds'] = 30
        result = grade_attempt(GRAM_POS, steps)
        self.assertEqual(statuses(result)['Reagent order'], 'ok')
        self.assertEqual(result.score, 100)  # 30s + 30s = 60s total

    def test_missed_rinses_cost_three_points_each(self):
        result = grade_attempt(GRAM_POS, run(rinse=False))
        self.assertEqual(result.score, 100 - 4 * 3)
        self.assertTrue(result.is_passed)
        self.assertEqual(statuses(result)['Rinses'], 'warn')

    def test_slight_timing_deviation(self):
        result = grade_attempt(GRAM_POS, run(cv=40))
        self.assertEqual(statuses(result)['Crystal Violet'], 'warn')
        self.assertEqual(result.score, 95)

    def test_pass_mark(self):
        self.assertEqual(PASS_MARK, 70)
        # Correct colour and complete protocol, but every timing is off and no rinses:
        # 100 - 3x10 (CV, iodine, safranin) - 15 (decolorizer) - 4x3 (rinses) = 43.
        sloppy = grade_attempt(GRAM_NEG, run(cv=200, iodine=200, decol=40, safranin=200, rinse=False))
        self.assertEqual(sloppy.observed_color, 'pink')
        self.assertEqual(sloppy.score, 43)
        self.assertFalse(sloppy.is_passed)

    def test_score_never_negative(self):
        steps = [{'reagent': 'safranin', 'seconds': 1}, {'reagent': 'decolorizer', 'seconds': 900}]
        self.assertEqual(grade_attempt(GRAM_POS, steps).score, 0)


class ValidationTests(SimpleTestCase):
    def test_rejects_bad_input(self):
        bad_inputs = [
            'not a list',
            {'reagent': 'water'},
            ['not a dict'],
            [{'reagent': 'bleach', 'seconds': 5}],
            [{'reagent': 'water'}],
            [{'reagent': 'water', 'seconds': '5'}],
            [{'reagent': 'water', 'seconds': True}],
            [{'reagent': 'water', 'seconds': 0}],
            [{'reagent': 'water', 'seconds': -3}],
            [{'reagent': 'water', 'seconds': 901}],
            [{'reagent': 'water', 'seconds': 1}] * 51,
        ]
        for bad in bad_inputs:
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(StepValidationError):
                validate_steps(bad)

    def test_cleans_and_rounds(self):
        clean = validate_steps([{'reagent': 'iodine', 'seconds': 59.96, 'extra': 'ignored'}])
        self.assertEqual(clean, [{'reagent': 'iodine', 'seconds': 60.0}])

    def test_grade_returns_clean_steps(self):
        result = grade_attempt(GRAM_POS, [{'reagent': 'crystal_violet', 'seconds': 60.04, 'x': 1}])
        self.assertEqual(result.steps, [{'reagent': 'crystal_violet', 'seconds': 60.0}])


class SimulateColorTests(SimpleTestCase):
    def test_stain_colours_after_each_stage(self):
        self.assertEqual(simulate_color(GRAM_NEG, run(iodine=None, decol=None, safranin=None)), 'violet')
        self.assertEqual(simulate_color(GRAM_NEG, run(safranin=None)), 'colorless')
        self.assertEqual(simulate_color(GRAM_NEG, run()), 'pink')
        self.assertEqual(simulate_color(GRAM_POS, run()), 'violet')
