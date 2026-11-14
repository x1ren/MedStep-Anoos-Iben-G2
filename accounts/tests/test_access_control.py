from urllib.parse import quote

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.decorators import role_required
from accounts.models import User

PASSWORD = 'pw-Test-123'


@override_settings(ROOT_URLCONF='accounts.tests.role_urls')
class RoleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user('stud', 'stud@example.com', PASSWORD)
        cls.instructor = User.objects.create_user(
            'inst', 'inst@example.com', PASSWORD, role=User.Role.ADMIN
        )

    def assert_redirects_to_login(self, url):
        response = self.client.get(url)
        expected = f"{reverse('accounts:login')}?next={quote(url)}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)

    # --- anonymous users -------------------------------------------------
    def test_anonymous_redirected_to_login(self):
        for url in ('/t/student/', '/t/instructor/', '/t/any/', '/t/instructor-cbv/'):
            with self.subTest(url=url):
                self.assert_redirects_to_login(url)

    # --- correct role ----------------------------------------------------
    def test_student_can_open_student_area(self):
        self.client.force_login(self.student)
        self.assertContains(self.client.get('/t/student/'), 'student area')

    def test_instructor_can_open_instructor_areas(self):
        self.client.force_login(self.instructor)
        self.assertContains(self.client.get('/t/instructor/'), 'instructor area')
        self.assertContains(self.client.get('/t/instructor-cbv/'), 'instructor cbv')

    def test_multi_role_view_allows_both(self):
        for user in (self.student, self.instructor):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertContains(self.client.get('/t/any/'), 'shared area')

    # --- wrong role (privilege escalation attempts) ------------------------
    def test_student_blocked_from_instructor_area(self):
        """Vertical escalation: student -> instructor."""
        self.client.force_login(self.student)
        for url in ('/t/instructor/', '/t/instructor-cbv/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)
                self.assertTemplateUsed(response, '403.html')
                self.assertNotContains(response, 'instructor area', status_code=403)

    def test_instructor_blocked_from_student_area(self):
        """Horizontal escalation: instructor -> student-only page."""
        self.client.force_login(self.instructor)
        response = self.client.get('/t/student/')
        self.assertEqual(response.status_code, 403)

    def test_403_page_explains_why(self):
        self.client.force_login(self.student)
        response = self.client.get('/t/instructor/')
        self.assertContains(
            response, 'restricted to Lab Admin / Content Curator accounts', status_code=403
        )
        self.assertContains(response, 'stud', status_code=403)

    def test_role_change_takes_effect_immediately(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get('/t/instructor/').status_code, 403)
        self.student.role = User.Role.ADMIN
        self.student.save()
        self.assertEqual(self.client.get('/t/instructor/').status_code, 200)


class RoleRequiredConfigTests(TestCase):
    def test_requires_at_least_one_role(self):
        with self.assertRaises(ValueError):
            role_required()

    def test_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            role_required('instuctor')
