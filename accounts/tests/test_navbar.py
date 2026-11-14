from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'pw-Test-123'


class NavbarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user('lea', 'lea@example.com', PASSWORD)
        cls.lab_admin = User.objects.create_user(
            'curator', 'curator@example.com', PASSWORD, role=User.Role.ADMIN
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

    def test_learner_links(self):
        html = self.nav_html(self.learner)
        learner_url = reverse('dashboard:learner')
        for anchor in ('#quick-start', '#modules', '#stats'):
            self.assertIn(f'{learner_url}{anchor}', html)
        self.assertIn('Playground', html)
        self.assertNotIn(reverse('dashboard:admin'), html)
        self.assertNotIn('Lab Management', html)

    def test_lab_admin_links(self):
        html = self.nav_html(self.lab_admin)
        admin_url = reverse('dashboard:admin')
        for anchor in ('#catalog', '#scenarios', '#engagement'):
            self.assertIn(f'{admin_url}{anchor}', html)
        self.assertIn('Lab Management', html)
        self.assertNotIn(reverse('dashboard:learner'), html)
        self.assertNotIn('Quick start', html)

    def test_admin_site_link_only_for_staff(self):
        admin_site_link = f'href="{reverse("admin:index")}"'
        self.assertNotIn(admin_site_link, self.nav_html(self.lab_admin))
        self.lab_admin.is_staff = True
        self.lab_admin.save()
        self.assertIn(admin_site_link, self.nav_html(self.lab_admin))

    def test_role_badge(self):
        html = self.nav_html(self.learner)
        self.assertIn('text-bg-info', html)
        self.assertIn('Learner', html)
        self.client.logout()
        html = self.nav_html(self.lab_admin)
        self.assertIn('text-bg-warning', html)
        self.assertIn('Lab Admin', html)

    def test_account_menu(self):
        html = self.nav_html(self.learner)
        self.assertIn(reverse('accounts:profile'), html)
        self.assertIn(reverse('accounts:profile_edit'), html)
        self.assertIn(reverse('accounts:password_change'), html)
        self.assertIn('/static/img/default-avatar.svg', html)
        self.assertIn(f'<form method="post" action="{reverse("accounts:logout")}">', html)
