from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, ProfileForm, RegistrationForm, StyledPasswordChangeForm
from .models import User


@require_http_methods(['GET', 'POST'])
def register(request):
    """Public student sign-up."""
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Welcome to MedStep, {user.first_name}! Your learner account was '
                'created successfully. Please sign in to continue.',
            )
            return redirect('accounts:login')
        messages.error(request, 'Registration failed. Please fix the highlighted errors below.')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


class MedStepLoginView(auth_views.LoginView):
    """Login page. Already-signed-in users are sent straight on."""

    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get('remember_me'):
            # Session cookie expires when the browser is closed.
            self.request.session.set_expiry(0)
        user = form.get_user()
        messages.success(self.request, f'Welcome back, {user.first_name or user.username}!')
        return response


class MedStepLogoutView(auth_views.LogoutView):
    """POST-only (Django default): flushes the session, then redirects to login."""

    next_page = 'accounts:login'

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, 'You have been signed out. See you at the bench!')
        return response


# ---------------------------------------------------------------------------
# Profile — always the logged-in user's own record (request.user).
# There is deliberately no <pk>/<username> in these URLs, so another
# user's profile can never be opened or edited by changing the URL.
# ---------------------------------------------------------------------------

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


@login_required
@require_http_methods(['GET', 'POST'])
def profile_edit(request):
    # Edit a fresh copy so a failed submission doesn't leave half-applied
    # changes on request.user (which the navbar renders).
    user = User.objects.get(pk=request.user.pk)
    old_photo_name = user.profile_photo.name

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save()
            # Delete the previous file when the photo was replaced or removed.
            if old_photo_name and old_photo_name != user.profile_photo.name:
                user.profile_photo.storage.delete(old_photo_name)
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile')
        messages.error(request, 'Your profile was not saved. Please fix the highlighted errors.')
    else:
        form = ProfileForm(instance=user)

    return render(request, 'accounts/profile_edit.html', {'form': form})


class MedStepPasswordChangeView(auth_views.PasswordChangeView):
    """Change own password. Django requires login and keeps the user signed in
    (update_session_auth_hash) while logging out their other sessions."""

    template_name = 'accounts/password_change.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Your password has been changed.')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Your password was not changed. Please fix the errors below.')
        return super().form_invalid(form)
