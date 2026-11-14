from django.conf import settings
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'Str3ak!Plate#Agar'


class LoginTests(TestCase):
    url = reverse('accounts:login')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            'labstudent', 'student@example.com', PASSWORD, first_name='Lea'
        )

    def logged_in_user_id(self):
        user_id = self.client.session.get('_auth_user_id')
        return int(user_id) if user_id else None

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_login_with_username(self):
        response = self.client.post(self.url, {'username': 'labstudent', 'password': PASSWORD})
        self.assertRedirects(response, reverse(settings.LOGIN_REDIRECT_URL), fetch_redirect_response=False)
        self.assertEqual(self.logged_in_user_id(), self.user.pk)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn('Welcome back, Lea!', messages)

    def test_login_with_email_case_insensitive(self):
        self.client.post(self.url, {'username': 'STUDENT@Example.com', 'password': PASSWORD})
        self.assertEqual(self.logged_in_user_id(), self.user.pk)

    def test_wrong_password_shows_error(self):
        response = self.client.post(self.url, {'username': 'labstudent', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username/email or password')
        self.assertIsNone(self.logged_in_user_id())

    def test_unknown_user_shows_same_error(self):
        response = self.client.post(self.url, {'username': 'nobody', 'password': PASSWORD})
        self.assertContains(response, 'Invalid username/email or password')

    def test_empty_form_shows_field_errors(self):
        response = self.client.post(self.url, {})
        self.assertIn('username', response.context['form'].errors)
        self.assertIn('password', response.context['form'].errors)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(self.url, {'username': 'labstudent', 'password': PASSWORD})
        self.assertIsNone(self.logged_in_user_id())

    def test_without_remember_me_session_ends_on_browser_close(self):
        self.client.post(self.url, {'username': 'labstudent', 'password': PASSWORD})
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_with_remember_me_session_persists(self):
        self.client.post(self.url, {
            'username': 'labstudent', 'password': PASSWORD, 'remember_me': 'on',
        })
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_external_next_url_is_ignored(self):
        response = self.client.post(self.url, {
            'username': 'labstudent', 'password': PASSWORD,
            'next': 'https://evil.example.com/',
        })
        self.assertNotIn('evil.example.com', response['Location'])

    def test_authenticated_user_is_redirected_away(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 302)


class LogoutTests(TestCase):
    url = reverse('accounts:logout')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('labstudent', 'student@example.com', PASSWORD)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_post_ends_session_and_redirects_to_login(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse(settings.LOGOUT_REDIRECT_URL))
        self.assertNotIn('_auth_user_id', self.client.session)
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('signed out' in m for m in messages))

    def test_post_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertIn('_auth_user_id', client.session)

    def test_navbar_logout_is_a_post_form(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('home'))
        self.assertContains(response, f'<form method="post" action="{self.url}">', html=False)
