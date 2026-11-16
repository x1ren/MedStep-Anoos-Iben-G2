from urllib.parse import quote

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from simulator.models import GramStainScenario

PASSWORD = 'pw-Test-123'


def scenario_payload(**overrides):
    data = {
        'title': 'Practice #3: Pseudomonas aeruginosa',
        'specimen_name': 'Pseudomonas aeruginosa',
        'gram_type': 'gram_negative',
        'cell_shape': 'bacilli',
        'difficulty': 'intermediate',
        'description': 'Rods from a wound swab.',
        'crystal_violet_seconds': 60,
        'iodine_seconds': 60,
        'decolorizer_seconds': 15,
        'safranin_seconds': 45,
        'is_active': 'on',
    }
    data.update(overrides)
    return data


def messages_of(response):
    return [m.message for m in get_messages(response.wsgi_request)]


class ScenarioAdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            'curator', 'curator@example.com', PASSWORD, role=User.Role.ADMIN
        )
        cls.learner = User.objects.create_user('lea', 'lea@example.com', PASSWORD)
        cls.seeded = GramStainScenario.objects.get(title='Practice #2: Escherichia coli')

    def urls(self):
        return {
            'list': reverse('simulator:scenario_list'),
            'create': reverse('simulator:scenario_create'),
            'update': reverse('simulator:scenario_update', args=[self.seeded.pk]),
        }


class ScenarioAccessTests(ScenarioAdminTestCase):
    def test_anonymous_redirected_to_login(self):
        for name, url in self.urls().items():
            with self.subTest(page=name):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('accounts:login')}?next={quote(url)}")

    def test_learner_forbidden_everywhere(self):
        self.client.force_login(self.learner)
        for name, url in self.urls().items():
            with self.subTest(page=name):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_learner_cannot_create_or_edit_by_post(self):
        self.client.force_login(self.learner)
        response = self.client.post(self.urls()['create'], scenario_payload())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(GramStainScenario.objects.filter(specimen_name='Pseudomonas aeruginosa').exists())

        response = self.client.post(self.urls()['update'], scenario_payload(title='Hacked'))
        self.assertEqual(response.status_code, 403)
        self.seeded.refresh_from_db()
        self.assertEqual(self.seeded.title, 'Practice #2: Escherichia coli')


class ScenarioListTests(ScenarioAdminTestCase):
    def test_lists_all_scenarios_including_hidden(self):
        GramStainScenario.objects.filter(pk=self.seeded.pk).update(is_active=False)
        self.client.force_login(self.admin)
        response = self.client.get(self.urls()['list'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['scenarios']), 3)
        self.assertContains(response, 'Unknown Clinical Smear')
        self.assertContains(response, 'Hidden')
        self.assertContains(response, 'Starter seed')
        self.assertContains(response, self.urls()['update'])


class ScenarioCreateTests(ScenarioAdminTestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_form_renders_with_defaults(self):
        response = self.client.get(self.urls()['create'])
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/scenario_form.html')
        self.assertEqual(response.context['form']['decolorizer_seconds'].value(), 15)

    def test_create_sets_author_and_shows_message(self):
        response = self.client.post(self.urls()['create'], scenario_payload())
        self.assertRedirects(response, self.urls()['list'])
        scenario = GramStainScenario.objects.get(title='Practice #3: Pseudomonas aeruginosa')
        self.assertEqual(scenario.created_by, self.admin)
        self.assertEqual(scenario.difficulty, 'intermediate')
        self.assertTrue(scenario.is_active)
        self.assertIn('Scenario "Practice #3: Pseudomonas aeruginosa" was created.', messages_of(response))

    def test_created_by_cannot_be_forged(self):
        self.client.post(self.urls()['create'], scenario_payload(created_by=self.learner.pk))
        scenario = GramStainScenario.objects.get(title='Practice #3: Pseudomonas aeruginosa')
        self.assertEqual(scenario.created_by, self.admin)

    def test_unchecked_active_creates_hidden_scenario(self):
        payload = scenario_payload()
        del payload['is_active']
        self.client.post(self.urls()['create'], payload)
        self.assertFalse(GramStainScenario.objects.get(specimen_name='Pseudomonas aeruginosa').is_active)

    def test_required_fields(self):
        response = self.client.post(self.urls()['create'], {})
        errors = response.context['form'].errors
        for field in ('title', 'specimen_name', 'gram_type', 'cell_shape'):
            self.assertIn(field, errors)
        self.assertNotIn('description', errors)
        self.assertTrue(any('not saved' in m for m in messages_of(response)))
        self.assertContains(response, 'is-invalid')

    def test_duplicate_title_case_insensitive(self):
        response = self.client.post(
            self.urls()['create'], scenario_payload(title='practice #2: escherichia COLI')
        )
        self.assertEqual(
            response.context['form'].errors['title'], ['A scenario with this title already exists.']
        )

    def test_invalid_choices_rejected(self):
        response = self.client.post(
            self.urls()['create'], scenario_payload(gram_type='gram_purple', cell_shape='spirilla')
        )
        self.assertIn('gram_type', response.context['form'].errors)
        self.assertIn('cell_shape', response.context['form'].errors)

    def test_timing_limits(self):
        response = self.client.post(self.urls()['create'], scenario_payload(
            crystal_violet_seconds=0, decolorizer_seconds=121, safranin_seconds=-5, iodine_seconds='abc',
        ))
        errors = response.context['form'].errors
        for field in ('crystal_violet_seconds', 'decolorizer_seconds', 'safranin_seconds', 'iodine_seconds'):
            self.assertIn(field, errors)
        self.assertEqual(GramStainScenario.objects.count(), 3)


class ScenarioUpdateTests(ScenarioAdminTestCase):
    def setUp(self):
        self.client.force_login(self.admin)

    def test_form_prefilled(self):
        response = self.client.get(self.urls()['update'])
        self.assertEqual(response.context['form'].instance, self.seeded)
        self.assertContains(response, 'Practice #2: Escherichia coli')

    def test_update_saves_and_keeps_author(self):
        response = self.client.post(self.urls()['update'], scenario_payload(
            title='Practice #2: Escherichia coli', specimen_name='Escherichia coli',
            decolorizer_seconds=12, difficulty='challenge',
        ))
        self.assertRedirects(response, self.urls()['list'])
        self.seeded.refresh_from_db()
        self.assertEqual(self.seeded.decolorizer_seconds, 12)
        self.assertEqual(self.seeded.difficulty, 'challenge')
        self.assertIsNone(self.seeded.created_by)  # editing does not claim authorship
        self.assertIn('Scenario "Practice #2: Escherichia coli" was updated.', messages_of(response))

    def test_keeping_own_title_is_allowed(self):
        response = self.client.post(self.urls()['update'], scenario_payload(
            title='PRACTICE #2: Escherichia coli',
        ))
        self.assertRedirects(response, self.urls()['list'])

    def test_cannot_rename_to_another_scenarios_title(self):
        response = self.client.post(self.urls()['update'], scenario_payload(title='Unknown Clinical Smear'))
        self.assertIn('title', response.context['form'].errors)

    def test_hide_scenario(self):
        payload = scenario_payload(title=self.seeded.title)
        del payload['is_active']
        self.client.post(self.urls()['update'], payload)
        self.seeded.refresh_from_db()
        self.assertFalse(self.seeded.is_active)

    def test_missing_scenario_is_404(self):
        response = self.client.get(reverse('simulator:scenario_update', args=[99999]))
        self.assertEqual(response.status_code, 404)
