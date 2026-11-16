import json

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Avg, Count, Max, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.decorators import RoleRequiredMixin, learner_required
from accounts.models import User

from .forms import GramStainScenarioForm, LabNotesForm
from .grading import (
    CRYSTAL_VIOLET,
    DECOLORIZER,
    IODINE,
    REAGENT_LABELS,
    SAFRANIN,
    WATER,
    StepValidationError,
    decolorizer_limits,
    grade_attempt,
    target_seconds,
)
from .models import GramStainScenario, SimulationAttempt
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


# Largest `steps` payload accepted (50 steps of JSON fit in well under this).
MAX_STEPS_PAYLOAD = 10_000


@learner_required
@require_POST
def submit_attempt(request, pk):
    """Grade the submitted run on the server and save it as a SimulationAttempt."""
    scenario = get_object_or_404(GramStainScenario, pk=pk, is_active=True)
    raw_steps = request.POST.get('steps', '')

    try:
        if len(raw_steps) > MAX_STEPS_PAYLOAD:
            raise StepValidationError('the run is too long')
        steps = json.loads(raw_steps)
        if steps == []:
            raise StepValidationError('apply at least one reagent before submitting')
        # Score, diagnosis and colours are always computed here, never trusted from the browser.
        result = grade_attempt(scenario, steps)
    except StepValidationError as error:
        reason = str(error).rstrip('.')
        reason = reason[:1].lower() + reason[1:]
        messages.error(request, f'Your run could not be graded: {reason}. Please try again.')
        return redirect('simulator:workbench', pk=scenario.pk)
    except ValueError:  # malformed JSON
        messages.error(request, 'Your run could not be read. Please try again.')
        return redirect('simulator:workbench', pk=scenario.pk)

    attempt = SimulationAttempt.objects.create(
        user=request.user,
        scenario=scenario,
        recorded_steps_json=result.steps,
        score=result.score,
        outcome_diagnosis=result.outcome_diagnosis,
        is_passed=result.is_passed,
        observed_color=result.observed_color,
        expected_color=result.expected_color,
        grading_feedback=result.feedback,
    )
    summary = f'{result.outcome_diagnosis} · {result.score}/100'
    if result.is_passed:
        messages.success(request, f'Attempt saved and passed — {summary}.')
    else:
        messages.warning(request, f'Attempt saved but not passed — {summary}. Review the feedback below.')
    return redirect('simulator:attempt_detail', pk=attempt.pk)


class LearnerRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.LEARNER,)


def own_attempts(user):
    """Learners only ever see, edit or delete their own attempts (others' give 404)."""
    return SimulationAttempt.objects.filter(user=user).select_related('scenario')


REAGENT_COLORS = {reagent: color for reagent, _role, color in REAGENT_RACK}


def report_context(attempt, notes_form=None):
    steps = [
        {
            'number': number,
            'reagent': step.get('reagent'),
            'label': REAGENT_LABELS.get(step.get('reagent'), step.get('reagent')),
            'color': REAGENT_COLORS.get(step.get('reagent'), '#ccc'),
            'seconds': step.get('seconds'),
        }
        for number, step in enumerate(attempt.recorded_steps_json, start=1)
    ]
    return {
        'attempt': attempt,
        'scenario': attempt.scenario,
        'cells': build_cells(attempt.scenario.cell_shape, seed=attempt.scenario_id),
        'steps': steps,
        'notes_form': notes_form or LabNotesForm(instance=attempt),
    }


@learner_required
def attempt_detail(request, pk):
    """Microscopic outcome report for one of the learner's own attempts."""
    attempt = get_object_or_404(own_attempts(request.user), pk=pk)
    return render(request, 'simulator/attempt_detail.html', report_context(attempt))


@learner_required
@require_POST
def attempt_notes(request, pk):
    """Update: the learner edits lab notes on their own attempt."""
    attempt = get_object_or_404(own_attempts(request.user), pk=pk)
    form = LabNotesForm(request.POST, instance=attempt)
    if form.is_valid():
        form.save()
        messages.success(request, 'Lab notes saved.')
        return redirect(attempt)
    messages.error(request, 'Your lab notes were not saved. Please fix the error below.')
    return render(request, 'simulator/attempt_detail.html', report_context(attempt, form))


class AttemptListView(LearnerRequiredMixin, ListView):
    """Read: the learner's practice log, filterable by scenario and result."""

    template_name = 'simulator/attempt_list.html'
    context_object_name = 'attempts'
    paginate_by = 10

    def get_filters(self):
        scenario = self.request.GET.get('scenario', '')
        result = self.request.GET.get('result', '')
        return {
            'scenario': int(scenario) if scenario.isdigit() else None,
            'result': result if result in ('passed', 'failed') else '',
        }

    def get_queryset(self):
        attempts = own_attempts(self.request.user)
        filters = self.get_filters()
        if filters['scenario']:
            attempts = attempts.filter(scenario_id=filters['scenario'])
        if filters['result']:
            attempts = attempts.filter(is_passed=filters['result'] == 'passed')
        return attempts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        filters = self.get_filters()
        context.update({
            'filters': filters,
            'is_filtered': bool(filters['scenario'] or filters['result']),
            'summary': own_attempts(user).aggregate(
                total=Count('id'),
                passed=Count('id', filter=Q(is_passed=True)),
                best=Max('score'),
                average=Avg('score'),
            ),
            'scenario_choices': (
                GramStainScenario.objects.filter(attempts__user=user).distinct().order_by('title')
            ),
        })
        return context


class AttemptDeleteView(LearnerRequiredMixin, DeleteView):
    """Delete: GET shows a confirmation page; POST removes the learner's own attempt."""

    template_name = 'simulator/attempt_confirm_delete.html'
    context_object_name = 'attempt'
    success_url = reverse_lazy('simulator:attempt_list')

    def get_queryset(self):
        return own_attempts(self.request.user)

    def form_valid(self, form):
        title = self.object.scenario.title
        when = timezone.localtime(self.object.completed_at).strftime('%b %d, %Y %I:%M %p')
        response = super().form_valid(form)
        messages.success(self.request, f'Your "{title}" attempt from {when} was deleted.')
        return response
