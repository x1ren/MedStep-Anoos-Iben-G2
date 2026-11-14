from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

STRONG_PASSWORD = 'Gr4mStain!Violet'


def valid_payload(**overrides):
    data = {
        'first_name': 'Ana',
        'last_name': 'Reyes',
        'username': 'anareyes',
        'email': 'Ana.Reyes@Example.com',
        'contact_number': '+63 912 345 6789',
        'password1': STRONG_PASSWORD,
        'password2': STRONG_PASSWORD,
    }
    data.update(overrides)
    return data


def message_texts(response):
    return [m.message for m in get_messages(response.wsgi_request)]


class RegistrationTests(TestCase):
    url = reverse('accounts:register')

    def test_page_renders(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_successful_registration_creates_hashed_student(self):
        response = self.client.post(self.url, valid_payload())
        self.assertRedirects(response, reverse('accounts:login'))

        user = User.objects.get(username='anareyes')
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertEqual(user.email, 'ana.reyes@example.com')
        self.assertEqual(user.contact_number, '+63 912 345 6789')
        self.assertNotEqual(user.password, STRONG_PASSWORD)
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertTrue(any('created successfully' in m for m in message_texts(response)))

    def test_contact_number_is_optional(self):
        self.client.post(self.url, valid_payload(contact_number=''))
        self.assertTrue(User.objects.filter(username='anareyes').exists())

    def test_role_cannot_be_escalated_via_post(self):
        self.client.post(self.url, valid_payload(role='admin'))
        self.assertEqual(User.objects.get(username='anareyes').role, User.Role.LEARNER)

    def test_required_fields(self):
        response = self.client.post(self.url, {})
        form = response.context['form']
        for field in ('first_name', 'last_name', 'username', 'email', 'password1', 'password2'):
            self.assertIn(field, form.errors, field)
        self.assertNotIn('contact_number', form.errors)
        self.assertFalse(User.objects.exists())

    def test_blank_names_rejected(self):
        response = self.client.post(self.url, valid_payload(first_name='   ', last_name=''))
        self.assertIn('first_name', response.context['form'].errors)
        self.assertIn('last_name', response.context['form'].errors)

    def test_invalid_email_format(self):
        response = self.client.post(self.url, valid_payload(email='not-an-email'))
        self.assertIn('email', response.context['form'].errors)

    def test_duplicate_username_rejected(self):
        User.objects.create_user('anareyes', 'other@example.com', STRONG_PASSWORD)
        response = self.client.post(self.url, valid_payload())
        self.assertIn('username', response.context['form'].errors)

    def test_duplicate_email_rejected_case_insensitive(self):
        User.objects.create_user('someone', 'ana.reyes@example.com', STRONG_PASSWORD)
        response = self.client.post(self.url, valid_payload(email='ANA.REYES@example.com'))
        self.assertEqual(
            response.context['form'].errors['email'],
            ['An account with this email already exists.'],
        )
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch(self):
        response = self.client.post(self.url, valid_payload(password2='Different!Pass99'))
        self.assertIn('password2', response.context['form'].errors)

    def test_weak_password_rejected(self):
        response = self.client.post(
            self.url, valid_payload(password1='12345678', password2='12345678')
        )
        self.assertIn('password2', response.context['form'].errors)

    def test_invalid_contact_number(self):
        response = self.client.post(self.url, valid_payload(contact_number='call me'))
        self.assertIn('contact_number', response.context['form'].errors)

    def test_failure_shows_error_message_and_highlights_fields(self):
        response = self.client.post(self.url, valid_payload(email='bad'))
        self.assertTrue(any('Registration failed' in m for m in message_texts(response)))
        self.assertContains(response, 'is-invalid')
        self.assertContains(response, 'Enter a valid email address.')

    def test_authenticated_user_is_redirected_away(self):
        user = User.objects.create_user('anareyes', 'ana@example.com', STRONG_PASSWORD)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
