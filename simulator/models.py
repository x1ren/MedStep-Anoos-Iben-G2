from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


def reagent_seconds_field(default, maximum):
    """Target exposure time (seconds) for one reagent step."""
    return models.PositiveSmallIntegerField(
        default=default,
        validators=[MinValueValidator(1), MaxValueValidator(maximum)],
        help_text=f'Target exposure in seconds (1–{maximum}).',
    )


class GramStainScenario(models.Model):
    """A Gram Staining playground module: one specimen plus its target timings."""

    class GramType(models.TextChoices):
        POSITIVE = 'gram_positive', 'Gram-positive'
        NEGATIVE = 'gram_negative', 'Gram-negative'

    class CellShape(models.TextChoices):
        COCCI = 'cocci', 'Cocci'
        BACILLI = 'bacilli', 'Bacilli'

    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        CHALLENGE = 'challenge', 'Challenge'

    title = models.CharField(max_length=120, unique=True)
    specimen_name = models.CharField(max_length=120)
    gram_type = models.CharField(max_length=20, choices=GramType.choices)
    cell_shape = models.CharField(max_length=10, choices=CellShape.choices)
    difficulty = models.CharField(
        max_length=15, choices=Difficulty.choices, default=Difficulty.BEGINNER
    )
    description = models.TextField(blank=True)

    crystal_violet_seconds = reagent_seconds_field(default=60, maximum=300)
    iodine_seconds = reagent_seconds_field(default=60, maximum=300)
    decolorizer_seconds = reagent_seconds_field(default=15, maximum=120)
    safranin_seconds = reagent_seconds_field(default=45, maximum=300)

    # Nullable: seeded scenarios have no author, and deleting an admin's
    # account must not delete the modules they curated.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gram_scenarios',
    )
    is_active = models.BooleanField(
        default=True, help_text='Only active scenarios are shown to learners.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Gram stain scenario'
        constraints = [
            # Database-level guards in addition to the form validators.
            models.CheckConstraint(
                condition=Q(gram_type__in=['gram_positive', 'gram_negative']),
                name='gram_scenario_valid_gram_type',
            ),
            models.CheckConstraint(
                condition=Q(cell_shape__in=['cocci', 'bacilli']),
                name='gram_scenario_valid_cell_shape',
            ),
            models.CheckConstraint(
                condition=Q(crystal_violet_seconds__gt=0) & Q(iodine_seconds__gt=0)
                & Q(decolorizer_seconds__gt=0) & Q(safranin_seconds__gt=0),
                name='gram_scenario_positive_timings',
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_gram_positive(self):
        return self.gram_type == self.GramType.POSITIVE

    @property
    def expected_color(self):
        """Colour of correctly stained cells: violet (+) or pink (−)."""
        return 'violet' if self.is_gram_positive else 'pink'

    @property
    def expected_result(self):
        """e.g. 'Gram-Positive Cocci (Violet)'."""
        gram = 'Gram-Positive' if self.is_gram_positive else 'Gram-Negative'
        return f'{gram} {self.get_cell_shape_display()} ({self.expected_color.title()})'


class SimulationAttempt(models.Model):
    """One completed Gram staining run by a learner (their practice log)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attempts',
    )
    # PROTECT: a scenario with saved attempts cannot be deleted, so learners
    # never lose their practice history. Admins hide it (is_active) instead.
    scenario = models.ForeignKey(
        GramStainScenario,
        on_delete=models.PROTECT,
        related_name='attempts',
    )
    # Exact reagent sequence and seconds held, e.g.
    # [{"reagent": "crystal_violet", "seconds": 60}, {"reagent": "water", "seconds": 5}, ...]
    recorded_steps_json = models.JSONField(default=list)
    score = models.PositiveIntegerField(validators=[MaxValueValidator(100)])
    outcome_diagnosis = models.CharField(max_length=200)
    is_passed = models.BooleanField(default=False)
    lab_notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        indexes = [
            # Practice log and dashboard stats query "this user's latest attempts".
            models.Index(fields=['user', '-completed_at'], name='attempt_user_recent_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(score__lte=100), name='attempt_score_max_100'),
        ]

    def __str__(self):
        return f'{self.user} · {self.scenario} · {self.score}/100'
