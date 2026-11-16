from urllib.parse import quote

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from simulator.models import GramStainScenario

PASSWORD = 'Gr4mStain!Violet'


def make_learner(username='lea', **extra):
    return User.objects.create_user(username, f'{username}@example.com', PASSWORD, **extra)


def make_admin(username='curator', **extra):
    return User.objects.create_user(
        username, f'{username}@example.com', PASSWORD, role=User.Role.ADMIN, **extra
    )


class DashboardRedirectTests(TestCase):
    def test_requires_login(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_learner_redirected_to_learner_dashboard(self):
        self.client.force_login(make_learner())
        self.assertRedirects(self.client.get(reverse('dashboard:home')), reverse('dashboard:learner'))

    def test_admin_redirected_to_admin_dashboard(self):
        self.client.force_login(make_admin())
        self.assertRedirects(self.client.get(reverse('dashboard:home')), reverse('dashboard:admin'))

    def test_learner_login_lands_on_learner_dashboard(self):
        make_learner()
        response = self.client.post(
            reverse('accounts:login'), {'username': 'lea', 'password': PASSWORD}, follow=True
        )
        self.assertRedirects(response, reverse('dashboard:learner'))
        self.assertContains(response, 'Welcome back')

    def test_admin_login_lands_on_admin_dashboard(self):
        make_admin()
        response = self.client.post(
            reverse('accounts:login'), {'username': 'curator', 'password': PASSWORD}, follow=True
        )
        self.assertRedirects(response, reverse('dashboard:admin'))

    def test_old_dashboard_urls_are_gone(self):
        self.client.force_login(make_learner())
        for url in ('/dashboard/student/', '/dashboard/instructor/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)


class LearnerDashboardTests(TestCase):
    url = reverse('dashboard:learner')

    @classmethod
    def setUpTestData(cls):
        cls.learner = make_learner(first_name='Lea')
        cls.admin = make_admin()

    def test_url(self):
        self.assertEqual(self.url, '/dashboard/learner/')

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={quote(self.url)}")

    def test_admin_is_forbidden(self):
        """Horizontal escalation: Lab Admin opening the learner-only page."""
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')

    def test_learner_sees_playground(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/learner.html')
        for text in ('Student Playground', 'Welcome, Lea!', 'Quick start',
                     'Gram Staining', 'Quadrant Streak Plating', 'My simulation stats'):
            self.assertContains(response, text)

    def test_quick_start_cards(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['quick_starts']), 3)
        self.assertContains(response, 'Decolorizer timing drill')

    def test_personal_stats_start_at_zero(self):
        self.client.force_login(self.learner)
        stats = self.client.get(self.url).context['stats']
        self.assertEqual(stats['sessions'], 0)
        self.assertEqual(stats['modules_completed'], 0)
        self.assertEqual(stats['modules_available'], 2)
        self.assertIsNone(stats['best_score'])

    def test_does_not_leak_admin_content(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        self.assertNotContains(response, 'Bacterial specimens')
        self.assertNotContains(response, 'curator@example.com')


class AdminDashboardTests(TestCase):
    url = reverse('dashboard:admin')

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_admin(first_name='Maria', last_name='Cruz')
        cls.learner = make_learner(first_name='Lea', last_name='Santos')

    def test_url(self):
        self.assertEqual(self.url, '/dashboard/admin/')

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={quote(self.url)}")

    def test_learner_is_forbidden(self):
        """Vertical escalation: learner typing the Lab Admin URL."""
        self.client.force_login(self.learner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertContains(
            response, 'restricted to Lab Admin / Content Curator accounts', status_code=403
        )
        self.assertNotContains(response, 'Active lab scenarios', status_code=403)

    def test_admin_sees_all_sections(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/admin.html')
        for text in ('Lab Management Dashboard', 'Catalog overview', 'Bacterial specimens',
                     'Active lab scenarios', 'Learner activity', 'Staphylococcus aureus'):
            self.assertContains(response, text)
        self.assertContains(response, reverse('simulator:scenario_list'))
        self.assertContains(response, reverse('simulator:scenario_create'))

    def test_catalog_overview_counts_come_from_database(self):
        GramStainScenario.objects.filter(title='Practice #2: Escherichia coli').update(is_active=False)
        self.client.force_login(self.admin)
        catalog = self.client.get(self.url).context['catalog']
        self.assertEqual(catalog['modules'], 2)
        self.assertEqual(catalog['scenarios'], 3)
        self.assertEqual(catalog['active_scenarios'], 2)
        self.assertEqual(catalog['hidden_scenarios'], 1)
        self.assertEqual(catalog['gram_positive'], 2)
        self.assertEqual(catalog['gram_negative'], 1)
        self.assertEqual(catalog['specimens'], 3)

    def test_new_scenario_appears_immediately(self):
        GramStainScenario.objects.create(
            title='Practice #3: Pseudomonas aeruginosa', specimen_name='Pseudomonas aeruginosa',
            gram_type='gram_negative', cell_shape='bacilli',
        )
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.context['catalog']['scenarios'], 4)
        self.assertContains(response, 'Practice #3: Pseudomonas aeruginosa')
        self.assertContains(response, 'Gram-Negative Bacilli (Pink)')

    def test_specimens_are_distinct(self):
        GramStainScenario.objects.create(
            title='Another E. coli smear', specimen_name='Escherichia coli',
            gram_type='gram_negative', cell_shape='bacilli',
        )
        self.client.force_login(self.admin)
        specimens = list(self.client.get(self.url).context['specimens'])
        self.assertEqual([s['specimen_name'] for s in specimens],
                         ['Bacillus cereus', 'Escherichia coli', 'Staphylococcus aureus'])

    def test_only_active_scenarios_listed(self):
        unknown = GramStainScenario.objects.get(title='Unknown Clinical Smear')
        unknown.is_active = False
        unknown.save()
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        listed = [s.title for s in response.context['active_scenarios']]
        self.assertEqual(listed, ['Practice #1: Staphylococcus aureus', 'Practice #2: Escherichia coli'])
        practice1 = GramStainScenario.objects.get(title='Practice #1: Staphylococcus aureus')
        self.assertContains(response, reverse('simulator:scenario_update', args=[practice1.pk]))
        self.assertNotContains(response, reverse('simulator:scenario_update', args=[unknown.pk]))
        self.assertContains(response, '1 hidden scenario not visible to learners')

    def test_empty_catalog(self):
        GramStainScenario.objects.all().delete()
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertContains(response, 'learners have nothing to practice yet')
        self.assertContains(response, 'No specimens yet.')

    def test_engagement_metrics(self):
        make_learner('idle')
        self.client.force_login(self.learner)  # gives "lea" a recent last_login
        self.client.logout()
        self.client.force_login(self.admin)
        engagement = self.client.get(self.url).context['engagement']
        self.assertEqual(engagement['total_learners'], 2)
        self.assertEqual(engagement['active_7d'], 1)
        self.assertEqual(engagement['engagement_rate'], 50)
        self.assertEqual(engagement['new_30d'], 2)
        self.assertEqual(engagement['lab_admins'], 1)

    def test_engagement_rate_with_no_learners(self):
        User.objects.filter(role=User.Role.LEARNER).delete()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url).context['engagement']['engagement_rate'], 0)

    def test_learner_list_excludes_admins(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['learners']), [self.learner])
        self.assertContains(response, '>@lea</div>')
        self.assertNotContains(response, '>@curator</div>')

    def test_search(self):
        make_learner('juan', first_name='Juan')
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'q': 'juan'})
        self.assertEqual([u.username for u in response.context['learners']], ['juan'])
        response = self.client.get(self.url, {'q': 'SANTOS'})
        self.assertEqual([u.username for u in response.context['learners']], ['lea'])
        response = self.client.get(self.url, {'q': 'curator'})
        self.assertEqual(list(response.context['learners']), [])
        self.assertContains(response, 'No learners match')

    def test_pagination_keeps_search(self):
        for i in range(12):
            make_learner(f'lab{i:02}')
        self.client.force_login(self.admin)
        response = self.client.get(self.url, {'q': 'lab'})
        self.assertEqual(len(response.context['learners']), 10)
        self.assertContains(response, '?q=lab&amp;page=2#engagement')
        page2 = self.client.get(self.url, {'q': 'lab', 'page': 2})
        self.assertEqual(len(page2.context['learners']), 2)
