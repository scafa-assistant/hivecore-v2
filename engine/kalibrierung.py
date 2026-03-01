"""Patch 17 — Zentrale Kalibrierung + Decision-Log.

Alle Schwellenwerte an EINEM Ort. Decision-Log als Black Box
damit man bei jedem 'komischen' Moment nachschauen kann
welche Sperre gegriffen hat und warum.

Biologisches Prinzip:
  Regulation dient dem Ueberleben, nicht der Normalisierung.
  ERST fuehlen, DANN regulieren, ZULETZT reflektieren.

Die 4 Sperren schuetzen sich gegenseitig:
  - Nachhall bremst Homoestase (Peaks nicht kappen)
  - Floor hebt Thalamus (aufgewuehlte EGONs verarbeiten ALLES intensiv)
  - Ueberflutung sperrt Metacognition (frische Wunden fuehlen lassen)
  - Flashbulb schuetzt vor Decay (traumatische Erinnerungen vergisst man nicht)
"""

from collections import defaultdict
import time


# ================================================================
# Zentrale Schwellenwerte
# ================================================================

# Homoestase (Patch 7)
NOTFALL_SCHWELLE = 0.95          # Ueber 0.95: Verstaerkte Korrektur
NOTFALL_KORREKTUR = 1.5          # Sanftere Bremse (war: 2.0)

# Thalamus (Patch 8)
THALAMUS_EMOTION_FLOOR = 0.75    # Ab hier mindestens Pfad C
# Biologisch: Amygdala-Uebernahme bei hoher Erregung

# Metacognition (Patch 11)
METACOG_UEBERFLUTET = 0.85       # Darueber: Metacognition offline
# Biologisch: Praefrontaler Kortex geht bei Ueberflutung offline
METACOG_COOLDOWN = 5             # Gespraeche nach Korrektur (war: 3)
METACOG_EGO_MIN = 3              # Ego-Widerspruch: Erst nach 3x korrigieren

# Decay (Patch 13)
FLASHBULB_MARKER = 0.85          # Marker darueber: Flashbulb Memory
FLASHBULB_FLOOR = 0.10           # Retention-Floor bis Nacht-Pulse konsolidiert
# Brown & Kulik 1977: Traumatische Erinnerungen vergisst man nicht


# ================================================================
# Decision-Log (In-Memory Black Box)
# ================================================================

_decision_log = defaultdict(list)
MAX_LOG_ENTRIES = 100


def log_decision(egon_id: str, system: str, entscheidung: str,
                 details: dict = None):
    """Loggt eine Kalibrierungs-Entscheidung in die Black Box.

    Args:
        egon_id: Agent-ID
        system: 'homoestase' | 'thalamus' | 'metacognition' | 'decay'
        entscheidung: Kurzbeschreibung was passiert ist
        details: Optionale Zusatzinfos (Werte, Schwellen etc.)
    """
    entry = {
        'ts': time.time(),
        'system': system,
        'entscheidung': entscheidung,
        'details': details or {},
    }
    log = _decision_log[egon_id]
    log.append(entry)
    if len(log) > MAX_LOG_ENTRIES:
        _decision_log[egon_id] = log[-MAX_LOG_ENTRIES:]

    try:
        from engine.neuroplastizitaet import ne_emit
        ne_emit(egon_id, 'AKTIVIERUNG', 'praefrontal', 'praefrontal', label=f'Kalibrierung: {entscheidung}', intensitaet=0.4, animation='pulse')
    except Exception:
        pass


def get_decision_log(egon_id: str, seit_ts: float = 0) -> list:
    """Liest Decision-Log seit Timestamp.

    Args:
        egon_id: Agent-ID
        seit_ts: Unix-Timestamp — nur Eintraege danach

    Returns:
        Liste der Decision-Log-Eintraege
    """
    return [e for e in _decision_log.get(egon_id, []) if e['ts'] > seit_ts]


def clear_decision_log(egon_id: str) -> int:
    """Leert den Decision-Log eines Agents. Returns: Anzahl geloeschter Eintraege."""
    count = len(_decision_log.get(egon_id, []))
    _decision_log[egon_id] = []
    return count
