from django.test import TestCase
from django.urls import reverse


class LandingPageTests(TestCase):
    def test_home_renders_with_base_layout(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertTemplateUsed(response, 'partials/_navbar.html')

    def test_home_loads_theme_assets(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'bootstrap@5.3.3/dist/css/bootstrap.min.css')
        self.assertContains(response, '/static/css/medstep.css')
        self.assertContains(response, '/static/img/favicon.svg')

    def test_home_lists_both_lab_modules(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Gram Staining')
        self.assertContains(response, 'Quadrant Streak Plating')
