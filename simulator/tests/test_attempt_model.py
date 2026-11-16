from datetime import timedelta

from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from simulator.models import GramStainScenario, SimulationAttempt

PASSWORD = 'pw-Test-123'

STEPS = [
    {'reagent': 'crystal_violet', 'seconds': 60},
    {'reagent': 'water', 'seconds': 5},
    {'reagent': 'iodine', 'seconds': 60},
    {'reagent': 'water', 'seconds': 5},
    {'reagent': 'decolorizer', 'seconds': 12},
    {'reagent': 'water', 'seconds': 5},
    {'reagent': 'safranin', 'seconds': 45},
    {'reagent': 'water', 'seconds': 5},
]


class AttemptTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user('lea', 'lea@example.com', PASSWORD)
        cls.other = User.objects.create_user('bob', 'bob@example.com', PASSWORD)
        cls.admin = User.objects.create_user(
            'curator', 'curator@example.com', PASSWORD, role=User.Role.ADMIN
        )
        cls.scenario = GramStainScenario.objects.get(title='Practice #1: Staphylococcus aureus')

    def make_attempt(self, user=None, scenario=None, **extra):
        data = {
            'user': user or self.learner,
            'scenario': scenario or self.scenario,
            'recorded_steps_json': STEPS,
            'score': 95,
            'outcome_diagnosis': 'Accurate Stain: Gram-Positive Cocci (Violet)',
            'is_passed': True,
        }
        data.update(extra)
        return SimulationAttempt.objects.create(**data)


class SimulationAttemptModelTests(AttemptTestCase):
    def test_create_and_defaults(self):
        attempt = SimulationAttempt.objects.create(
            user=self.learner, scenario=self.scenario, score=40,
            outcome_diagnosis='Procedural Error: Over-decolorized (False Gram-Negative)',
        )
        self.assertEqual(attempt.recorded_steps_json, [])
        self.assertFalse(attempt.is_passed)
        self.assertEqual(attempt.lab_notes, '')
        self.assertIsNotNone(attempt.completed_at)

    def test_steps_json_round_trips(self):
        attempt = self.make_attempt()
        attempt.refresh_from_db()
        self.assertEqual(attempt.recorded_steps_json, STEPS)
        self.assertEqual(attempt.recorded_steps_json[4], {'reagent': 'decolorizer', 'seconds': 12})

    def test_related_names(self):
        attempt = self.make_attempt()
        self.assertEqual(list(self.learner.attempts.all()), [attempt])
        self.assertEqual(list(self.scenario.attempts.all()), [attempt])
        self.assertEqual(self.other.attempts.count(), 0)

    def test_newest_first(self):
        old = self.make_attempt()
        new = self.make_attempt()
        SimulationAttempt.objects.filter(pk=old.pk).update(
            completed_at=timezone.now() - timedelta(days=1)
        )
        self.assertEqual(list(SimulationAttempt.objects.all()), [new, old])

    def test_str(self):
        self.assertEqual(
            str(self.make_attempt()), 'lea · Practice #1: Staphylococcus aureus · 95/100'
        )

    def test_score_capped_at_100(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.make_attempt(score=101)
        attempt = SimulationAttempt(
            user=self.learner, scenario=self.scenario, score=150, outcome_diagnosis='x'
        )
        with self.assertRaises(ValidationError) as ctx:
            attempt.full_clean()
        self.assertIn('score', ctx.exception.message_dict)

    def test_deleting_user_deletes_their_attempts(self):
        self.make_attempt(user=self.other)
        self.make_attempt()
        self.other.delete()
        self.assertEqual(SimulationAttempt.objects.count(), 1)

    def test_scenario_with_attempts_is_protected(self):
        self.make_attempt()
        with self.assertRaises(ProtectedError):
            self.scenario.delete()
        self.assertTrue(GramStainScenario.objects.filter(pk=self.scenario.pk).exists())


class ProtectedScenarioDeleteViewTests(AttemptTestCase):
    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse('simulator:scenario_delete', args=[self.scenario.pk])

    def test_confirmation_page_explains_and_hides_button(self):
        self.make_attempt()
        self.make_attempt(user=self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.context['attempt_count'], 2)
        self.assertContains(response, '2 saved learner attempts')
        self.assertNotContains(response, 'Yes, delete it')

    def test_post_is_refused_with_message(self):
        self.make_attempt()
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('simulator:scenario_update', args=[self.scenario.pk]))
        self.assertTrue(GramStainScenario.objects.filter(pk=self.scenario.pk).exists())
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('has 1 saved learner attempt and cannot be deleted' in m for m in messages))
        self.assertEqual(SimulationAttempt.objects.count(), 1)

    def test_scenario_without_attempts_still_deletable(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['attempt_count'], 0)
        self.assertContains(response, 'Yes, delete it')
