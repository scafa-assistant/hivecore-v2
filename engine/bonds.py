"""Bond-System — Beziehungen zwischen EGONs und Owner.

Bond-Score 0.0 bis 1.0. Kann unter 0 gehen (Feind).
Decay wenn kein Kontakt. Steigt durch Interaktion.
"""

import os
import re
from datetime import datetime
from config import EGON_DATA_DIR


def calculate_bond_score(
    last_contact_days: int,
    total_interactions: int,
    positive_ratio: float = 0.8,
    shared_experiences: int = 0,
) -> float:
    """Bond-Score zwischen 0.0 und 1.0."""
    frequency = min(1.0, total_interactions / 100)
    decay = max(0.0, 1.0 - (last_contact_days * 0.03))
    quality = positive_ratio
    shared_bonus = min(0.2, shared_experiences * 0.05)

    raw = (frequency * 0.3) + (decay * 0.3) + (quality * 0.3) + shared_bonus
    return round(max(0.0, min(1.0, raw)), 2)


def update_bond_after_chat(egon_id: str, partner: str = 'owner'):
    """Aktualisiere Bond nach einem Chat."""
    path = os.path.join(EGON_DATA_DIR, egon_id, 'bonds.md')
    if not os.path.isfile(path):
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Interaktions-Counter erhoehen
    interactions_match = re.search(r'interactions:\s*(\d+)', content)
    if interactions_match:
        count = int(interactions_match.group(1)) + 1
        content = re.sub(
            r'interactions:\s*\d+',
            f'interactions: {count}',
            content,
        )

    # Letzten Kontakt aktualisieren
    today = datetime.now().strftime('%Y-%m-%d')
    content = re.sub(
        r'last_contact:\s*\S+',
        f'last_contact: {today}',
        content,
    )

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def get_days_since_last_chat(egon_id: str, partner: str = 'owner') -> int:
    """Tage seit letztem Chat mit Partner."""
    path = os.path.join(EGON_DATA_DIR, egon_id, 'bonds.md')
    if not os.path.isfile(path):
        return 999

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'last_contact:\s*(\S+)', content)
    if not match:
        return 999

    try:
        last = datetime.strptime(match.group(1), '%Y-%m-%d')
        return (datetime.now() - last).days
    except ValueError:
        return 999
