import json
import math
from urllib.parse import quote

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import User
from simulator.models import GramStainScenario
from simulator.slide import FIELD_CENTER, build_cells

PASSWORD = 'pw-Test-123'


class SlideBuilderTests(SimpleTestCase):
    def test_cocci_are_circles_in_clusters(self):
        cells = build_cells('cocci', seed=1)
        self.assertGreater(len(cells), 25)
        self.assertTrue(all(c['kind'] == 'coccus' for c in cells))

    def test_bacilli_are_rods(self):
        cells = build_cells('bacilli', seed=1)
        self.assertEqual(len(cells), 34)
        for cell in cells:
            self.assertEqual(cell['kind'], 'rod')
            self.assertGreater(cell['width'], cell['height'])  # longer than wide

    def test_cells_stay_inside_field_of_view(self):
        for shape in ('cocci', 'bacilli'):
            for cell in build_cells(shape, seed=7):
                with self.subTest(shape=shape):
                    self.assertLess(math.hypot(cell['cx'] - FIELD_CENTER, cell['cy'] - FIELD_CENTER), 190)

    def test_same_seed_same_field(self):
        self.assertEqual(build_cells('cocci', seed=3), build_cells('cocci', seed=3))
        self.assertNotEqual(build_cells('cocci', seed=3), build_cells('cocci', seed=4))


class WorkbenchPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.learner = User.objects.create_user('lea', 'lea@example.com', PASSWORD)
        cls.admin = User.objects.create_user(
            'curator', 'curator@example.com', PASSWORD, role=User.Role.ADMIN
        )
        cls.staph = GramStainScenario.objects.get(title='Practice #1: Staphylococcus aureus')
        cls.ecoli = GramStainScenario.objects.get(title='Practice #2: Escherichia coli')
        cls.unknown = GramStainScenario.objects.get(title='Unknown Clinical Smear')

    def url(self, scenario):
        return reverse('simulator:workbench', args=[scenario.pk])

    def test_anonymous_redirected_to_login(self):
        url = self.url(self.staph)
        self.assertRedirects(self.client.get(url), f"{reverse('accounts:login')}?next={quote(url)}")

    def test_lab_admin_forbidden(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url(self.staph)).status_code, 403)

    def test_inactive_or_missing_scenario_is_404(self):
        self.client.force_login(self.learner)
        GramStainScenario.objects.filter(pk=self.ecoli.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url(self.ecoli)).status_code, 404)
        self.assertEqual(self.client.get(reverse('simulator:workbench', args=[99999])).status_code, 404)

    def test_learner_sees_workbench(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url(self.staph))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/workbench.html')
        self.assertTemplateUsed(response, 'simulator/_slide.html')
        self.assertContains(response, '/static/css/workbench.css')
        self.assertContains(response, 'Practice #1: Staphylococcus aureus')
        self.assertContains(response, 'data-stain="unstained"')
        self.assertContains(response, 'id="exposureTimer"')
        self.assertContains(response, '+10 s')

    def test_reagent_rack_lists_all_five_with_targets(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url(self.unknown))
        for key in ('crystal_violet', 'iodine', 'decolorizer', 'safranin', 'water'):
            self.assertContains(response, f'data-reagent="{key}"')
        self.assertContains(response, 'target 10 s')  # Unknown smear's tight decolorizer

    def test_slide_draws_shape_of_scenario(self):
        self.client.force_login(self.learner)
        cocci = self.client.get(self.url(self.staph)).content.decode()
        rods = self.client.get(self.url(self.ecoli)).content.decode()
        self.assertGreater(cocci.count('<circle class="ms-cell"'), 25)
        self.assertNotIn('<rect class="ms-cell"', cocci)
        self.assertEqual(rods.count('<rect class="ms-cell"'), 34)

    def test_challenge_hides_specimen_identity(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url(self.unknown))
        self.assertContains(response, 'Unknown specimen')
        self.assertNotContains(response, 'Bacillus cereus')
        self.assertContains(self.client.get(self.url(self.ecoli)), 'Escherichia coli')

    def test_config_for_javascript(self):
        self.client.force_login(self.learner)
        response = self.client.get(self.url(self.unknown))
        config = response.context['workbench_config']
        self.assertEqual(config['targets'], {
            'crystal_violet': 60, 'iodine': 60, 'decolorizer': 10, 'safranin': 45,
        })
        self.assertEqual(config['decolorizerLimits']['over'], 20)
        self.assertContains(response, '<script id="workbench-config" type="application/json">')
        json.dumps(config)  # serialisable
