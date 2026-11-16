from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decorators import RoleRequiredMixin, learner_required
from accounts.models import User

from .forms import GramStainScenarioForm
from .grading import (
    CRYSTAL_VIOLET,
    DECOLORIZER,
    IODINE,
    REAGENT_LABELS,
    SAFRANIN,
    WATER,
    decolorizer_limits,
    target_seconds,
)
from .models import GramStainScenario
from .slide import build_cells


class LabAdminRequiredMixin(RoleRequiredMixin):
    """Only Lab Admins may manage the scenario catalog."""

    allowed_roles = (User.Role.ADMIN,)


class ScenarioListView(LabAdminRequiredMixin, ListView):
    model = GramStainScenario
    template_name = 'simulator/scenario_list.html'
    context_object_name = 'scenarios'

    def get_queryset(self):
        return GramStainScenario.objects.select_related('created_by')


class ScenarioFormMixin(LabAdminRequiredMixin, SuccessMessageMixin):
    model = GramStainScenario
    form_class = GramStainScenarioForm
    template_name = 'simulator/scenario_form.html'
    success_url = reverse_lazy('simulator:scenario_list')

    def form_invalid(self, form):
        messages.error(self.request, 'The scenario was not saved. Please fix the highlighted errors.')
        return super().form_invalid(form)


class ScenarioCreateView(ScenarioFormMixin, CreateView):
    success_message = 'Scenario "%(title)s" was created.'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ScenarioUpdateView(ScenarioFormMixin, UpdateView):
    success_message = 'Scenario "%(title)s" was updated.'


class ScenarioDeleteView(LabAdminRequiredMixin, DeleteView):
    """GET shows a confirmation page; only POST actually deletes."""

    model = GramStainScenario
    template_name = 'simulator/scenario_confirm_delete.html'
    context_object_name = 'scenario'
    success_url = reverse_lazy('simulator:scenario_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attempt_count'] = self.object.attempts.count()
        return context

    def form_valid(self, form):
        title = self.object.title
        try:
            response = super().form_valid(form)
        except ProtectedError:
            # SimulationAttempt.scenario is PROTECT: keep learners' history.
            count = self.object.attempts.count()
            messages.error(
                self.request,
                f'"{title}" has {count} saved learner attempt{pluralize(count)} and cannot be '
                'deleted. Untick "Active" to hide it from the playground instead.',
            )
            return redirect('simulator:scenario_update', pk=self.object.pk)
        messages.success(self.request, f'Scenario "{title}" was deleted.')
        return response


# ---------------------------------------------------------------------------
# Learner: Gram Staining Workbench
# ---------------------------------------------------------------------------

REAGENT_RACK = [
    # (reagent, role on the protocol, bottle colour)
    (CRYSTAL_VIOLET, 'Primary stain', '#6b3fa0'),
    (IODINE, 'Mordant', '#8a5a1f'),
    (DECOLORIZER, 'Decolorizer', '#8fbcd4'),
    (SAFRANIN, 'Counterstain', '#d6336c'),
    (WATER, 'Rinse', '#5fb3e0'),
]


def workbench_reagents(scenario):
    return [
        {
            'key': reagent,
            'label': REAGENT_LABELS[reagent],
            'role': role,
            'color': color,
            'target': None if reagent == WATER else target_seconds(scenario, reagent),
        }
        for reagent, role, color in REAGENT_RACK
    ]


@learner_required
def workbench(request, pk):
    """Interactive Gram staining bench for one active scenario."""
    scenario = get_object_or_404(GramStainScenario, pk=pk, is_active=True)
    reagents = workbench_reagents(scenario)
    under, over = decolorizer_limits(scenario.decolorizer_seconds)
    config = {
        'scenarioId': scenario.pk,
        'gramType': scenario.gram_type,
        'targets': {r['key']: r['target'] for r in reagents if r['target']},
        'decolorizerLimits': {'under': under, 'over': over},
        'reagents': {r['key']: {'label': r['label'], 'color': r['color']} for r in reagents},
    }
    return render(request, 'simulator/workbench.html', {
        'scenario': scenario,
        'cells': build_cells(scenario.cell_shape, seed=scenario.pk),
        'reagents': reagents,
        'hide_identity': scenario.difficulty == GramStainScenario.Difficulty.CHALLENGE,
        'workbench_config': config,
    })
