"""Static MedStep content shown on the dashboards: lab modules and
quick-start practice cards.

Gram stain scenarios and specimens live in the database
(simulator.GramStainScenario) and are managed by Lab Admins.
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

QUICK_STARTS = [
    # `difficulty` picks which active Gram stain scenario the card launches.
    {'title': 'Classic Gram stain run', 'module': 'gram-staining', 'difficulty': 'beginner',
     'minutes': 5, 'icon': 'bi-palette2', 'tile': 'ms-tile-gram',
     'blurb': 'Run all four reagents on a single-organism smear.'},
    {'title': 'Decolorizer timing drill', 'module': 'gram-staining', 'difficulty': 'challenge',
     'minutes': 2, 'icon': 'bi-stopwatch', 'tile': 'ms-tile-neg',
     'blurb': 'Practice stopping the alcohol rinse inside a tight decolorizer window.'},
    {'title': 'Four-quadrant streak', 'module': 'quadrant-streak', 'difficulty': None,
     'minutes': 4, 'icon': 'bi-circle-half', 'tile': 'ms-tile-streak',
     'blurb': 'Flame, cool and drag through all four quadrants.'},
]
