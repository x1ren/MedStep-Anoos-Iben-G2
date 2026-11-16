from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Case, Count, IntegerField, Max, Q, Value, When
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView

from accounts.decorators import RoleRequiredMixin, learner_required
from accounts.models import User
from simulator.models import GramStainScenario, SimulationAttempt

from .catalog import LAB_MODULES, QUICK_STARTS


@login_required
def dashboard_home(request):
    """Send each user to the dashboard for their role (used after login)."""
    if request.user.is_lab_admin:
        return redirect('dashboard:admin')
    return redirect('dashboard:learner')


DIFFICULTY_ORDER = Case(
    When(difficulty=GramStainScenario.Difficulty.BEGINNER, then=Value(0)),
    When(difficulty=GramStainScenario.Difficulty.INTERMEDIATE, then=Value(1)),
    default=Value(2),
    output_field=IntegerField(),
)


def pick_scenario(scenarios, card):
    """Scenario a quick-start card launches: preferred difficulty, else the first one."""
    if card['module'] != 'gram-staining' or not scenarios:
        return None
    preferred = [s for s in scenarios if s.difficulty == card.get('difficulty')]
    return (preferred or scenarios)[0]


def percent(part, whole):
    return round(part * 100 / whole) if whole else None


@learner_required
def learner_dashboard(request):
    """Student Playground: Gram stain scenarios, quick starts and personal stats."""
    user = request.user
    mine = Q(attempts__user=user)
    scenarios = list(
        GramStainScenario.objects.filter(is_active=True)
        .annotate(
            my_attempts=Count('attempts', filter=mine),
            my_best=Max('attempts__score', filter=mine),
            my_passes=Count('attempts', filter=mine & Q(attempts__is_passed=True)),
            difficulty_rank=DIFFICULTY_ORDER,
        )
        .order_by('difficulty_rank', 'title')
    )
    attempts = SimulationAttempt.objects.filter(user=user).select_related('scenario')
    summary = attempts.aggregate(
        sessions=Count('id'),
        passed=Count('id', filter=Q(is_passed=True)),
        best_score=Max('score'),
    )
    scenarios_passed = sum(1 for scenario in scenarios if scenario.my_passes)
    gram_progress = percent(scenarios_passed, len(scenarios)) or 0

    modules = [
        {**module, 'live': module['slug'] == 'gram-staining',
         'progress': gram_progress if module['slug'] == 'gram-staining' else 0}
        for module in LAB_MODULES
    ]
    context = {
        'scenarios': scenarios,
        'modules': modules,
        'quick_starts': [{**card, 'scenario': pick_scenario(scenarios, card)} for card in QUICK_STARTS],
        'recent_attempts': attempts[:5],
        'stats': {
            'sessions': summary['sessions'],
            'passed': summary['passed'],
            'best_score': summary['best_score'],
            'pass_rate': percent(summary['passed'], summary['sessions']),
            'scenarios_passed': scenarios_passed,
            'scenarios_total': len(scenarios),
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
        learners = (
            User.objects.filter(role=User.Role.LEARNER)
            .annotate(attempt_count=Count('attempts'), best_score=Max('attempts__score'))
            .order_by('last_name', 'first_name', 'username')
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

        # Gram stain catalog, straight from the database.
        positive = Q(gram_type=GramStainScenario.GramType.POSITIVE)
        negative = Q(gram_type=GramStainScenario.GramType.NEGATIVE)
        catalog = GramStainScenario.objects.aggregate(
            scenarios=Count('id'),
            active_scenarios=Count('id', filter=Q(is_active=True)),
            hidden_scenarios=Count('id', filter=Q(is_active=False)),
            gram_positive=Count('id', filter=positive),
            gram_negative=Count('id', filter=negative),
        )
        catalog['modules'] = len(LAB_MODULES)
        specimens = (
            GramStainScenario.objects
            .values('specimen_name', 'gram_type', 'cell_shape')
            .distinct()
            .order_by('specimen_name')
        )
        catalog['specimens'] = len(specimens)

        # Simulation attempts across all learners.
        attempts = SimulationAttempt.objects.aggregate(
            total=Count('id'),
            last_7d=Count('id', filter=Q(completed_at__gte=now - timedelta(days=7))),
            passed=Count('id', filter=Q(is_passed=True)),
            average=Avg('score'),
        )
        active_scenarios = list(
            GramStainScenario.objects.filter(is_active=True)
            .select_related('created_by')
            .annotate(
                attempt_count=Count('attempts'),
                average_score=Avg('attempts__score'),
                pass_count=Count('attempts', filter=Q(attempts__is_passed=True)),
            )
        )
        for scenario in active_scenarios:
            scenario.pass_rate = percent(scenario.pass_count, scenario.attempt_count)

        context.update({
            'q': self.get_search_query(),
            'modules': LAB_MODULES,
            'specimens': specimens,
            'active_scenarios': active_scenarios,
            'catalog': catalog,
            'attempt_stats': {
                'total': attempts['total'],
                'last_7d': attempts['last_7d'],
                'pass_rate': percent(attempts['passed'], attempts['total']),
                'average_score': round(attempts['average']) if attempts['average'] is not None else None,
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
