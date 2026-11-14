from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView

from accounts.decorators import RoleRequiredMixin, learner_required
from accounts.models import User

from .modules import LAB_MODULES


@login_required
def dashboard_home(request):
    """Send each user to the dashboard for their role (used after login)."""
    if request.user.is_lab_admin:
        return redirect('dashboard:instructor')
    return redirect('dashboard:student')


@learner_required
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


class InstructorDashboardView(RoleRequiredMixin, ListView):
    """Instructor home: student roster, lab modules and performance overview."""

    allowed_roles = (User.Role.ADMIN,)
    template_name = 'dashboard/instructor.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_search_query(self):
        return self.request.GET.get('q', '').strip()

    def get_queryset(self):
        students = User.objects.filter(role=User.Role.LEARNER).order_by(
            'last_name', 'first_name', 'username'
        )
        q = self.get_search_query()
        if q:
            students = students.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
        return students

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        all_students = User.objects.filter(role=User.Role.LEARNER)
        context.update({
            'q': self.get_search_query(),
            'modules': LAB_MODULES,
            'stats': {
                'total_students': all_students.count(),
                'active_this_week': all_students.filter(
                    last_login__gte=now - timedelta(days=7)
                ).count(),
                'new_this_month': all_students.filter(
                    date_joined__gte=now - timedelta(days=30)
                ).count(),
                'modules': len(LAB_MODULES),
            },
        })
        return context
