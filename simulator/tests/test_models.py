from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from simulator.models import GramStainScenario


def make_scenario(**overrides):
    data = {
        'title': 'Test smear: Staphylococcus aureus',
        'specimen_name': 'Staphylococcus aureus',
        'gram_type': GramStainScenario.GramType.POSITIVE,
        'cell_shape': GramStainScenario.CellShape.COCCI,
    }
    data.update(overrides)
    return GramStainScenario.objects.create(**data)


class GramStainScenarioModelTests(TestCase):
    def test_defaults(self):
        scenario = make_scenario()
        self.assertEqual(scenario.crystal_violet_seconds, 60)
        self.assertEqual(scenario.iodine_seconds, 60)
        self.assertEqual(scenario.decolorizer_seconds, 15)
        self.assertEqual(scenario.safranin_seconds, 45)
        self.assertEqual(scenario.difficulty, GramStainScenario.Difficulty.BEGINNER)
        self.assertTrue(scenario.is_active)
        self.assertIsNone(scenario.created_by)
        self.assertIsNotNone(scenario.created_at)

    def test_str_and_expected_results(self):
        positive = make_scenario()
        self.assertEqual(str(positive), 'Test smear: Staphylococcus aureus')
        self.assertTrue(positive.is_gram_positive)
        self.assertEqual(positive.expected_color, 'violet')
        self.assertEqual(positive.expected_result, 'Gram-Positive Cocci (Violet)')

        negative = make_scenario(
            title='Test smear: Escherichia coli', specimen_name='Escherichia coli',
            gram_type=GramStainScenario.GramType.NEGATIVE,
            cell_shape=GramStainScenario.CellShape.BACILLI,
        )
        self.assertEqual(negative.expected_color, 'pink')
        self.assertEqual(negative.expected_result, 'Gram-Negative Bacilli (Pink)')

    def test_title_is_unique(self):
        make_scenario()
        with self.assertRaises(IntegrityError):
            make_scenario()

    def test_database_rejects_invalid_choices_and_zero_timings(self):
        for bad in ({'gram_type': 'gram_purple'}, {'cell_shape': 'spirilla'},
                    {'decolorizer_seconds': 0}):
            with self.subTest(bad=bad), self.assertRaises(IntegrityError), transaction.atomic():
                make_scenario(title=f'Bad {bad}', **bad)

    def test_validators_limit_timings(self):
        scenario = GramStainScenario(
            title='Too long', specimen_name='X', gram_type='gram_positive',
            cell_shape='cocci', decolorizer_seconds=500,
        )
        with self.assertRaises(ValidationError) as ctx:
            scenario.full_clean()
        self.assertIn('decolorizer_seconds', ctx.exception.message_dict)

    def test_deleting_author_keeps_scenario(self):
        admin = User.objects.create_user(
            'curator', 'curator@example.com', 'pw-Test-123', role=User.Role.ADMIN
        )
        scenario = make_scenario(created_by=admin)
        self.assertEqual(list(admin.gram_scenarios.all()), [scenario])
        admin.delete()
        scenario.refresh_from_db()
        self.assertIsNone(scenario.created_by)
