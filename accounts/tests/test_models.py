from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User


class UserModelTests(TestCase):
    def test_new_users_default_to_learner(self):
        user = User.objects.create_user('ana', 'ana@example.com', 'pw-Test-123')
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertTrue(user.is_learner)
        self.assertFalse(user.is_lab_admin)

    def test_superuser_is_lab_admin(self):
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'pw-Test-123')
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_lab_admin)

    def test_email_is_stored_lowercase(self):
        user = User.objects.create_user('ana', '  Ana.Reyes@Example.COM ', 'pw-Test-123')
        self.assertEqual(user.email, 'ana.reyes@example.com')

    def test_email_must_be_unique(self):
        User.objects.create_user('ana', 'ana@example.com', 'pw-Test-123')
        with self.assertRaises(IntegrityError):
            User.objects.create_user('ana2', 'ANA@example.com', 'pw-Test-123')

    def test_password_is_hashed(self):
        user = User.objects.create_user('ana', 'ana@example.com', 'pw-Test-123')
        self.assertNotEqual(user.password, 'pw-Test-123')
        self.assertTrue(user.check_password('pw-Test-123'))

    def test_contact_number_validation(self):
        user = User(username='bob', email='bob@example.com', contact_number='call me')
        user.set_password('pw-Test-123')
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn('contact_number', ctx.exception.message_dict)

        user.contact_number = '+63 912 345 6789'
        user.full_clean()  # does not raise

    def test_str_uses_full_name_then_username(self):
        user = User(username='bob', first_name='Bob', last_name='Cruz')
        self.assertEqual(str(user), 'Bob Cruz')
        self.assertEqual(str(User(username='bob')), 'bob')

    def test_profile_photo_path_is_randomised_per_user(self):
        user = User.objects.create_user('ana', 'ana@example.com', 'pw-Test-123')
        upload_to = User._meta.get_field('profile_photo').upload_to
        path = upload_to(user, '../../Evil Name.PNG')
        self.assertTrue(path.startswith(f'profile_photos/user_{user.pk}/'))
        self.assertTrue(path.endswith('.png'))
        self.assertNotIn('Evil', path)
        self.assertNotEqual(path, upload_to(user, 'x.png'))
