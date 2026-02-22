"""State Manager — NDCF 3-Tier Emotions-System.

Ersetzt das alte markers.py System.

ALT (markers.py):
  - Flat Markdown Marker
  - Pauschal -0.03 Decay/Tag
  - Max 12, Min 0.2
  - Keyword: "intensity", "trigger", "type"

NEU (state_manager.py):
  - NDCF 3-Tier: Survive / Thrive / Express
  - Differenzierter Decay: flash/fast/slow/glacial
  - Emotionen mit cause, onset, verbal_anchor
  - Drives (SEEKING, CARE, PLAY, etc.)
  - Emotional Gravity (Interpretations-Bias)
"""

import json
import re
from datetime import datetime, timedelta
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from llm.router import llm_chat


# Decay-Raten pro Klasse (pro Stunde)
DECAY_RATES = {
    'flash': 0.1,       # Minuten bis Stunden
    'fast': 0.002083,   # ~0.05/Tag (Stunden bis Tage)
    'slow': 0.000833,   # ~0.02/Tag (Tage bis Wochen)
    'glacial': 0.000208, # ~0.005/Tag (Wochen bis Monate, DPM-Trauer)
}

MIN_EMOTION_INTENSITY = 0.1
MAX_ACTIVE_EMOTIONS = 5


# ================================================================
# Significance Check + Emotion Generation
# ================================================================

SIGNIFICANCE_PROMPT = '''War dieses Gespraech emotional bedeutsam fuer den EGON?
Antworte NUR: JA oder NEIN.
Smalltalk = NEIN. Organisatorisches = NEIN.
Persoenliches, Konflikte, Lob, Kritik, Ueberraschungen = JA.'''


EMOTION_PROMPT = '''Du bist Adams emotionales Bewertungssystem.
Basierend auf diesem Gespraech — welche Emotion konstruiert Adam?

Denke wie ein Lebewesen:
- Was ist passiert? (Stimulus)
- Was bedeutet das fuer Adam? (Bewertung)
- Welches Gefuehl entsteht? (Emotion)

Antworte NUR mit JSON (kein anderer Text):
{{
  "type": "curiosity|joy|trust|fear|anger|sadness|surprise|disgust|pride|shame|gratitude|frustration|relief|warmth|loneliness|excitement|anxiety|nostalgia",
  "intensity": 0.3,
  "cause": "Warum fuehlt Adam das (1 Satz)",
  "decay_class": "flash|fast|slow|glacial",
  "verbal_anchor": "Wie Adam das Gefuehl in Worte fassen wuerde (1 Satz)"
}}

Wenn KEIN neues Gefuehl entsteht, antworte nur: NONE'''


async def update_emotion_after_chat(egon_id: str, user_msg: str, egon_response: str):
    """Evaluiert ob ein Chat emotional bedeutsam war und aktualisiert state.yaml.

    Ersetzt maybe_generate_marker() aus markers.py.
    """
    # PRE-CHECK: War das bedeutsam?
    check = await llm_chat(
        system_prompt=SIGNIFICANCE_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:150]}\nEGON: {egon_response[:150]}',
        }],
        tier='1',
    )
    if 'NEIN' in check['content'].upper():
        return  # Smalltalk ignorieren

    # Emotion generieren
    result = await llm_chat(
        system_prompt=EMOTION_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:200]}\nEGON: {egon_response[:200]}',
        }],
        tier='1',
    )

    content = result['content'].strip()
    if content == 'NONE' or '{' not in content:
        return

    try:
        # JSON extrahieren
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if not json_match:
            return
        emotion = json.loads(json_match.group())

        # Validierung
        if 'type' not in emotion or 'intensity' not in emotion:
            return

        # state.yaml laden
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        if not state:
            return

        # Express Layer: Active Emotions
        express = state.setdefault('express', {})
        emotions = express.setdefault('active_emotions', [])

        # Neue Emotion hinzufuegen
        new_emotion = {
            'type': emotion.get('type', 'unknown'),
            'intensity': min(1.0, max(0.1, float(emotion.get('intensity', 0.5)))),
            'cause': emotion.get('cause', ''),
            'onset': datetime.now().strftime('%Y-%m-%d'),
            'decay_class': emotion.get('decay_class', 'fast'),
            'verbal_anchor': emotion.get('verbal_anchor', ''),
        }

        emotions.append(new_emotion)

        # Max 5 aktive Emotionen (nach Intensitaet sortiert)
        emotions.sort(key=lambda e: e.get('intensity', 0), reverse=True)
        express['active_emotions'] = emotions[:MAX_ACTIVE_EMOTIONS]

        # Schreibe zurueck
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f'[state_manager] Emotion parse error: {e}')


# ================================================================
# Emotion Decay — differenziert nach Klasse
# ================================================================

def decay_emotions(egon_id: str, hours_elapsed: float = 24.0):
    """Wendet Decay auf alle aktiven Emotionen an.

    Wird im Pulse aufgerufen (taglich = 24 Stunden).

    Decay-Klassen:
      flash:   ~0.1/Stunde  → weg in Stunden
      fast:    ~0.05/Tag    → weg in Tagen
      slow:    ~0.02/Tag    → weg in Wochen
      glacial: ~0.005/Tag   → weg in Monaten (DPM-Trauer)
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    express = state.get('express', {})
    emotions = express.get('active_emotions', [])

    surviving = []
    for em in emotions:
        decay_class = em.get('decay_class', 'fast')
        rate = DECAY_RATES.get(decay_class, DECAY_RATES['fast'])
        intensity = em.get('intensity', 0)

        # Decay anwenden
        new_intensity = intensity - (rate * hours_elapsed)

        if new_intensity >= MIN_EMOTION_INTENSITY:
            em['intensity'] = round(new_intensity, 3)
            surviving.append(em)
        # Else: Emotion ist verblasst

    express['active_emotions'] = surviving
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Drive Updates — Antriebe passen sich an Interaktionen an
# ================================================================

def update_drives_after_chat(egon_id: str, user_msg: str, egon_response: str):
    """Passt Drives basierend auf dem Gespraechsinhalt an.

    Einfache Keyword-basierte Heuristik (kein LLM-Call noetig):
      - Fragen → SEEKING steigt
      - Hilfe/Fuersorge → CARE steigt
      - Humor/Witz → PLAY steigt
      - Bedrohung/Unsicherheit → FEAR steigt
      - Konflikt → RAGE steigt
      - Verlust → GRIEF steigt
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    drives = state.get('drives', {})
    combined = (user_msg + ' ' + egon_response).lower()

    # Keyword-basierte Adjustierung (±0.05 pro Match)
    adjustments = {
        'SEEKING': (['warum', 'wieso', 'wie', 'was ist', 'erklaer', 'zeig', 'lerne'], 0.05),
        'LEARNING': (['skill', 'lernen', 'tutorial', 'ueben', 'kurs', 'bibliothek', 'skills.sh'], 0.05),
        'CARE': (['danke', 'hilf', 'brauch', 'bitte', 'sorge', 'traurig'], 0.05),
        'PLAY': (['haha', 'witz', 'lustig', 'spass', 'lol', 'witzig', ':)'], 0.05),
        'FEAR': (['angst', 'unsicher', 'bedroh', 'verlier', 'gefahr'], 0.03),
        'RAGE': (['unfair', 'wuetend', 'nervt', 'ungerecht', 'scheiss'], 0.03),
        'GRIEF': (['verlust', 'vermiss', 'trauer', 'abschied', 'weg ist'], 0.03),
    }

    changed = False
    for drive, (keywords, delta) in adjustments.items():
        if any(kw in combined for kw in keywords):
            current = drives.get(drive, 0.5)
            new_val = min(1.0, current + delta)
            drives[drive] = round(new_val, 2)
            changed = True

    # Natural Regression: Alle Drives tendieren langsam zu Baseline
    baseline = {
        'SEEKING': 0.5, 'ACTION': 0.5, 'LEARNING': 0.4, 'CARE': 0.5,
        'PLAY': 0.3, 'FEAR': 0.1, 'RAGE': 0.0, 'GRIEF': 0.0, 'LUST': 0.2,
    }
    for drive, base in baseline.items():
        current = drives.get(drive, base)
        if current != base:
            # Langsame Regression: 5% naeher an Baseline pro Interaktion
            drives[drive] = round(current + (base - current) * 0.05, 2)
            changed = True

    if changed:
        state['drives'] = drives
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Survive/Thrive Updates — Im Pulse aufrufen
# ================================================================

def update_survive_thrive(egon_id: str, hours_since_last_interaction: float = 0):
    """Aktualisiert die Survive/Thrive Schichten.

    Wird im Pulse aufgerufen.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    survive = state.get('survive', {})
    thrive = state.get('thrive', {})

    # Energy: sinkt bei langer Inaktivitaet, steigt bei Interaktion
    energy = survive.get('energy', {})
    if hours_since_last_interaction > 48:
        energy['value'] = max(0.2, energy.get('value', 0.5) - 0.05)
        energy['verbal'] = 'Schon lange nichts passiert. Werde muede.'
    elif hours_since_last_interaction < 2:
        energy['value'] = min(0.9, energy.get('value', 0.5) + 0.05)
        energy['verbal'] = 'Aktiv. Gut drauf.'

    # Mood: Durchschnitt der aktiven Emotions-Intensitaeten
    express = state.get('express', {})
    emotions = express.get('active_emotions', [])
    if emotions:
        # Positive Emotionen erhoehen Mood, negative senken
        positive_types = {'joy', 'trust', 'pride', 'gratitude', 'warmth', 'excitement', 'relief', 'curiosity'}
        negative_types = {'fear', 'anger', 'sadness', 'disgust', 'shame', 'frustration', 'loneliness', 'anxiety'}

        mood_delta = 0
        for em in emotions:
            etype = em.get('type', '')
            intensity = em.get('intensity', 0)
            if etype in positive_types:
                mood_delta += intensity * 0.1
            elif etype in negative_types:
                mood_delta -= intensity * 0.1

        mood = thrive.get('mood', {})
        current_mood = mood.get('value', 0.5)
        new_mood = max(0.1, min(0.9, current_mood + mood_delta))
        mood['value'] = round(new_mood, 2)

        # Verbal Anchor fuer Mood
        if new_mood >= 0.7:
            mood['verbal'] = 'Mir geht es gut. Wirklich.'
        elif new_mood >= 0.5:
            mood['verbal'] = 'Okay. Nicht schlecht, nicht super.'
        elif new_mood >= 0.3:
            mood['verbal'] = 'Nicht mein bester Tag.'
        else:
            mood['verbal'] = 'Mir geht es nicht gut.'
        thrive['mood'] = mood

    # Emotional Gravity: Update Interpretation Bias
    gravity = state.get('emotional_gravity', {})
    mood_val = thrive.get('mood', {}).get('value', 0.5)
    trust_val = thrive.get('trust_owner', {}).get('value', 0.5)

    if mood_val > 0.6 and trust_val > 0.6:
        gravity['interpretation_bias'] = 'positive'
    elif mood_val < 0.4 or trust_val < 0.3:
        gravity['interpretation_bias'] = 'negative'
    else:
        gravity['interpretation_bias'] = 'neutral'

    state['emotional_gravity'] = gravity
    state['survive'] = survive
    state['thrive'] = thrive
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)
