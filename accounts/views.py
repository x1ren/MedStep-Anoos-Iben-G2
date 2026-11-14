from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import LoginForm, RegistrationForm


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
                f'Welcome to MedStep, {user.first_name}! Your student account was '
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
