"""Puls-Hierarchie — Stufe 0 AutoBody.

Wenn das LLM keinen ###BODY### Block generiert,
uebersetzt diese Engine aktive Emotionen in Motor-Worte.

Stufe 0 = Automatisch (kein LLM noetig):
  Emotion aus state.yaml → Motor-Worte aus dem Vokabular.
  Der Koerper bewegt sich IMMER, auch wenn das LLM schweigt.

Die Map wird von chat.py aufgerufen als Fallback.
"""


# ================================================================
# Emotion → Motor Map (Stufe 0: AutoBody)
# ================================================================
# Jede Emotion hat 1-2 Motor-Worte + Default-Intensitaet.
# Die Intensitaet wird spaeter mit der tatsaechlichen Emotion-Intensity skaliert.

EMOTION_MOTOR_MAP = {
    # Basis-Emotionen
    'joy':         {'words': ['jubeln'],                        'intensity': 0.5},
    'excitement':  {'words': ['hand_heben', 'wippen'],          'intensity': 0.6},
    'anger':       {'words': ['wuetend_stehen'],                'intensity': 0.6},
    'fear':        {'words': ['aengstlich'],                    'intensity': 0.5},
    'sadness':     {'words': ['traurig_stehen'],                'intensity': 0.5},
    'surprise':    {'words': ['ueberrascht'],                   'intensity': 0.6},

    # Soziale Emotionen
    'pride':       {'words': ['stolz_stehen', 'kopf_heben'],    'intensity': 0.5},
    'gratitude':   {'words': ['nicken', 'kopf_heben'],          'intensity': 0.5},
    'curiosity':   {'words': ['kopf_neigen', 'nach_vorn_lehnen'], 'intensity': 0.3},
    'love':        {'words': ['nach_vorn_lehnen'],              'intensity': 0.5},

    # Erweiterte Emotionen
    'relief':      {'words': ['zuruecklehnen'],                 'intensity': 0.4},
    'loneliness':  {'words': ['blick_wegdrehen'],               'intensity': 0.4},
    'confusion':   {'words': ['verwirrt'],                      'intensity': 0.5},
    'shame':       {'words': ['blick_wegdrehen'],               'intensity': 0.5},
    'disgust':     {'words': ['kopf_schuetteln'],               'intensity': 0.5},
    'trust':       {'words': ['nicken', 'blick_halten'],        'intensity': 0.4},
    'anticipation': {'words': ['nach_vorn_lehnen', 'wippen'],   'intensity': 0.4},
    'contempt':    {'words': ['arme_verschraenken'],            'intensity': 0.5},
    'anxiety':     {'words': ['wippen', 'gewicht_links'],       'intensity': 0.5},
    'calm':        {'words': ['stehen'],                        'intensity': 0.2},
    'awe':         {'words': ['kopf_heben', 'stehen'],          'intensity': 0.6},
    'frustration': {'words': ['haende_huefte'],                 'intensity': 0.6},
    'hope':        {'words': ['kopf_heben'],                    'intensity': 0.4},
    'guilt':       {'words': ['blick_wegdrehen'],               'intensity': 0.4},
}

# Schweigen-Body — wenn das LLM *schweigt* antwortet
SCHWEIGEN_BODY = {'words': ['blick_wegdrehen'], 'intensity': 0.3, 'reason': 'Bewusstes Schweigen'}


def get_motor_fallback(primary_emotion: str, emotion_intensity: float = 0.5) -> dict | None:
    """Gibt Motor-Daten fuer eine Emotion zurueck (Stufe 0 AutoBody).

    Args:
        primary_emotion: Name der staerksten aktiven Emotion
        emotion_intensity: Staerke der Emotion (0.0-1.0)

    Returns:
        Body-Daten dict {"words": [...], "intensity": float} oder None
    """
    fallback = EMOTION_MOTOR_MAP.get(primary_emotion)
    if not fallback:
        return None

    # Intensitaet skalieren: Base × Emotion × 1.5 (cap bei 1.0)
    scaled_intensity = round(
        min(fallback['intensity'] * emotion_intensity * 1.5, 1.0), 2,
    )

    return {
        'words': list(fallback['words']),
        'intensity': scaled_intensity,
        'reason': f'AutoBody: {primary_emotion}',
    }
