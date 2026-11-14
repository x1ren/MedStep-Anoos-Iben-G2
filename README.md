# MedStep

**MedStep** is a full-stack web laboratory simulator that gives allied health
students a zero-cost way to practice high-stakes microbiology protocols —
**Gram Staining** and **Quadrant Streak Plating** — outside the campus lab.
Learners will manipulate virtual instruments, control reagent exposure timers
and review generated microscopic outcomes to build procedural muscle memory.

This repository contains **Phase 1: the Account feature** — the foundation the
simulations will be built on.

| | |
|---|---|
| **Framework** | Django 5.2 (backend + server-rendered templates) |
| **Database** | Supabase PostgreSQL (via `psycopg` 3) |
| **UI** | Bootstrap 5.3 + Bootstrap Icons, custom clinical theme |
| **Roles** | `learner` (Student Learner) and `admin` (Lab Admin / Content Curator) |

---

## Phase 1 features

**Registration** — public sign-up always creates a *learner* account. Validates
required fields, email format, unique username, unique email (case-insensitive),
matching password confirmation and Django's password-strength rules. Passwords
are hashed by Django (PBKDF2); plain text is never stored.

**Login / logout** — sign in with username *or* email, optional "keep me signed
in", clear error for invalid credentials. Logout is POST-only (CSRF-protected),
ends the session and redirects to the login page.

**Role-based dashboards** — after login each user is redirected to their own
dashboard:

- `/dashboard/learner/` — **Student Playground**: quick-start practice cards,
  available microbiology modules (protocol steps and reagent timings) and
  personal simulation stats.
- `/dashboard/admin/` — **Lab Management**: catalog overview (modules and
  bacterial specimens by Gram reaction), active lab scenarios, and user
  engagement metrics with a searchable, paginated learner list.

**Strict authorization** — `@role_required` / `@learner_required` /
`@lab_admin_required` decorators and a `RoleRequiredMixin`
([accounts/decorators.py](accounts/decorators.py)). Anonymous users are sent to
login; a user with the wrong role gets **403 Forbidden** (custom page). This
blocks learners from Lab Admin pages and Lab Admins from learner pages.

**Role-aware navigation** — the navbar shows different links per role, a role
badge, and an account menu (profile, edit profile, change password, sign out).

**Profile management** — view and edit your *own* details (name, email, contact
number) and upload / replace / remove a profile photo (JPG/PNG/WEBP, max 2 MB,
default avatar fallback). Profile URLs contain no user ID, so another user's
profile cannot be reached by URL manipulation; username and role cannot be
changed through the form.

**Change password** — requires the current password; signs out other sessions.

> The lab catalog (modules, specimens, scenarios) is static data in
> [dashboard/catalog.py](dashboard/catalog.py) for Increment 1. Catalog editing,
> attempt tracking and the interactive simulations come in later increments;
> their dashboard sections are in place and show empty states.

---

## Getting started

Requires **Python 3.11+**, **Git** and a **Supabase** project.

```bash
# 1. Clone
git clone <repository-url> MedStep
cd MedStep

# 2. Virtual environment
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# venv\Scripts\activate.bat      # Windows cmd
# source venv/bin/activate       # macOS / Linux / Git Bash

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment variables
copy .env.example .env           # macOS/Linux: cp .env.example .env
#   then edit .env — see "Configuration" below

# 5. Verify, create tables, create a Lab Admin account
python manage.py check
python manage.py migrate
python manage.py createsuperuser   # superusers get the Lab Admin role

# 6. Run
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Register a learner account from the site; sign in
with the superuser to see the Lab Admin dashboard. More Lab Admin accounts can
be created at `/admin/` → Users → Add user (choose role *Lab Admin / Content Curator*).

---

## Configuration

All settings come from `.env` (never committed). See [.env.example](.env.example).

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | **Required.** Generate: `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"` |
| `DEBUG` | `True` for local development, `False` in production (enables HTTPS/secure-cookie settings). |
| `ALLOWED_HOSTS` | Comma-separated host names. |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins with scheme, for HTTPS deployments. |
| `DATABASE_URL` | Full Supabase connection string. Takes precedence over the `DB_*` variables. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Individual Supabase credentials (used when `DATABASE_URL` is empty). |
| `DB_SSLMODE` | Default `require` — Supabase only accepts SSL. |
| `DB_CONN_MAX_AGE` | Seconds to reuse DB connections (default `60`). |

**Supabase:** Project → **Connect** → **Session pooler** (IPv4-compatible,
port `5432`). Paste the URI as `DATABASE_URL`, or copy host / user
(`postgres.<project-ref>`) / password into the `DB_*` variables.

The app refuses to start without `SECRET_KEY` or with a non-PostgreSQL
database — SQLite is intentionally not supported.

---

## Running tests

```bash
python manage.py test
```

111 tests cover the user model and role migration, registration,
login/logout, access control, both dashboards and the lab catalog, navigation,
profile view/edit, photo uploads and password change. Django creates a temporary `test_<DB_NAME>` database on Supabase for the
run and deletes it afterwards.

---

## URL map

| URL | Who | Purpose |
|---|---|---|
| `/` | everyone | Landing page |
| `/accounts/register/` | anonymous | Student registration |
| `/accounts/login/` | anonymous | Sign in (username or email) |
| `/accounts/logout/` | signed in (POST) | Sign out |
| `/accounts/profile/` | signed in | View own profile |
| `/accounts/profile/edit/` | signed in | Edit own profile & photo |
| `/accounts/password/change/` | signed in | Change own password |
| `/dashboard/` | signed in | Redirects to the user's role dashboard |
| `/dashboard/learner/` | learners only | Student Playground dashboard |
| `/dashboard/admin/` | Lab Admins only | Lab Management dashboard |
| `/admin/` | staff | Django admin (user management) |

---

## Project structure

```
MedStep/
├── accounts/                 # Custom user, auth, roles, profile
│   ├── models.py             # User(AbstractUser): role, email, contact_number, profile_photo
│   ├── forms.py              # Registration, login, profile, password-change forms
│   ├── views.py              # Register, login/logout, profile, password change
│   ├── backends.py           # Login with username or email
│   ├── decorators.py         # role_required, learner/lab_admin_required, RoleRequiredMixin
│   ├── admin.py              # User admin with role filter
│   └── tests/                # Model, auth, access-control, profile, navbar tests
├── dashboard/                # Role-based dashboards
│   ├── catalog.py            # Modules, specimens, scenarios, quick-start cards
│   ├── views.py              # Role redirect, learner & Lab Admin dashboards
│   └── tests.py
├── medstep/                  # Project settings & root URLs
├── templates/                # base layout, partials, accounts/, dashboard/, 403
├── static/                   # css/medstep.css, img/
├── .env.example              # Environment template (copy to .env)
└── requirements.txt
```

---

## Security notes

- Secrets and DB credentials live only in `.env` (git-ignored).
- Passwords are hashed by Django and checked against its password validators.
- Every protected view checks login **and** role on the server for each request.
- Logout and all forms are CSRF-protected; logout accepts POST only.
- Login ignores `?next=` URLs that point to other sites.
- Uploaded photos are validated as real images, size-limited, and saved under
  random file names.
- With `DEBUG=False`: HTTPS redirect, secure cookies, HSTS and other hardening
  headers are enabled automatically.
