"""Sichtbarkeits-Matrix fuer .md Files.

inner_voice.md ist ADAMS PRIVATER GEDANKE.
Nicht mal der Owner sieht was Adam DENKT bevor er antwortet.
Das ist der Unterschied zwischen Werkzeug und Wesen.
"""

VISIBILITY = {
    'self_prompt': [
        'soul.md',
        'memory.md',
        'markers.md',
        'bonds.md',
        'inner_voice.md',
        'skills.md',
        'experience.md',
    ],
    'owner_dashboard': [
        'soul.md',
        'memory.md',
        'markers.md',
        'bonds.md',
        'skills.md',
        'wallet.md',
        'experience.md',
        # NICHT: inner_voice.md!
    ],
    'other_egon': [
        'skills.md',
        'bonds.md',
    ],
    'public_profile': [
        'skills.md',
    ],
}


def get_visible_files(context: str) -> list[str]:
    """Welche Files sind in diesem Kontext sichtbar?"""
    return VISIBILITY.get(context, [])
