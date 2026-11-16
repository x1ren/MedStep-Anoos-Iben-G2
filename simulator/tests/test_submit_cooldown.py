import json
from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from simulator.models import SimulationAttempt
from simulator.tests.factories import ecoli, make_attempt, make_learner, protocol_steps, staph


@override_settings(ATTEMPT_COOLDOWN_SECONDS=10)
class SubmitCooldownTests(TestCase):
    """A second submission for the same scenario within the cooldown is not saved."""

    @classmethod
    def setUpTestData(cls):
        cls.learner = make_learner()
        cls.staph = staph()

    def setUp(self):
        self.client.force_login(self.learner)

    def submit(self, scenario=None):
        url = reverse('simulator:submit_attempt', args=[(scenario or self.staph).pk])
        return self.client.post(url, {'steps': json.dumps(protocol_steps())})

    def backdate(self, attempt, seconds):
        SimulationAttempt.objects.filter(pk=attempt.pk).update(
            completed_at=timezone.now() - timedelta(seconds=seconds)
        )

    def test_double_submit_saves_one_attempt(self):
        self.submit()
        response = self.submit()
        attempt = SimulationAttempt.objects.get()
        self.assertRedirects(response, reverse('simulator:attempt_detail', args=[attempt.pk]))
        levels = [m.level_tag for m in get_messages(response.wsgi_request)]
        self.assertIn('info', levels)

    def test_submit_allowed_after_cooldown(self):
        self.backdate(make_attempt(self.learner, self.staph), seconds=11)
        self.submit()
        self.assertEqual(SimulationAttempt.objects.count(), 2)

    def test_cooldown_is_per_scenario(self):
        make_attempt(self.learner, self.staph)
        self.submit(scenario=ecoli())
        self.assertEqual(SimulationAttempt.objects.count(), 2)

    def test_cooldown_is_per_learner(self):
        make_attempt(make_learner('bob'), self.staph)
        self.submit()
        self.assertEqual(SimulationAttempt.objects.filter(user=self.learner).count(), 1)

    @override_settings(ATTEMPT_COOLDOWN_SECONDS=0)
    def test_zero_disables_cooldown(self):
        self.submit()
        self.submit()
        self.assertEqual(SimulationAttempt.objects.count(), 2)
