from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

PASSWORD = 'Gram-Stain#Demo-42'


def run(*args):
    out = StringIO()
    call_command('seed_demo_accounts', *args, stdout=out)
    return out.getvalue()


class SeedDemoAccountsTests(TestCase):

    def test_creates_one_account_per_role(self):
        run('--password', PASSWORD)
        learner = User.objects.get(username='demo_learner')
        admin = User.objects.get(username='demo_admin')
        self.assertEqual(learner.role, User.Role.LEARNER)
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(learner.check_password(PASSWORD))
        self.assertTrue(admin.check_password(PASSWORD))

    def test_running_twice_resets_instead_of_duplicating(self):
        run('--password', PASSWORD)
        User.objects.filter(username='demo_admin').update(role=User.Role.LEARNER, is_active=False)
        output = run('--password', 'Another#Strong-Pass-7')
        self.assertEqual(User.objects.filter(username__startswith='demo_').count(), 2)
        admin = User.objects.get(username='demo_admin')
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_active)
        self.assertTrue(admin.check_password('Another#Strong-Pass-7'))
        self.assertIn('Reset', output)

    def test_random_password_is_printed_and_works(self):
        output = run()
        password = output.strip().splitlines()[-1].split(': ', 1)[1]
        self.assertTrue(User.objects.get(username='demo_learner').check_password(password))

    def test_weak_password_rejected(self):
        with self.assertRaises(CommandError):
            run('--password', '12345')
        self.assertFalse(User.objects.filter(username__startswith='demo_').exists())

    def test_demo_accounts_land_on_their_role_dashboards(self):
        run('--password', PASSWORD)
        for username, dashboard in (('demo_learner', 'dashboard:learner'),
                                    ('demo_admin', 'dashboard:admin')):
            with self.subTest(username=username):
                self.client.post(reverse('accounts:login'),
                                 {'username': username, 'password': PASSWORD})
                response = self.client.get(reverse('dashboard:home'))
                self.assertRedirects(response, reverse(dashboard), fetch_redirect_response=False)
                self.client.logout()
