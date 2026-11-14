import io
import os
import shutil
import tempfile

from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import User

PASSWORD = 'pw-Test-123'
TEMP_MEDIA = tempfile.mkdtemp(prefix='medstep-test-media-')


def make_image(name='photo.png', fmt='PNG', size=(20, 20), noise=False):
    """Build an in-memory image upload."""
    if noise:
        image = Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3))
    else:
        image = Image.new('RGB', size, color=(13, 122, 114))
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    content_type = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'GIF': 'image/gif'}[fmt]
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def edit_payload(**overrides):
    data = {
        'first_name': 'Ana',
        'last_name': 'Reyes',
        'email': 'ana@example.com',
        'contact_number': '+63 912 345 6789',
    }
    data.update(overrides)
    return data


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ProfileTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            'ana', 'ana@example.com', PASSWORD, first_name='Ana', last_name='Reyes'
        )
        cls.other = User.objects.create_user(
            'bob', 'bob@example.com', PASSWORD, first_name='Bob', last_name='Cruz',
            contact_number='0917 000 0000',
        )

    def setUp(self):
        self.client.force_login(self.user)


class ProfileViewTests(ProfileTestCase):
    url = reverse('accounts:profile')

    def test_requires_login(self):
        self.client.logout()
        for url in (self.url, reverse('accounts:profile_edit')):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTrue(response['Location'].startswith(reverse('accounts:login')))

    def test_shows_own_details(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        for text in ('Ana Reyes', '@ana', 'ana@example.com', 'Student Learner', 'Not provided'):
            self.assertContains(response, text)

    def test_never_shows_another_users_details(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'bob@example.com')
        self.assertNotContains(response, '0917 000 0000')

    def test_default_avatar_when_no_photo(self):
        response = self.client.get(self.url)
        self.assertContains(response, '/static/img/default-avatar.svg')

    def test_no_url_accepts_a_user_id(self):
        """IDOR guard: profiles are only reachable as request.user."""
        for url in (f'/accounts/profile/{self.other.pk}/', '/accounts/profile/bob/',
                    f'/accounts/profile/edit/{self.other.pk}/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)


class ProfileEditTests(ProfileTestCase):
    url = reverse('accounts:profile_edit')

    def test_form_is_prefilled(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].instance, self.user)
        self.assertContains(response, 'value="ana@example.com"')
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_updates_own_details(self):
        response = self.client.post(self.url, edit_payload(
            first_name='Anabelle', email='Anabelle@Example.com', contact_number='0918 111 2222',
        ))
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Anabelle')
        self.assertEqual(self.user.email, 'anabelle@example.com')
        self.assertEqual(self.user.contact_number, '0918 111 2222')
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn('Your profile has been updated.', messages)

    def test_keeping_own_email_is_allowed(self):
        response = self.client.post(self.url, edit_payload(email='ANA@example.com'))
        self.assertRedirects(response, reverse('accounts:profile'))

    def test_cannot_take_another_users_email(self):
        response = self.client.post(self.url, edit_payload(email='BOB@example.com'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'ana@example.com')

    def test_required_fields_and_validation(self):
        response = self.client.post(self.url, edit_payload(
            first_name='', email='not-an-email', contact_number='call me',
        ))
        errors = response.context['form'].errors
        self.assertIn('first_name', errors)
        self.assertIn('email', errors)
        self.assertIn('contact_number', errors)
        self.assertContains(response, 'is-invalid')
        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('not saved' in m for m in messages))

    def test_failed_submit_does_not_alter_logged_in_user(self):
        response = self.client.post(self.url, edit_payload(first_name='Hacked', email='bad'))
        self.assertEqual(response.context['user'].first_name, 'Ana')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana')

    def test_role_username_and_staff_flags_cannot_be_changed(self):
        self.client.post(self.url, edit_payload(
            role='admin', username='hacker', is_staff='on', is_superuser='on',
        ))
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.LEARNER)
        self.assertEqual(self.user.username, 'ana')
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_cannot_edit_another_user_by_posting_their_id(self):
        self.client.post(self.url, edit_payload(id=self.other.pk, pk=self.other.pk, first_name='Owned'))
        self.other.refresh_from_db()
        self.assertEqual(self.other.first_name, 'Bob')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Owned')  # only their own record changed


class ProfilePhotoTests(ProfileTestCase):
    url = reverse('accounts:profile_edit')

    def upload(self, photo, **extra):
        return self.client.post(self.url, edit_payload(profile_photo=photo, **extra))

    def test_upload_photo(self):
        response = self.upload(make_image('me.png'))
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_photo.name.startswith(f'profile_photos/user_{self.user.pk}/'))
        self.assertTrue(os.path.exists(self.user.profile_photo.path))

        page = self.client.get(reverse('accounts:profile'))
        self.assertContains(page, self.user.profile_photo.url)
        self.assertNotContains(page, 'default-avatar.svg')

    def test_jpeg_upload_accepted(self):
        response = self.upload(make_image('me.jpg', fmt='JPEG'))
        self.assertRedirects(response, reverse('accounts:profile'))

    def test_replacing_photo_deletes_old_file(self):
        self.upload(make_image('first.png'))
        self.user.refresh_from_db()
        old_path = self.user.profile_photo.path

        self.upload(make_image('second.png'))
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.profile_photo.path, old_path)
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(self.user.profile_photo.path))

    def test_saving_without_new_photo_keeps_existing(self):
        self.upload(make_image('keep.png'))
        self.user.refresh_from_db()
        kept = self.user.profile_photo.name
        self.client.post(self.url, edit_payload(first_name='Ann'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile_photo.name, kept)

    def test_remove_photo(self):
        self.upload(make_image('bye.png'))
        self.user.refresh_from_db()
        old_path = self.user.profile_photo.path

        self.client.post(self.url, edit_payload(remove_photo='on'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_photo)
        self.assertFalse(os.path.exists(old_path))

    def test_non_image_rejected(self):
        fake = SimpleUploadedFile('virus.png', b'not really an image', content_type='image/png')
        response = self.upload(fake)
        self.assertIn('profile_photo', response.context['form'].errors)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_photo)

    def test_disallowed_extension_rejected(self):
        response = self.upload(make_image('anim.gif', fmt='GIF'))
        self.assertIn('profile_photo', response.context['form'].errors)

    def test_oversized_photo_rejected(self):
        big = make_image('big.png', size=(1000, 1000), noise=True)  # ~3 MB of noise
        self.assertGreater(big.size, 2 * 1024 * 1024)
        response = self.upload(big)
        self.assertEqual(
            response.context['form'].errors['profile_photo'], ['Photo must be 2 MB or smaller.']
        )
