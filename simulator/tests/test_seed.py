from importlib import import_module

from django.apps import apps as django_apps
from django.test import TestCase

from simulator.models import GramStainScenario

seed_migration = import_module('simulator.migrations.0002_seed_starter_scenarios')


class StarterScenarioSeedTests(TestCase):
    """The seed migration has already run on the test database."""

    def test_three_starter_scenarios_exist(self):
        titles = set(GramStainScenario.objects.values_list('title', flat=True))
        self.assertEqual(titles, {
            'Practice #1: Staphylococcus aureus',
            'Practice #2: Escherichia coli',
            'Unknown Clinical Smear',
        })

    def test_starter_scenarios_are_microbiologically_correct(self):
        expected = {
            'Practice #1: Staphylococcus aureus': ('gram_positive', 'cocci', 'beginner'),
            'Practice #2: Escherichia coli': ('gram_negative', 'bacilli', 'beginner'),
            'Unknown Clinical Smear': ('gram_positive', 'bacilli', 'challenge'),
        }
        for scenario in GramStainScenario.objects.all():
            with self.subTest(scenario=scenario.title):
                self.assertEqual(
                    (scenario.gram_type, scenario.cell_shape, scenario.difficulty),
                    expected[scenario.title],
                )
                self.assertTrue(scenario.is_active)
                self.assertIsNone(scenario.created_by)
                self.assertTrue(scenario.description)

    def test_seed_passes_model_validation(self):
        for scenario in GramStainScenario.objects.all():
            with self.subTest(scenario=scenario.title):
                scenario.full_clean()

    def test_challenge_has_tighter_decolorizer_window(self):
        unknown = GramStainScenario.objects.get(title='Unknown Clinical Smear')
        self.assertLess(unknown.decolorizer_seconds, 15)

    def test_seed_is_idempotent(self):
        seed_migration.seed(django_apps, None)
        seed_migration.seed(django_apps, None)
        self.assertEqual(GramStainScenario.objects.count(), 3)

    def test_seed_does_not_overwrite_admin_edits(self):
        GramStainScenario.objects.filter(title='Practice #2: Escherichia coli').update(
            decolorizer_seconds=20
        )
        seed_migration.seed(django_apps, None)
        self.assertEqual(
            GramStainScenario.objects.get(title='Practice #2: Escherichia coli').decolorizer_seconds,
            20,
        )

    def test_unseed_removes_only_starter_rows(self):
        GramStainScenario.objects.create(
            title='Admin-made scenario', specimen_name='Pseudomonas aeruginosa',
            gram_type='gram_negative', cell_shape='bacilli',
        )
        seed_migration.unseed(django_apps, None)
        self.assertEqual(
            list(GramStainScenario.objects.values_list('title', flat=True)),
            ['Admin-made scenario'],
        )
