from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User

OLD = 'Old-Passw0rd!Lab'
NEW = 'New-Passw0rd!Bench'


class PasswordChangeTests(TestCase):
    url = reverse('accounts:password_change')

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('ana', 'ana@example.com', OLD)

    def setUp(self):
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/password_change.html')

    def test_change_password_success(self):
        response = self.client.post(self.url, {
            'old_password': OLD, 'new_password1': NEW, 'new_password2': NEW,
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))
        self.assertIn('Your password has been changed.',
                      [m.message for m in get_messages(response.wsgi_request)])
        # Still signed in on this device.
        self.assertEqual(self.client.get(reverse('accounts:profile')).status_code, 200)

    def test_other_sessions_are_signed_out(self):
        other_device = Client()
        other_device.force_login(self.user)
        self.client.post(self.url, {
            'old_password': OLD, 'new_password1': NEW, 'new_password2': NEW,
        })
        response = other_device.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)

    def test_wrong_old_password(self):
        response = self.client.post(self.url, {
            'old_password': 'nope', 'new_password1': NEW, 'new_password2': NEW,
        })
        self.assertIn('old_password', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(OLD))

    def test_mismatch_and_weak_passwords_rejected(self):
        response = self.client.post(self.url, {
            'old_password': OLD, 'new_password1': NEW, 'new_password2': NEW + 'x',
        })
        self.assertIn('new_password2', response.context['form'].errors)

        response = self.client.post(self.url, {
            'old_password': OLD, 'new_password1': '12345678', 'new_password2': '12345678',
        })
        self.assertIn('new_password2', response.context['form'].errors)
        self.assertTrue(any('not changed' in m.message for m in get_messages(response.wsgi_request)))

    def test_linked_from_navbar_and_profile(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertContains(response, self.url, count=2)
