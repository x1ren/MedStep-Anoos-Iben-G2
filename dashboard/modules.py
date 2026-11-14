"""Catalogue of MedStep lab modules shown on the dashboards.

Phase 1 keeps this as static data. The interactive simulations and the
database tables that record practice attempts arrive in Phase 2.
"""

LAB_MODULES = [
    {
        'slug': 'gram-staining',
        'title': 'Gram Staining',
        'summary': (
            'Differentiate Gram-positive and Gram-negative bacteria by '
            'controlling each reagent exposure on a heat-fixed smear.'
        ),
        'icon': 'bi-palette2',
        'tile': 'ms-tile-gram',
        'duration': '~15 min',
        'steps': [
            ('Prepare & heat-fix smear', ''),
            ('Crystal violet (primary stain)', '60 s'),
            ("Gram's iodine (mordant)", '60 s'),
            ('Decolorize with alcohol/acetone', '5–15 s'),
            ('Safranin (counterstain)', '30–60 s'),
            ('Examine under oil immersion (100×)', ''),
        ],
    },
    {
        'slug': 'quadrant-streak',
        'title': 'Quadrant Streak Plating',
        'summary': (
            'Isolate pure colonies by streaking an inoculum across four '
            'quadrants with proper aseptic technique.'
        ),
        'icon': 'bi-circle-half',
        'tile': 'ms-tile-streak',
        'duration': '~10 min',
        'steps': [
            ('Flame-sterilize the inoculating loop', ''),
            ('Streak quadrant 1 from the inoculum', ''),
            ('Flame, cool, drag into quadrant 2', ''),
            ('Flame, cool, drag into quadrant 3', ''),
            ('Flame, cool, drag into quadrant 4', ''),
            ('Incubate inverted & inspect isolated colonies', '18–24 h'),
        ],
    },
]
