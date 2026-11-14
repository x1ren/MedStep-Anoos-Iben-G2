from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import RegistrationForm


@require_http_methods(['GET', 'POST'])
def register(request):
    """Public student sign-up."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f'Welcome to MedStep, {user.first_name}! Your student account '
                'was created successfully.',
            )
            return redirect('home')
        messages.error(request, 'Registration failed. Please fix the highlighted errors below.')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})
