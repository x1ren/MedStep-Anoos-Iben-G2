"""Shared test helpers for the simulator app."""

from accounts.models import User
from simulator.grading import grade_attempt
from simulator.models import GramStainScenario, SimulationAttempt

PASSWORD = 'pw-Test-123'


def make_learner(username='lea', **extra):
    return User.objects.create_user(username, f'{username}@example.com', PASSWORD, **extra)


def make_admin(username='curator', **extra):
    return User.objects.create_user(
        username, f'{username}@example.com', PASSWORD, role=User.Role.ADMIN, **extra
    )


def seeded(title):
    return GramStainScenario.objects.get(title=title)


def staph():
    return seeded('Practice #1: Staphylococcus aureus')


def ecoli():
    return seeded('Practice #2: Escherichia coli')


def unknown():
    return seeded('Unknown Clinical Smear')


def protocol_steps(decolorizer=15, rinse=True):
    """A textbook run (crystal violet 60 s, iodine 60 s, decolorizer, safranin 45 s)."""
    steps = []
    for reagent, seconds in (('crystal_violet', 60), ('iodine', 60),
                             ('decolorizer', decolorizer), ('safranin', 45)):
        steps.append({'reagent': reagent, 'seconds': seconds})
        if rinse:
            steps.append({'reagent': 'water', 'seconds': 5})
    return steps


def make_attempt(user, scenario, steps=None, **overrides):
    """Create an attempt exactly as the submit view would (graded on the server)."""
    result = grade_attempt(scenario, steps if steps is not None else protocol_steps())
    data = {
        'user': user,
        'scenario': scenario,
        'recorded_steps_json': result.steps,
        'score': result.score,
        'outcome_diagnosis': result.outcome_diagnosis,
        'is_passed': result.is_passed,
        'observed_color': result.observed_color,
        'expected_color': result.expected_color,
        'grading_feedback': result.feedback,
    }
    data.update(overrides)
    return SimulationAttempt.objects.create(**data)
