from django.contrib import admin

from .models import GramStainScenario, SimulationAttempt


@admin.register(GramStainScenario)
class GramStainScenarioAdmin(admin.ModelAdmin):
    list_display = ('title', 'specimen_name', 'gram_type', 'cell_shape', 'difficulty',
                    'decolorizer_seconds', 'is_active', 'created_by', 'created_at')
    list_filter = ('gram_type', 'cell_shape', 'difficulty', 'is_active')
    search_fields = ('title', 'specimen_name')
    readonly_fields = ('created_at',)


@admin.register(SimulationAttempt)
class SimulationAttemptAdmin(admin.ModelAdmin):
    """Read-only audit view: graded attempts must not be altered by staff."""

    list_display = ('user', 'scenario', 'score', 'is_passed', 'outcome_diagnosis', 'completed_at')
    list_filter = ('is_passed', 'scenario', 'observed_color')
    search_fields = ('user__username', 'scenario__title', 'outcome_diagnosis')
    date_hierarchy = 'completed_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
