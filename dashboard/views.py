from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView

from accounts.decorators import RoleRequiredMixin, learner_required
from accounts.models import User

from .catalog import LAB_MODULES, QUICK_STARTS, SPECIMENS, scenarios_with_details


@login_required
def dashboard_home(request):
    """Send each user to the dashboard for their role (used after login)."""
    if request.user.is_lab_admin:
        return redirect('dashboard:admin')
    return redirect('dashboard:learner')


@learner_required
def learner_dashboard(request):
    """Student Playground: modules, quick-start cards and personal stats."""
    # Simulation attempts are recorded from a later increment; until then
    # every learner starts at zero.
    modules = [{**module, 'progress': 0} for module in LAB_MODULES]
    context = {
        'modules': modules,
        'quick_starts': QUICK_STARTS,
        'stats': {
            'sessions': 0,
            'modules_completed': 0,
            'modules_available': len(modules),
            'best_score': None,
            'timing_accuracy': None,
        },
    }
    return render(request, 'dashboard/learner.html', context)


class AdminDashboardView(RoleRequiredMixin, ListView):
    """Lab Management: catalog overview, active scenarios, user engagement."""

    allowed_roles = (User.Role.ADMIN,)
    template_name = 'dashboard/admin.html'
    context_object_name = 'learners'
    paginate_by = 10

    def get_search_query(self):
        return self.request.GET.get('q', '').strip()

    def get_queryset(self):
        learners = User.objects.filter(role=User.Role.LEARNER).order_by(
            'last_name', 'first_name', 'username'
        )
        q = self.get_search_query()
        if q:
            learners = learners.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
        return learners

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        all_learners = User.objects.filter(role=User.Role.LEARNER)
        total = all_learners.count()
        active = all_learners.filter(last_login__gte=now - timedelta(days=7)).count()
        scenarios = scenarios_with_details()

        context.update({
            'q': self.get_search_query(),
            'modules': LAB_MODULES,
            'specimens': SPECIMENS,
            'active_scenarios': [s for s in scenarios if s['status'] == 'active'],
            'catalog': {
                'modules': len(LAB_MODULES),
                'scenarios': len(scenarios),
                'active_scenarios': sum(s['status'] == 'active' for s in scenarios),
                'draft_scenarios': sum(s['status'] == 'draft' for s in scenarios),
                'specimens': len(SPECIMENS),
                'gram_positive': sum(s['gram'] == 'positive' for s in SPECIMENS),
                'gram_negative': sum(s['gram'] == 'negative' for s in SPECIMENS),
            },
            'engagement': {
                'total_learners': total,
                'active_7d': active,
                'new_30d': all_learners.filter(
                    date_joined__gte=now - timedelta(days=30)
                ).count(),
                'engagement_rate': round(active * 100 / total) if total else 0,
                'lab_admins': User.objects.filter(role=User.Role.ADMIN).count(),
            },
        })
        return context
