"""
Django settings for the MedStep project.

All secrets and environment-specific values are loaded from a `.env` file
(see `.env.example`). Nothing sensitive is hard-coded here.
"""

import os
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from <project root>/.env into os.environ.
# Real environment variables (e.g. set by a hosting provider) take precedence.
load_dotenv(BASE_DIR / '.env')


def env_str(name, default=None, required=False):
    """Read a string environment variable, optionally failing if missing."""
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(
            f'Missing required environment variable "{name}". '
            'Copy .env.example to .env and fill it in.'
        )
    return value


def env_bool(name, default=False):
    """Read a boolean environment variable (1/true/yes/on)."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    """Read a comma-separated environment variable as a list."""
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(',') if item.strip()]


# ---------------------------------------------------------------
# Core security
# ---------------------------------------------------------------
SECRET_KEY = env_str('SECRET_KEY', required=True)
DEBUG = env_bool('DEBUG', default=False)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')


# ---------------------------------------------------------------
# Applications
# ---------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # MedStep apps
    'accounts.apps.AccountsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'medstep.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'medstep.wsgi.application'


# ---------------------------------------------------------------
# Database — Supabase PostgreSQL (SQLite is intentionally NOT used)
#
# DATABASE_URL takes precedence; otherwise DB_NAME / DB_USER /
# DB_PASSWORD / DB_HOST / DB_PORT are used.
# ---------------------------------------------------------------
DB_SSLMODE = env_str('DB_SSLMODE', 'require')
DB_CONN_MAX_AGE = int(env_str('DB_CONN_MAX_AGE', '60'))

if env_str('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.parse(
            env_str('DATABASE_URL'),
            conn_max_age=DB_CONN_MAX_AGE,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env_str('DB_NAME', required=True),
            'USER': env_str('DB_USER', required=True),
            'PASSWORD': env_str('DB_PASSWORD', required=True),
            'HOST': env_str('DB_HOST', required=True),
            'PORT': env_str('DB_PORT', '5432'),
            'CONN_MAX_AGE': DB_CONN_MAX_AGE,
            'CONN_HEALTH_CHECKS': True,
        }
    }

if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('MedStep must run on PostgreSQL (Supabase).')

# Supabase only accepts SSL connections; fail fast if the host is unreachable.
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS'].setdefault('sslmode', DB_SSLMODE)
DATABASES['default']['OPTIONS'].setdefault('connect_timeout', 10)


# ---------------------------------------------------------------
# Authentication — custom user model with student/instructor roles
# ---------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ['accounts.backends.EmailOrUsernameModelBackend']

LOGIN_URL = 'accounts:login'            # where @login_required sends anonymous users
LOGIN_REDIRECT_URL = 'home'             # after a successful login
LOGOUT_REDIRECT_URL = 'accounts:login'  # after logging out

# Map Django's "error" message level to Bootstrap's "danger" alert style.
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}


# ---------------------------------------------------------------
# Password validation (Django hashes passwords with PBKDF2 by default)
# ---------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------
# Static & media files (media = user uploads such as profile photos)
# ---------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'   # target of `collectstatic` for deployment

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------
# Production hardening (active automatically when DEBUG=False)
# ---------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=True)
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
