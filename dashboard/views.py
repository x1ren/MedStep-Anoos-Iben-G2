from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.decorators import student_required

from .modules import LAB_MODULES


@login_required
def dashboard_home(request):
    """Send each user to the dashboard for their role (used after login)."""
    if request.user.is_student:
        return redirect('dashboard:student')
    # Instructor dashboard is added in the next step.
    return redirect('home')


@student_required
def student_dashboard(request):
    # Practice tracking is Phase 2; every module starts at 0% for now.
    modules = [{**module, 'progress': 0, 'attempts': 0} for module in LAB_MODULES]
    context = {
        'modules': modules,
        'stats': {
            'modules_available': len(modules),
            'modules_completed': 0,
            'practice_sessions': 0,
        },
    }
    return render(request, 'dashboard/student.html', context)
