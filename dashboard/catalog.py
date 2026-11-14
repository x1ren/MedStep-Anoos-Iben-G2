"""MedStep lab catalog: modules, bacterial specimens, scenarios and
quick-start practice cards shown on the dashboards.

Increment 1 keeps the catalog as static data. Database-backed editing by
Lab Admins and the interactive simulations arrive in later increments.
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

SPECIMENS = [
    {'slug': 's-aureus', 'name': 'Staphylococcus aureus', 'gram': 'positive',
     'morphology': 'Cocci in clusters'},
    {'slug': 's-pyogenes', 'name': 'Streptococcus pyogenes', 'gram': 'positive',
     'morphology': 'Cocci in chains'},
    {'slug': 'b-subtilis', 'name': 'Bacillus subtilis', 'gram': 'positive',
     'morphology': 'Rods (spore-forming)'},
    {'slug': 'e-coli', 'name': 'Escherichia coli', 'gram': 'negative',
     'morphology': 'Rods (bacilli)'},
    {'slug': 'p-aeruginosa', 'name': 'Pseudomonas aeruginosa', 'gram': 'negative',
     'morphology': 'Rods (bacilli)'},
    {'slug': 'n-gonorrhoeae', 'name': 'Neisseria gonorrhoeae', 'gram': 'negative',
     'morphology': 'Diplococci'},
]

SCENARIOS = [
    {'slug': 'gram-single-sa', 'title': 'Single-organism smear',
     'module': 'gram-staining', 'specimens': ['s-aureus'],
     'difficulty': 'Beginner', 'status': 'active'},
    {'slug': 'gram-mixed', 'title': 'Mixed smear: Gram-positive vs Gram-negative',
     'module': 'gram-staining', 'specimens': ['s-aureus', 'e-coli'],
     'difficulty': 'Intermediate', 'status': 'active'},
    {'slug': 'gram-overdecolorize', 'title': 'Over-decolorization challenge',
     'module': 'gram-staining', 'specimens': ['s-pyogenes'],
     'difficulty': 'Advanced', 'status': 'draft'},
    {'slug': 'streak-pure', 'title': 'Pure culture streak',
     'module': 'quadrant-streak', 'specimens': ['e-coli'],
     'difficulty': 'Beginner', 'status': 'active'},
    {'slug': 'streak-mixed', 'title': 'Isolate colonies from a mixed broth',
     'module': 'quadrant-streak', 'specimens': ['s-aureus', 'p-aeruginosa'],
     'difficulty': 'Intermediate', 'status': 'draft'},
]

QUICK_STARTS = [
    {'title': 'Classic Gram stain run', 'module': 'gram-staining', 'minutes': 5,
     'icon': 'bi-palette2', 'tile': 'ms-tile-gram',
     'blurb': 'Run all four reagents on a single-organism smear.'},
    {'title': 'Decolorizer timing drill', 'module': 'gram-staining', 'minutes': 2,
     'icon': 'bi-stopwatch', 'tile': 'ms-tile-neg',
     'blurb': 'Practice stopping the alcohol rinse inside the 5–15 s window.'},
    {'title': 'Four-quadrant streak', 'module': 'quadrant-streak', 'minutes': 4,
     'icon': 'bi-circle-half', 'tile': 'ms-tile-streak',
     'blurb': 'Flame, cool and drag through all four quadrants.'},
]


def _by_slug(items):
    return {item['slug']: item for item in items}


def scenarios_with_details():
    """Scenarios with their module title and specimen records resolved."""
    modules, specimens = _by_slug(LAB_MODULES), _by_slug(SPECIMENS)
    return [
        {
            **scenario,
            'module_title': modules[scenario['module']]['title'],
            'specimen_list': [specimens[s] for s in scenario['specimens']],
        }
        for scenario in SCENARIOS
    ]
