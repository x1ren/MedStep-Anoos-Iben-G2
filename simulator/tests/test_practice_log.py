from datetime import timedelta
from urllib.parse import quote

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from simulator.models import GramStainScenario, SimulationAttempt
from simulator.tests.factories import (
    ecoli,
    make_admin,
    make_attempt,
    make_learner,
    protocol_steps,
    staph,
)


class PracticeLogTests(TestCase):
    """Read: each learner sees only their own attempts."""

    url = reverse('simulator:attempt_list')

    @classmethod
    def setUpTestData(cls):
        cls.learner = make_learner()
        cls.other = make_learner('bob')
        cls.admin = make_admin()
        cls.staph, cls.ecoli = staph(), ecoli()
        cls.old_pass = make_attempt(cls.learner, cls.staph)
        cls.new_fail = make_attempt(cls.learner, cls.ecoli, protocol_steps(decolorizer=3))
        SimulationAttempt.objects.filter(pk=cls.old_pass.pk).update(
            completed_at=timezone.now() - timedelta(days=2)
        )
        cls.others_attempt = make_attempt(cls.other, cls.staph, lab_notes='bob private')

    def setUp(self):
        self.client.force_login(self.learner)

    def test_access(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get(self.url),
                             f"{reverse('accounts:login')}?next={quote(self.url)}")

    def test_lists_only_own_attempts_newest_first(self):
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['attempts']), [self.new_fail, self.old_pass])
        self.assertNotContains(response, self.others_attempt.get_absolute_url())

    def test_summary(self):
        summary = self.client.get(self.url).context['summary']
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['passed'], 1)
        self.assertEqual(summary['best'], 100)

    def test_filter_by_result(self):
        passed = self.client.get(self.url, {'result': 'passed'}).context['attempts']
        failed = self.client.get(self.url, {'result': 'failed'}).context['attempts']
        self.assertEqual(list(passed), [self.old_pass])
        self.assertEqual(list(failed), [self.new_fail])

    def test_filter_by_scenario(self):
        response = self.client.get(self.url, {'scenario': self.ecoli.pk})
        self.assertEqual(list(response.context['attempts']), [self.new_fail])
        self.assertTrue(response.context['is_filtered'])

    def test_bad_filters_are_ignored(self):
        response = self.client.get(self.url, {'scenario': 'abc', 'result': 'hacked'})
        self.assertEqual(len(response.context['attempts']), 2)
        self.assertFalse(response.context['is_filtered'])

    def test_filter_cannot_reveal_other_users_attempts(self):
        bob_only = make_attempt(self.other, GramStainScenario.objects.get(title='Unknown Clinical Smear'))
        response = self.client.get(self.url, {'scenario': bob_only.scenario_id})
        self.assertEqual(list(response.context['attempts']), [])
        self.assertContains(response, 'No attempts match these filters')

    def test_scenario_choices_only_from_own_attempts(self):
        choices = list(self.client.get(self.url).context['scenario_choices'])
        self.assertEqual(choices, [self.staph, self.ecoli])

    def test_pagination(self):
        for _ in range(11):
            make_attempt(self.learner, self.staph)
        page1 = self.client.get(self.url)
        self.assertEqual(len(page1.context['attempts']), 10)
        self.assertEqual(len(self.client.get(self.url, {'page': 2}).context['attempts']), 3)
        self.assertContains(self.client.get(self.url, {'result': 'passed'}), '?result=passed&amp;page=2')

    def test_empty_log(self):
        self.client.force_login(make_learner('newbie'))
        self.assertContains(self.client.get(self.url), 'Your practice log is empty')


class DeleteAttemptTests(TestCase):
    """Delete: confirmation page, owner-only."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = make_learner()
        cls.other = make_learner('bob')
        cls.admin = make_admin()

    def setUp(self):
        self.attempt = make_attempt(self.owner, staph())
        self.url = reverse('simulator:attempt_delete', args=[self.attempt.pk])

    def test_get_shows_confirmation_without_deleting(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'simulator/attempt_confirm_delete.html')
        self.assertContains(response, 'Yes, delete it')
        self.assertTrue(SimulationAttempt.objects.filter(pk=self.attempt.pk).exists())

    def test_owner_deletes_with_message(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('simulator:attempt_list'))
        self.assertFalse(SimulationAttempt.objects.filter(pk=self.attempt.pk).exists())
        message = [m.message for m in get_messages(response.wsgi_request)][0]
        self.assertIn('Practice #1: Staphylococcus aureus', message)
        self.assertIn('was deleted', message)

    def test_other_learner_gets_404_and_nothing_is_deleted(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertTrue(SimulationAttempt.objects.filter(pk=self.attempt.pk).exists())

    def test_admin_forbidden_anonymous_redirected(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.client.logout()
        response = self.client.post(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={quote(self.url)}",
                             fetch_redirect_response=False)
        self.assertTrue(SimulationAttempt.objects.filter(pk=self.attempt.pk).exists())

    def test_deleting_last_attempt_unlocks_scenario_deletion(self):
        scenario = self.attempt.scenario
        self.client.force_login(self.owner)
        self.client.post(self.url)
        self.client.force_login(self.admin)
        self.client.post(reverse('simulator:scenario_delete', args=[scenario.pk]))
        self.assertFalse(GramStainScenario.objects.filter(pk=scenario.pk).exists())
