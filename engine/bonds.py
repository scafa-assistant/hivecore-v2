"""Bond-System — Beziehungen zwischen EGONs und Owner.

Bond-Score 0.0 bis 1.0. Kann unter 0 gehen (Feind).
Decay wenn kein Kontakt. Steigt durch Interaktion.
Sentiment-Analyse bestimmt positive_ratio aus echten Gespraechen.
"""

import os
import re
from datetime import datetime
from config import EGON_DATA_DIR


# Keyword-basierte Sentiment-Erkennung (kein extra LLM-Call noetig)
POSITIVE_WORDS = {
    'danke', 'super', 'toll', 'gut', 'perfekt', 'klasse', 'genau', 'richtig',
    'cool', 'nice', 'great', 'geil', 'mega', 'wunderbar', 'fantastisch',
    'ja', 'stimmt', 'absolut', 'bravo', 'hammer', 'top', 'liebe', 'freude',
    'stark', 'hilfreich', 'clever', 'brilliant', 'beeindruckt', 'respekt',
    'vertraue', 'stolz', 'lustig', 'witzig', 'nett', 'bester', 'beste',
}

NEGATIVE_WORDS = {
    'nein', 'falsch', 'schlecht', 'fehler', 'nervig', 'enttaeuscht', 'frustriert',
    'wuetend', 'bloed', 'mist', 'scheisse', 'furchtbar', 'schrecklich', 'dumm',
    'hass', 'doof', 'langweilig', 'nutzlos', 'sinnlos', 'stopp', 'aufhoeren',
    'nervt', 'falsch', 'kaputt', 'verrueckt', 'unfair', 'betrug', 'luege',
}


def estimate_sentiment(user_msg: str) -> float:
    """Schaetze Sentiment aus User-Nachricht. Returns 0.0-1.0.

    Kein extra LLM-Call noetig — keyword-basiert + rolling average.
    Default 0.6 (User redet freiwillig mit EGON = leicht positiv).
    """
    words = set(user_msg.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.6  # Default: leicht positiv
    return round(pos / total, 2)


def _get_stored_positive_ratio(content: str) -> float:
    """Lese gespeicherte positive_ratio aus bonds.md."""
    match = re.search(r'positive_ratio:\s*([\d.]+)', content)
    return float(match.group(1)) if match else 0.6


def calculate_bond_score(
    last_contact_days: int,
    total_interactions: int,
    positive_ratio: float = 0.6,
    shared_experiences: int = 0,
) -> float:
    """Bond-Score zwischen 0.0 und 1.0.

    Formel: frequency(30%) + recency_decay(30%) + quality(30%) + shared(10%)
    """
    frequency = min(1.0, total_interactions / 100)
    decay = max(0.0, 1.0 - (last_contact_days * 0.03))
    quality = positive_ratio
    shared_bonus = min(0.2, shared_experiences * 0.05)

    raw = (frequency * 0.3) + (decay * 0.3) + (quality * 0.3) + shared_bonus
    return round(max(0.0, min(1.0, raw)), 2)


def update_bond_after_chat(
    egon_id: str,
    partner: str = 'owner',
    user_msg: str = '',
):
    """Aktualisiere Bond nach einem Chat — jetzt MIT Sentiment-Analyse."""
    path = os.path.join(EGON_DATA_DIR, egon_id, 'bonds.md')
    if not os.path.isfile(path):
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Interaktions-Counter erhoehen
    interactions_match = re.search(r'interactions:\s*(\d+)', content)
    count = 1
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

    # Sentiment-basierte positive_ratio (Rolling Average)
    if user_msg:
        current_sentiment = estimate_sentiment(user_msg)
        old_ratio = _get_stored_positive_ratio(content)
        # Rolling Average: 90% alter Wert + 10% neuer Wert
        # So aendert sich die Ratio langsam und organisch
        new_ratio = round(old_ratio * 0.9 + current_sentiment * 0.1, 3)
        if re.search(r'positive_ratio:\s*[\d.]+', content):
            content = re.sub(
                r'positive_ratio:\s*[\d.]+',
                f'positive_ratio: {new_ratio}',
                content,
            )
        else:
            # positive_ratio noch nicht in bonds.md → hinzufuegen
            content = re.sub(
                r'(interactions:\s*\d+)',
                f'\\1\npositive_ratio: {new_ratio}',
                content,
            )

    # Bond-Score neu berechnen
    days = 0  # Gerade eben gechattet
    ratio = _get_stored_positive_ratio(content)
    new_score = calculate_bond_score(days, count, ratio)
    if re.search(r'bond_score:\s*[\d.]+', content):
        content = re.sub(
            r'bond_score:\s*[\d.]+',
            f'bond_score: {new_score}',
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
