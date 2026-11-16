from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from accounts.decorators import RoleRequiredMixin
from accounts.models import User

from .forms import GramStainScenarioForm
from .models import GramStainScenario


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
