from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

BEFORE = [('accounts', '0001_initial')]
AFTER = [('accounts', '0002_rename_roles_learner_admin')]


class RoleRenameMigrationTests(TransactionTestCase):
    """Users created with the old role names keep equivalent access."""

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def tearDown(self):
        # Leave the test database fully migrated for the next test.
        self.migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_forward_and_backward(self):
        old_apps = self.migrate(BEFORE)
        OldUser = old_apps.get_model('accounts', 'User')
        OldUser.objects.create(username='s', email='s@example.com', role='student')
        OldUser.objects.create(username='i', email='i@example.com', role='instructor')

        new_apps = self.migrate(AFTER)
        NewUser = new_apps.get_model('accounts', 'User')
        self.assertEqual(NewUser.objects.get(username='s').role, 'learner')
        self.assertEqual(NewUser.objects.get(username='i').role, 'admin')

        reverted = self.migrate(BEFORE).get_model('accounts', 'User')
        self.assertEqual(reverted.objects.get(username='s').role, 'student')
        self.assertEqual(reverted.objects.get(username='i').role, 'instructor')
