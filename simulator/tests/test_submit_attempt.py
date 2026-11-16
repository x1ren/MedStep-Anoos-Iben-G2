import json
from urllib.parse import quote

from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from simulator.models import GramStainScenario, SimulationAttempt
from simulator.tests.factories import (
    ecoli,
    make_admin,
    make_attempt,
    make_learner,
    protocol_steps,
    staph,
    unknown,
)


def messages_of(response):
    return [(m.level_tag, m.message) for m in get_messages(response.wsgi_request)]


class SubmitAttemptTests(TestCase):
    """Create: the workbench run is graded on the server and saved to the database."""

    @classmethod
    def setUpTestData(cls):
        cls.learner = make_learner()
        cls.admin = make_admin()
        cls.staph = staph()

    def setUp(self):
        self.client.force_login(self.learner)

    def submit(self, steps, scenario=None, raw=None, **extra):
        url = reverse('simulator:submit_attempt', args=[(scenario or self.staph).pk])
        return self.client.post(url, {'steps': raw if raw is not None else json.dumps(steps), **extra})

    # --- access ------------------------------------------------------------
    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        url = reverse('simulator:submit_attempt', args=[self.staph.pk])
        response = self.client.post(url, {'steps': json.dumps(protocol_steps())})
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={quote(url)}",
                             fetch_redirect_response=False)
        self.assertFalse(SimulationAttempt.objects.exists())

    def test_lab_admin_forbidden(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.submit(protocol_steps()).status_code, 403)
        self.assertFalse(SimulationAttempt.objects.exists())

    def test_get_not_allowed(self):
        url = reverse('simulator:submit_attempt', args=[self.staph.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_csrf_token_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.learner)
        url = reverse('simulator:submit_attempt', args=[self.staph.pk])
        response = client.post(url, {'steps': json.dumps(protocol_steps())})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(SimulationAttempt.objects.exists())

    def test_inactive_scenario_is_404(self):
        GramStainScenario.objects.filter(pk=self.staph.pk).update(is_active=False)
        self.assertEqual(self.submit(protocol_steps()).status_code, 404)
        self.assertFalse(SimulationAttempt.objects.exists())

    def test_workbench_form_posts_to_submit_url(self):
        response = self.client.get(reverse('simulator:workbench', args=[self.staph.pk]))
        self.assertContains(response, f'action="{reverse("simulator:submit_attempt", args=[self.staph.pk])}"')

    # --- saving --------------------------------------------------------------
    def test_perfect_run_saved_and_passed(self):
        response = self.submit(protocol_steps())
        attempt = SimulationAttempt.objects.get()
        self.assertRedirects(response, reverse('simulator:attempt_detail', args=[attempt.pk]))
        self.assertEqual(attempt.user, self.learner)
        self.assertEqual(attempt.scenario, self.staph)
        self.assertEqual(attempt.score, 100)
        self.assertTrue(attempt.is_passed)
        self.assertEqual(attempt.outcome_diagnosis, 'Accurate Stain: Gram-Positive Cocci (Violet)')
        self.assertEqual(attempt.observed_color, 'violet')
        self.assertEqual(attempt.expected_color, 'violet')
        self.assertEqual(attempt.recorded_steps_json, protocol_steps())
        self.assertTrue(attempt.grading_feedback)
        self.assertEqual(attempt.lab_notes, '')
        level, text = messages_of(response)[0]
        self.assertEqual(level, 'success')
        self.assertIn('Attempt saved and passed', text)
        self.assertIn('100/100', text)

    def test_failed_run_saved_with_warning(self):
        response = self.submit(protocol_steps(decolorizer=40))
        attempt = SimulationAttempt.objects.get()
        self.assertFalse(attempt.is_passed)
        self.assertEqual(attempt.outcome_diagnosis,
                         'Procedural Error: Over-decolorized (False Gram-Negative)')
        self.assertEqual(attempt.observed_color, 'pink')
        level, text = messages_of(response)[0]
        self.assertEqual(level, 'warning')
        self.assertIn('not passed', text)

    def test_grading_uses_the_scenario_rules(self):
        self.submit(protocol_steps(decolorizer=25), scenario=unknown())   # 10 s target
        self.submit(protocol_steps(decolorizer=25), scenario=ecoli())     # 15 s target
        by_title = {a.scenario.title: a for a in SimulationAttempt.objects.all()}
        self.assertIn('Over-decolorized', by_title['Unknown Clinical Smear'].outcome_diagnosis)
        self.assertTrue(by_title['Practice #2: Escherichia coli'].is_passed)

    def test_client_cannot_forge_results_or_owner(self):
        other = make_learner('bob')
        self.submit(protocol_steps(decolorizer=40),
                    score=100, is_passed='on', user=other.pk, outcome_diagnosis='Perfect')
        attempt = SimulationAttempt.objects.get()
        self.assertEqual(attempt.user, self.learner)
        self.assertLess(attempt.score, 100)
        self.assertFalse(attempt.is_passed)
        self.assertNotEqual(attempt.outcome_diagnosis, 'Perfect')

    def test_steps_are_cleaned_before_saving(self):
        self.submit([{'reagent': 'crystal_violet', 'seconds': 59.96, 'hacked': True}])
        self.assertEqual(SimulationAttempt.objects.get().recorded_steps_json,
                         [{'reagent': 'crystal_violet', 'seconds': 60.0}])

    # --- rejected runs --------------------------------------------------------
    def assert_rejected(self, response, fragment):
        self.assertRedirects(response, reverse('simulator:workbench', args=[self.staph.pk]))
        self.assertFalse(SimulationAttempt.objects.exists())
        level, text = messages_of(response)[0]
        self.assertEqual(level, 'danger')
        self.assertIn(fragment, text)

    def test_malformed_json_rejected(self):
        self.assert_rejected(self.submit(None, raw='{not json'), 'could not be read')

    def test_missing_steps_rejected(self):
        url = reverse('simulator:submit_attempt', args=[self.staph.pk])
        self.assert_rejected(self.client.post(url, {}), 'could not be read')

    def test_empty_run_rejected(self):
        self.assert_rejected(self.submit([]), 'apply at least one reagent')

    def test_tampered_steps_rejected(self):
        for bad in ([{'reagent': 'bleach', 'seconds': 5}],
                    [{'reagent': 'water', 'seconds': -1}],
                    {'reagent': 'water', 'seconds': 5}):
            with self.subTest(bad=bad):
                self.assert_rejected(self.submit(bad), 'could not be graded')

    def test_oversized_payload_rejected(self):
        self.assert_rejected(self.submit(None, raw='[' + ' ' * 10_001 + ']'), 'too long')


class AttemptDetailAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_learner()
        cls.other = make_learner('bob')
        cls.admin = make_admin()
        cls.attempt = make_attempt(cls.owner, staph())
        cls.url = reverse('simulator:attempt_detail', args=[cls.attempt.pk])

    def test_owner_can_view(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_other_learner_gets_404(self):
        """Horizontal privilege escalation: guessing another learner's attempt id."""
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_admin_forbidden_and_anonymous_redirected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get(self.url),
                             f"{reverse('accounts:login')}?next={quote(self.url)}")
