from urllib.parse import quote

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from simulator.models import GramStainScenario
from simulator.tests.factories import (
    make_admin,
    make_attempt,
    make_learner,
    protocol_steps,
    staph,
    unknown,
)


class OutcomeReportTests(TestCase):
    """Read: the microscopic outcome report for one attempt."""

    @classmethod
    def setUpTestData(cls):
        cls.learner = make_learner()
        cls.staph = staph()
        cls.failed = make_attempt(cls.learner, cls.staph, protocol_steps(decolorizer=40))
        cls.passed = make_attempt(cls.learner, cls.staph)

    def setUp(self):
        self.client.force_login(self.learner)

    def get(self, attempt):
        return self.client.get(reverse('simulator:attempt_detail', args=[attempt.pk]))

    def test_shows_score_diagnosis_and_result(self):
        response = self.get(self.failed)
        self.assertTemplateUsed(response, 'simulator/attempt_detail.html')
        self.assertContains(response, 'Procedural Error: Over-decolorized (False Gram-Negative)')
        self.assertContains(response, 'Not passed')
        self.assertContains(response, f'{self.failed.score}</span>')
        self.assertContains(self.get(self.passed), 'Passed')

    def test_high_magnification_slides_show_observed_and_expected_colours(self):
        html = self.get(self.failed).content.decode()
        self.assertIn('id="result-slide"', html)
        self.assertIn('id="reference-slide"', html)
        self.assertIn('data-stain="pink"', html)     # what the learner produced
        self.assertIn('data-stain="violet"', html)   # what S. aureus should look like
        self.assertIn('scale(1.9)', html)

    def test_step_by_step_feedback_and_recorded_steps(self):
        response = self.get(self.failed)
        self.assertContains(response, 'Step-by-step feedback')
        self.assertContains(response, 'Over-decolorized: 40s is more than double the 15s target.')
        self.assertEqual(len(response.context['steps']), 8)
        self.assertEqual(response.context['steps'][4]['label'], '95% Ethanol / Acetone')
        self.assertContains(response, '40.0 s')

    def test_report_uses_grading_snapshot_not_current_scenario(self):
        GramStainScenario.objects.filter(pk=self.staph.pk).update(decolorizer_seconds=60)
        response = self.get(self.failed)
        self.assertContains(response, 'Over-decolorized')  # stored result unchanged
        self.assertContains(response, 'data-stain="pink"')

    def test_challenge_identity_revealed_after_submission(self):
        attempt = make_attempt(self.learner, unknown())
        self.assertContains(self.get(attempt), 'Bacillus cereus')

    def test_try_again_only_for_active_scenarios(self):
        workbench_url = reverse('simulator:workbench', args=[self.staph.pk])
        self.assertContains(self.get(self.passed), workbench_url)
        GramStainScenario.objects.filter(pk=self.staph.pk).update(is_active=False)
        self.assertNotContains(self.get(self.passed), workbench_url)

    def test_links_to_log_notes_and_delete(self):
        response = self.get(self.passed)
        self.assertContains(response, reverse('simulator:attempt_list'))
        self.assertContains(response, reverse('simulator:attempt_notes', args=[self.passed.pk]))
        self.assertContains(response, reverse('simulator:attempt_delete', args=[self.passed.pk]))


class LabNotesTests(TestCase):
    """Update: learners edit lab notes on their own attempts only."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_learner()
        cls.other = make_learner('bob')
        cls.admin = make_admin()
        cls.attempt = make_attempt(cls.owner, staph(), lab_notes='first notes')
        cls.url = reverse('simulator:attempt_notes', args=[cls.attempt.pk])

    def test_owner_saves_notes(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {'lab_notes': '  Cells stayed violet — good timing.  '})
        self.assertRedirects(response, self.attempt.get_absolute_url())
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.lab_notes, 'Cells stayed violet — good timing.')
        self.assertIn('Lab notes saved.', [m.message for m in get_messages(response.wsgi_request)])

    def test_notes_can_be_cleared(self):
        self.client.force_login(self.owner)
        self.client.post(self.url, {'lab_notes': ''})
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.lab_notes, '')

    def test_too_long_notes_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {'lab_notes': 'x' * 2001})
        self.assertEqual(response.status_code, 200)
        self.assertIn('lab_notes', response.context['notes_form'].errors)
        self.assertContains(response, 'is-invalid')
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.lab_notes, 'first notes')

    def test_only_notes_can_change(self):
        failed = make_attempt(self.owner, staph(), protocol_steps(decolorizer=40))
        self.client.force_login(self.owner)
        self.client.post(reverse('simulator:attempt_notes', args=[failed.pk]), {
            'lab_notes': 'ok', 'score': 100, 'is_passed': 'on', 'outcome_diagnosis': 'Perfect',
        })
        failed.refresh_from_db()
        self.assertEqual(failed.lab_notes, 'ok')
        self.assertLess(failed.score, 100)
        self.assertFalse(failed.is_passed)
        self.assertIn('Over-decolorized', failed.outcome_diagnosis)

    def test_other_learner_cannot_edit(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url, {'lab_notes': 'hijacked'})
        self.assertEqual(response.status_code, 404)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.lab_notes, 'first notes')

    def test_admin_forbidden_get_not_allowed_anonymous_redirected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(self.url, {'lab_notes': 'x'}).status_code, 403)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        response = self.client.post(self.url, {'lab_notes': 'x'})
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={quote(self.url)}",
                             fetch_redirect_response=False)
