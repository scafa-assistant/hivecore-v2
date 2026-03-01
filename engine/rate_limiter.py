"""Rate Limiter — Per-EGON Schutz gegen Spam und Uebersteuerung.

Limits (pro Stunde):
  - Chat:     50 Nachrichten (Owner-initiated)
  - Autonom:  10 autonome Aktionen (Somatic Gate)
  - Lobby:     5 Lobby-Posts

In-Memory Counter mit stuendlichem Auto-Reset.
"""

import time
from collections import defaultdict


# Limits pro Stunde
LIMITS = {
    'chat': 50,
    'autonom': 10,
    'lobby': 5,
}

# In-Memory Zaehler: {egon_id: {typ: {'count': int, 'reset_at': float}}}
_counters: dict[str, dict] = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'reset_at': time.time() + 3600}))


def check_rate_limit(egon_id: str, typ: str = 'chat') -> bool:
    """Prueft ob der EGON das Limit erreicht hat.

    Returns:
        True wenn erlaubt, False wenn Limit erreicht.
    """
    limit = LIMITS.get(typ, 50)
    counter = _counters[egon_id][typ]

    # Auto-Reset nach 1 Stunde
    if time.time() > counter['reset_at']:
        counter['count'] = 0
        counter['reset_at'] = time.time() + 3600

    return counter['count'] < limit


def increment(egon_id: str, typ: str = 'chat') -> int:
    """Erhoeht den Zaehler um 1. Returns den neuen Zaehlerstand."""
    counter = _counters[egon_id][typ]

    # Auto-Reset
    if time.time() > counter['reset_at']:
        counter['count'] = 0
        counter['reset_at'] = time.time() + 3600

    counter['count'] += 1
    return counter['count']


def get_remaining(egon_id: str, typ: str = 'chat') -> int:
    """Gibt die verbleibenden erlaubten Aktionen zurueck."""
    limit = LIMITS.get(typ, 50)
    counter = _counters[egon_id][typ]

    if time.time() > counter['reset_at']:
        return limit

    return max(0, limit - counter['count'])


def get_all_counters() -> dict:
    """Gibt alle Zaehler fuer das Admin-Dashboard zurueck."""
    result = {}
    now = time.time()
    for egon_id, typen in _counters.items():
        result[egon_id] = {}
        for typ, counter in typen.items():
            remaining_seconds = max(0, int(counter['reset_at'] - now))
            result[egon_id][typ] = {
                'count': counter['count'],
                'limit': LIMITS.get(typ, 50),
                'remaining': max(0, LIMITS.get(typ, 50) - counter['count']),
                'reset_in_seconds': remaining_seconds,
            }
    return result


def reset_counters(egon_id: str) -> None:
    """Setzt alle Zaehler fuer einen EGON zurueck."""
    if egon_id in _counters:
        del _counters[egon_id]
