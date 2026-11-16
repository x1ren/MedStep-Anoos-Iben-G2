"""Builds the microscope-field cell layout drawn as SVG on the workbench and report.

Cells are generated from a seed (the scenario id) so a scenario always shows
the same field of view. Coordinates are in a 400x400 viewBox whose visible
field is a circle of radius 190 centred at (200, 200).
"""

import math
import random

FIELD_CENTER = 200
FIELD_RADIUS = 175  # keep cells comfortably inside the 190px field


def _inside_field(x, y, margin=0):
    return math.hypot(x - FIELD_CENTER, y - FIELD_CENTER) <= FIELD_RADIUS - margin


def _random_point(rng, margin):
    while True:
        x, y = rng.uniform(25, 375), rng.uniform(25, 375)
        if _inside_field(x, y, margin):
            return x, y


def build_cocci(rng, clusters=11):
    """Grape-like clusters of round cells (e.g. Staphylococcus)."""
    cells = []
    for _ in range(clusters):
        cx, cy = _random_point(rng, margin=20)
        for _ in range(rng.randint(4, 8)):
            angle = rng.uniform(0, 2 * math.pi)
            distance = rng.uniform(0, 11)
            x, y = cx + distance * math.cos(angle), cy + distance * math.sin(angle)
            if _inside_field(x, y, margin=6):
                cells.append({'kind': 'coccus', 'cx': round(x, 1), 'cy': round(y, 1),
                              'r': round(rng.uniform(5.2, 6.4), 1)})
    return cells


def build_bacilli(rng, count=34):
    """Scattered rod-shaped cells (e.g. E. coli, Bacillus)."""
    cells = []
    for _ in range(count):
        x, y = _random_point(rng, margin=18)
        width, height = rng.uniform(22, 30), rng.uniform(8, 9.5)
        cells.append({
            'kind': 'rod',
            'x': round(x - width / 2, 1), 'y': round(y - height / 2, 1),
            'width': round(width, 1), 'height': round(height, 1),
            'rx': round(height / 2, 1),
            'cx': round(x, 1), 'cy': round(y, 1),
            'angle': rng.randint(0, 179),
        })
    return cells


def build_cells(cell_shape, seed):
    rng = random.Random(seed)
    if cell_shape == 'bacilli':
        return build_bacilli(rng)
    return build_cocci(rng)
