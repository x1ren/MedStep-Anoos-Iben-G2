"""The browser chemistry (static/js/stain-chemistry.js) must colour cells exactly
like the server grader (simulator.grading.simulate_color).

Runs the JS in Node.js; skipped automatically when Node is not installed.
"""

import json
import random
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.test import SimpleTestCase

from simulator.grading import PROTOCOL, WATER, decolorizer_limits, simulate_color
from simulator.models import GramStainScenario

NODE = shutil.which('node')
CHEMISTRY_JS = Path(settings.BASE_DIR) / 'static' / 'js' / 'stain-chemistry.js'

NODE_RUNNER = """
const chemistry = require(process.argv[1]);
let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  const cases = JSON.parse(input);
  process.stdout.write(JSON.stringify(cases.map(c => chemistry.simulateStain(c.steps, c.config))));
});
"""


def scenario(gram, decolorizer):
    return GramStainScenario(
        title='Parity', specimen_name='x', gram_type=gram, cell_shape='cocci',
        crystal_violet_seconds=60, iodine_seconds=60,
        decolorizer_seconds=decolorizer, safranin_seconds=45,
    )


def js_config(s):
    under, over = decolorizer_limits(s.decolorizer_seconds)
    return {
        'gramType': s.gram_type,
        'targets': {'crystal_violet': s.crystal_violet_seconds, 'iodine': s.iodine_seconds,
                    'decolorizer': s.decolorizer_seconds, 'safranin': s.safranin_seconds},
        'decolorizerLimits': {'under': under, 'over': over},
    }


def build_cases():
    rng = random.Random(2026)
    scenarios = [scenario(g, d) for g in ('gram_positive', 'gram_negative') for d in (10, 15, 30)]
    timing_choices = [1, 3, 5, 9, 10, 14, 15, 16, 20, 21, 30, 31, 45, 60, 90, 200]
    cases = []
    for s in scenarios:
        # Every subset of the protocol in the right order, with assorted timings.
        for mask in range(16):
            for _ in range(4):
                steps = []
                for i, reagent in enumerate(PROTOCOL):
                    if mask & (1 << i):
                        steps.append({'reagent': reagent, 'seconds': rng.choice(timing_choices)})
                        steps.append({'reagent': WATER, 'seconds': 5})
                cases.append((s, steps))
        # Random orders, repeats and missing rinses.
        for _ in range(60):
            steps = [
                {'reagent': rng.choice(PROTOCOL + [WATER]), 'seconds': rng.choice(timing_choices)}
                for _ in range(rng.randint(1, 9))
            ]
            cases.append((s, steps))
    return cases


@skipUnless(NODE, 'Node.js is not installed')
class JsChemistryParityTests(SimpleTestCase):
    def test_browser_and_server_agree_on_cell_colour(self):
        cases = build_cases()
        payload = json.dumps([{'steps': steps, 'config': js_config(s)} for s, steps in cases])
        completed = subprocess.run(
            [NODE, '-e', NODE_RUNNER, str(CHEMISTRY_JS)],
            input=payload, capture_output=True, text=True, timeout=60, check=True,
        )
        js_results = json.loads(completed.stdout)
        self.assertEqual(len(js_results), len(cases))

        for (s, steps), js_color in zip(cases, js_results):
            # The browser shows "unstained" before any dye; the grader calls that colorless.
            js_color = 'colorless' if js_color == 'unstained' else js_color
            with self.subTest(gram=s.gram_type, decolorizer=s.decolorizer_seconds, steps=steps):
                self.assertEqual(js_color, simulate_color(s, steps))

    def test_unstained_before_any_dye(self):
        config = js_config(scenario('gram_positive', 15))
        script = (
            "const c = require(process.argv[1]);"
            f"process.stdout.write(c.simulateStain([], {json.dumps(config)}) + ',' +"
            f" c.simulateStain([{{reagent:'water',seconds:5}}], {json.dumps(config)}));"
        )
        out = subprocess.run([NODE, '-e', script, str(CHEMISTRY_JS)],
                             capture_output=True, text=True, timeout=30, check=True).stdout
        self.assertEqual(out, 'unstained,unstained')


@skipUnless(NODE, 'Node.js is not installed')
class JsSyntaxTests(SimpleTestCase):
    def test_workbench_scripts_parse(self):
        for name in ('stain-chemistry.js', 'workbench.js'):
            with self.subTest(script=name):
                subprocess.run(
                    [NODE, '--check', str(Path(settings.BASE_DIR) / 'static' / 'js' / name)],
                    capture_output=True, text=True, timeout=30, check=True,
                )
