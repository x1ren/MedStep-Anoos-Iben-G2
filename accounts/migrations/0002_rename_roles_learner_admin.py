"""Rename roles: student -> learner, instructor -> admin.

Updates the field's choices/default and converts existing rows so users
created before this change keep equivalent access. Reversible.
"""

from django.db import migrations, models

FORWARD = {'student': 'learner', 'instructor': 'admin'}
BACKWARD = {new: old for old, new in FORWARD.items()}


def convert_roles(mapping):
    def run(apps, schema_editor):
        User = apps.get_model('accounts', 'User')
        for old, new in mapping.items():
            User.objects.filter(role=old).update(role=new)
    return run


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('learner', 'Student Learner'), ('admin', 'Lab Admin / Content Curator')],
                db_index=True,
                default='learner',
                max_length=20,
            ),
        ),
        migrations.RunPython(convert_roles(FORWARD), convert_roles(BACKWARD)),
    ]
