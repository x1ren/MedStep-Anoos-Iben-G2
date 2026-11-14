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

    def test_student_login_lands_on_student_dashboard(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'stud', 'password': PASSWORD},
            follow=True,
        )
        self.assertRedirects(response, reverse('dashboard:student'))
        self.assertContains(response, 'Welcome back')
