"""Role-based access control for MedStep views.

Function-based views::

    @role_required(User.Role.ADMIN)
    def catalog(request): ...

    @learner_required
    def practice(request): ...

Class-based views::

    class CatalogView(RoleRequiredMixin, TemplateView):
        allowed_roles = (User.Role.ADMIN,)

Behaviour:
  * Not logged in  -> redirect to LOGIN_URL (with ?next=...).
  * Wrong role     -> 403 Forbidden, rendered by templates/403.html.

This blocks privilege escalation through URL manipulation: a learner
typing a Lab Admin URL (vertical) or a Lab Admin opening a
learner-only page (horizontal) is refused on the server side.
"""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .models import User


def _validate_roles(roles):
    if not roles:
        raise ValueError('At least one role is required.')
    # User.Role(...) raises ValueError for typos such as 'instuctor'.
    return frozenset(User.Role(role) for role in roles)


def _denied_message(roles):
    labels = ' or '.join(User.Role(role).label for role in roles)
    return f'This area is restricted to {labels} accounts.'


def role_required(*roles):
    """Allow the view only for logged-in users whose role is in `roles`."""
    allowed = _validate_roles(roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in allowed:
                raise PermissionDenied(_denied_message(roles))
            return view_func(request, *args, **kwargs)

        # login_required runs first, so request.user is authenticated above.
        return login_required(_wrapped)

    return decorator


learner_required = role_required(User.Role.LEARNER)
lab_admin_required = role_required(User.Role.ADMIN)


class RoleRequiredMixin(LoginRequiredMixin):
    """Class-based-view equivalent of `role_required`.

    Put it *first* in the base classes and set `allowed_roles`.
    """

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        allowed = _validate_roles(self.allowed_roles)
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # redirect to login
        if request.user.role not in allowed:
            raise PermissionDenied(_denied_message(self.allowed_roles))
        return super().dispatch(request, *args, **kwargs)
