from urllib.parse import quote

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'Gr4mStain!Violet'


class StudentDashboardTests(TestCase):
    url = reverse('dashboard:student')

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            'stud', 'stud@example.com', PASSWORD, first_name='Lea'
        )
        cls.instructor = User.objects.create_user(
            'inst', 'inst@example.com', PASSWORD, role=User.Role.INSTRUCTOR
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        expected = f"{reverse('accounts:login')}?next={quote(self.url)}"
        self.assertRedirects(response, expected)

    def test_student_sees_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/student.html')
        self.assertContains(response, 'Welcome, Lea!')

    def test_shows_both_modules_and_progress(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertContains(response, 'Gram Staining')
        self.assertContains(response, 'Quadrant Streak Plating')
        self.assertContains(response, 'Crystal violet (primary stain)')
        self.assertContains(response, 'Practice progress')
        self.assertEqual(len(response.context['modules']), 2)
        self.assertTrue(all(m['progress'] == 0 for m in response.context['modules']))

    def test_instructor_is_forbidden(self):
        self.client.force_login(self.instructor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')


class DashboardRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user('stud', 'stud@example.com', PASSWORD)

    def test_dashboard_home_requires_login(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_dashboard_home_sends_student_to_student_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard:home'))
        self.assertRedirects(response, reverse('dashboard:student'))

    def test_dashboard_home_sends_instructor_to_instructor_dashboard(self):
        instructor = User.objects.create_user(
            'inst', 'inst@example.com', PASSWORD, role=User.Role.INSTRUCTOR
        )
        self.client.force_login(instructor)
        response = self.client.get(reverse('dashboard:home'))
        self.assertRedirects(response, reverse('dashboard:instructor'))

    def test_instructor_login_lands_on_instructor_dashboard(self):
        User.objects.create_user('inst', 'inst@example.com', PASSWORD, role=User.Role.INSTRUCTOR)
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'inst', 'password': PASSWORD},
            follow=True,
        )
        self.assertRedirects(response, reverse('dashboard:instructor'))

    def test_student_login_lands_on_student_dashboard(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'stud', 'password': PASSWORD},
            follow=True,
        )
        self.assertRedirects(response, reverse('dashboard:student'))
        self.assertContains(response, 'Welcome back')


class InstructorDashboardTests(TestCase):
    url = reverse('dashboard:instructor')

    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(
            'inst', 'inst@example.com', PASSWORD,
            first_name='Maria', last_name='Cruz', role=User.Role.INSTRUCTOR,
        )
        cls.student = User.objects.create_user(
            'stud', 'stud@example.com', PASSWORD, first_name='Lea', last_name='Santos'
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(self.url)
        expected = f"{reverse('accounts:login')}?next={quote(self.url)}"
        self.assertRedirects(response, expected)

    def test_student_is_forbidden(self):
        """Vertical privilege escalation attempt via URL manipulation."""
        self.client.force_login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')
        self.assertNotContains(response, 'Student roster', status_code=403)

    def test_instructor_sees_all_sections(self):
        self.client.force_login(self.instructor)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/instructor.html')
        for text in ('Student roster', 'Lab module management', 'Performance overview',
                     'Gram Staining', 'Quadrant Streak Plating'):
            self.assertContains(response, text)

    def test_roster_lists_students_only(self):
        self.client.force_login(self.instructor)
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['students']), [self.student])
        self.assertContains(response, 'stud@example.com')
        self.assertNotContains(response, 'inst@example.com')

    def test_stats(self):
        User.objects.create_user('old', 'old@example.com', PASSWORD)
        self.client.force_login(self.student)  # gives the student a recent last_login
        self.client.logout()
        self.client.force_login(self.instructor)
        stats = self.client.get(self.url).context['stats']
        self.assertEqual(stats['total_students'], 2)
        self.assertEqual(stats['active_this_week'], 1)  # only "stud" has logged in
        self.assertEqual(stats['new_this_month'], 2)
        self.assertEqual(stats['modules'], 2)

    def test_search_filters_roster(self):
        User.objects.create_user('juan', 'juan@example.com', PASSWORD, first_name='Juan')
        self.client.force_login(self.instructor)
        response = self.client.get(self.url, {'q': 'juan'})
        self.assertEqual([u.username for u in response.context['students']], ['juan'])
        self.assertContains(response, '1 result for')

        response = self.client.get(self.url, {'q': 'SANTOS'})
        self.assertEqual([u.username for u in response.context['students']], ['stud'])

    def test_search_cannot_reveal_instructors(self):
        self.client.force_login(self.instructor)
        response = self.client.get(self.url, {'q': 'inst'})
        self.assertEqual(list(response.context['students']), [])
        self.assertContains(response, 'No students match')

    def test_roster_is_paginated(self):
        for i in range(12):
            User.objects.create_user(f'extra{i:02}', f'extra{i}@example.com', PASSWORD)
        self.client.force_login(self.instructor)
        page1 = self.client.get(self.url)
        self.assertTrue(page1.context['is_paginated'])
        self.assertEqual(len(page1.context['students']), 10)
        page2 = self.client.get(self.url, {'page': 2})
        self.assertEqual(len(page2.context['students']), 3)

    def test_pagination_links_keep_search(self):
        for i in range(12):
            User.objects.create_user(f'lab{i:02}', f'lab{i}@example.com', PASSWORD)
        self.client.force_login(self.instructor)
        response = self.client.get(self.url, {'q': 'lab'})
        self.assertContains(response, '?q=lab&amp;page=2')
