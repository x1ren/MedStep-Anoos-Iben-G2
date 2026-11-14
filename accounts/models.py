import uuid
from pathlib import Path

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.templatetags.static import static


def profile_photo_upload_to(instance, filename):
    """Store photos as media/profile_photos/user_<id>/<random>.<ext>.

    A random filename prevents guessing other users' photo URLs and avoids
    clashes or path tricks from user-supplied filenames.
    """
    ext = Path(filename).suffix.lower() or '.jpg'
    folder = f'user_{instance.pk}' if instance.pk else 'new'
    return f'profile_photos/{folder}/{uuid.uuid4().hex}{ext}'


contact_number_validator = RegexValidator(
    regex=r'^\+?[0-9][0-9\s\-()]{6,18}$',
    message='Enter a valid contact number (digits, spaces, dashes; optional leading +).',
)


class UserManager(DjangoUserManager):
    """Superusers created with `createsuperuser` are lab admins (instructors)."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.INSTRUCTOR)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """MedStep user with a role, unique email, contact number and photo."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        INSTRUCTOR = 'instructor', 'Instructor / Lab Admin'

    email = models.EmailField(
        'email address',
        unique=True,
        error_messages={'unique': 'An account with this email already exists.'},
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    contact_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[contact_number_validator],
        help_text='Optional. e.g. +63 912 345 6789',
    )
    profile_photo = models.ImageField(
        upload_to=profile_photo_upload_to,
        blank=True,
    )

    # `createsuperuser` will also prompt for an email.
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    class Meta:
        ordering = ['last_name', 'first_name', 'username']

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        # Treat emails case-insensitively so "A@x.com" and "a@x.com" collide.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def avatar_url(self):
        """Uploaded profile photo, or the default avatar if none."""
        if self.profile_photo:
            return self.profile_photo.url
        return static('img/default-avatar.svg')
