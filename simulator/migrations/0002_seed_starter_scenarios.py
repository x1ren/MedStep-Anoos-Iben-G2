"""Seed the three starter Gram Staining playground scenarios.

Idempotent: re-running never duplicates rows (matched on the unique title).
Reversible: rolling back removes only these seeded titles.
"""

from django.db import migrations

STARTER_SCENARIOS = [
    {
        'title': 'Practice #1: Staphylococcus aureus',
        'specimen_name': 'Staphylococcus aureus',
        'gram_type': 'gram_positive',
        'cell_shape': 'cocci',
        'difficulty': 'beginner',
        'description': (
            'Grape-like clusters of cocci from a skin abscess swab. Its thick '
            'peptidoglycan wall traps the crystal violet–iodine complex, so '
            'correctly stained cells stay violet after decolorizing.'
        ),
        'crystal_violet_seconds': 60,
        'iodine_seconds': 60,
        'decolorizer_seconds': 15,
        'safranin_seconds': 45,
    },
    {
        'title': 'Practice #2: Escherichia coli',
        'specimen_name': 'Escherichia coli',
        'gram_type': 'gram_negative',
        'cell_shape': 'bacilli',
        'difficulty': 'beginner',
        'description': (
            'Short rods from a urine culture. The thin peptidoglycan layer and '
            'outer membrane release the crystal violet during decolorizing, so '
            'cells take up the safranin counterstain and appear pink.'
        ),
        'crystal_violet_seconds': 60,
        'iodine_seconds': 60,
        'decolorizer_seconds': 15,
        'safranin_seconds': 45,
    },
    {
        'title': 'Unknown Clinical Smear',
        'specimen_name': 'Bacillus cereus',
        'gram_type': 'gram_positive',
        'cell_shape': 'bacilli',
        'difficulty': 'challenge',
        'description': (
            'An unlabelled smear from a food-poisoning investigation. Identify '
            'the Gram reaction and cell shape yourself. Watch the decolorizer: '
            'the window is tight, and over-decolorizing will make these cells '
            'look falsely Gram-negative.'
        ),
        'crystal_violet_seconds': 60,
        'iodine_seconds': 60,
        'decolorizer_seconds': 10,
        'safranin_seconds': 45,
    },
]


def seed(apps, schema_editor):
    Scenario = apps.get_model('simulator', 'GramStainScenario')
    for data in STARTER_SCENARIOS:
        defaults = {key: value for key, value in data.items() if key != 'title'}
        Scenario.objects.get_or_create(title=data['title'], defaults=defaults)


def unseed(apps, schema_editor):
    Scenario = apps.get_model('simulator', 'GramStainScenario')
    Scenario.objects.filter(title__in=[s['title'] for s in STARTER_SCENARIOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
