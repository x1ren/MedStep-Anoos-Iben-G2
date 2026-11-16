"""Create (or reset) one demo account per role for testing and grading.

    python manage.py seed_demo_accounts                    # random password, printed once
    python manage.py seed_demo_accounts --password "S3cure!pass"

Running it again resets the same two accounts instead of creating duplicates.
No password is stored in the repository.
"""

import secrets

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User

DEMO_ACCOUNTS = (
    {
        'username': 'demo_learner',
        'email': 'demo.learner@medstep.test',
        'first_name': 'Demo',
        'last_name': 'Learner',
        'role': User.Role.LEARNER,
    },
    {
        'username': 'demo_admin',
        'email': 'demo.admin@medstep.test',
        'first_name': 'Demo',
        'last_name': 'Lab Admin',
        'role': User.Role.ADMIN,
    },
)


class Command(BaseCommand):
    help = 'Create or reset the demo Student Learner and Lab Admin accounts.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help='Password for both accounts. If omitted, a random one is generated and printed.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options['password'] or secrets.token_urlsafe(12)
        if options['password']:
            try:
                validate_password(password)
            except ValidationError as error:
                raise CommandError(' '.join(error.messages))

        for data in DEMO_ACCOUNTS:
            fields = {key: value for key, value in data.items() if key != 'username'}
            user, created = User.objects.update_or_create(
                username=data['username'], defaults=fields
            )
            user.is_active = True
            user.set_password(password)
            user.save()
            action = 'Created' if created else 'Reset'
            self.stdout.write(self.style.SUCCESS(
                f'{action} {user.get_role_display()}: {user.username} ({user.email})'
            ))

        self.stdout.write(f'Password for both accounts: {password}')
