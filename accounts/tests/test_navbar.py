from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'pw-Test-123'


class NavbarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user('stud', 'stud@example.com', PASSWORD)
        cls.instructor = User.objects.create_user(
            'inst', 'inst@example.com', PASSWORD, role=User.Role.INSTRUCTOR
        )

    def nav_html(self, user=None):
        if user:
            self.client.force_login(user)
        return self.client.get(reverse('home')).content.decode()

    def test_anonymous_sees_sign_in_and_register(self):
        html = self.nav_html()
        self.assertIn(reverse('accounts:login'), html)
        self.assertIn(reverse('accounts:register'), html)
        self.assertNotIn('My profile', html)
        self.assertNotIn(reverse('accounts:logout'), html)

    def test_student_links(self):
        html = self.nav_html(self.student)
        self.assertIn(f"{reverse('dashboard:student')}#modules", html)
        self.assertIn(f"{reverse('dashboard:student')}#progress", html)
        self.assertIn('My progress', html)
        self.assertNotIn(reverse('dashboard:instructor'), html)
        self.assertNotIn('Student roster', html)
        self.assertNotIn('Performance', html)

    def test_instructor_links(self):
        html = self.nav_html(self.instructor)
        self.assertIn(f"{reverse('dashboard:instructor')}#roster", html)
        self.assertIn(f"{reverse('dashboard:instructor')}#modules", html)
        self.assertIn(f"{reverse('dashboard:instructor')}#performance", html)
        self.assertNotIn(reverse('dashboard:student'), html)
        self.assertNotIn('My progress', html)

    def test_admin_link_only_for_staff_instructors(self):
        self.assertNotIn(reverse('admin:index'), self.nav_html(self.instructor))
        self.instructor.is_staff = True
        self.instructor.save()
        self.assertIn(reverse('admin:index'), self.nav_html(self.instructor))

    def test_role_badge(self):
        self.assertIn('text-bg-info', self.nav_html(self.student))
        self.client.logout()
        self.assertIn('text-bg-warning', self.nav_html(self.instructor))

    def test_account_menu(self):
        html = self.nav_html(self.student)
        self.assertIn(reverse('accounts:profile'), html)
        self.assertIn(reverse('accounts:profile_edit'), html)
        self.assertIn('/static/img/default-avatar.svg', html)
        self.assertIn(f'<form method="post" action="{reverse("accounts:logout")}">', html)
