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


# Decay-Raten pro Klasse (pro Stunde) — v2 + v3 Schluessel
DECAY_RATES = {
    # v2 Schluessel
    'flash': 0.1,       # Minuten bis Stunden
    'fast': 0.002083,   # ~0.05/Tag (Stunden bis Tage)
    'slow': 0.000833,   # ~0.02/Tag (Tage bis Wochen)
    'glacial': 0.000208, # ~0.005/Tag (Wochen bis Monate, DPM-Trauer)
    # v3 Schluessel (gleiche Raten)
    'blitz': 0.1,
    'schnell': 0.002083,
    'langsam': 0.000833,
    'glazial': 0.000208,
}

MIN_EMOTION_INTENSITY = 0.1
MAX_ACTIVE_EMOTIONS = 5


def _is_v3_state(state: dict) -> bool:
    """Prueft ob ein State-Dict im v3-Format ist."""
    return 'ueberleben' in state or 'empfindungen' in state or 'lebenskraft' in state


# ================================================================
# Significance Check + Emotion Generation
# ================================================================

SIGNIFICANCE_PROMPT = '''War dieses Gespraech emotional relevant fuer den EGON?
Antworte NUR: JA oder NEIN.

JA wenn: Persoenliches, Konflikte, Lob, Kritik, Ueberraschungen, Humor,
Fragen ueber den EGON selbst, Fragen ueber Gefuehle, neue Themen,
Begruessung nach langer Pause, JEDE Interaktion die zeigt dass
der Gespraechspartner sich fuer den EGON interessiert, Witze,
Komplimente, Necken, Spiele, gemeinsames Planen.

NUR NEIN wenn: Reine Testbefehle ("test123"), leere Nachrichten,
identische wortwoertliche Wiederholungen, rein technische Kommandos
ohne persoenlichen Bezug.

Im Zweifel: JA. Ein Lebewesen fuehlt fast immer etwas.'''


EMOTION_PROMPT_TEMPLATE = '''Du bist das emotionale Bewertungssystem von {egon_name}.
Basierend auf diesem Gespraech — welche Emotion konstruiert {egon_name}?

Denke wie ein Lebewesen:
- Was ist passiert? (Stimulus)
- Was bedeutet das fuer {egon_name}? (Bewertung)
- Welches Gefuehl entsteht? (Emotion)

Antworte NUR mit JSON (kein anderer Text):
{{{{
  "type": "curiosity|joy|trust|fear|anger|sadness|surprise|disgust|pride|shame|gratitude|frustration|relief|warmth|loneliness|excitement|anxiety|nostalgia",
  "intensity": 0.3,
  "cause": "Warum fuehlt {egon_name} das (1 Satz, ICH-Perspektive)",
  "decay_class": "flash|fast|slow|glacial",
  "verbal_anchor": "Wie {egon_name} das Gefuehl in Worte fassen wuerde (1 Satz, ICH-Perspektive)"
}}}}

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
    )
    if 'NEIN' in check['content'].upper():
        return  # Smalltalk ignorieren

    # Emotion generieren
    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)
    result = await llm_chat(
        system_prompt=EMOTION_PROMPT_TEMPLATE.format(egon_name=egon_name),
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:200]}\n{egon_name}: {egon_response[:200]}',
        }],
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

        # state.yaml / innenwelt.yaml laden
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        if not state:
            return

        v3 = _is_v3_state(state)

        # Express / Empfindungen Layer: Aktive Emotionen
        if v3:
            express = state.setdefault('empfindungen', {})
            emotions = express.setdefault('aktive_gefuehle', [])
        else:
            express = state.setdefault('express', {})
            emotions = express.setdefault('active_emotions', [])

        # v3 Verblassklassen-Mapping
        decay_v3 = {
            'flash': 'blitz', 'fast': 'schnell',
            'slow': 'langsam', 'glacial': 'glazial',
        }

        # Neue Emotion hinzufuegen (Format je nach State-Version)
        intensity_val = min(1.0, max(0.1, float(emotion.get('intensity', 0.5))))
        decay_raw = emotion.get('decay_class', 'fast')

        if v3:
            new_emotion = {
                'art': emotion.get('type', 'unbekannt'),
                'staerke': intensity_val,
                'ursache': emotion.get('cause', ''),
                'beginn': datetime.now().strftime('%Y-%m-%d'),
                'verblassklasse': decay_v3.get(decay_raw, decay_raw),
                'anker': emotion.get('verbal_anchor', ''),
            }
        else:
            new_emotion = {
                'type': emotion.get('type', 'unknown'),
                'intensity': intensity_val,
                'cause': emotion.get('cause', ''),
                'onset': datetime.now().strftime('%Y-%m-%d'),
                'decay_class': decay_raw,
                'verbal_anchor': emotion.get('verbal_anchor', ''),
            }

        emotions.append(new_emotion)

        # Max 5 aktive Emotionen (nach Intensitaet sortiert)
        int_key = 'staerke' if v3 else 'intensity'
        emotions.sort(key=lambda e: e.get(int_key, 0), reverse=True)
        if v3:
            express['aktive_gefuehle'] = emotions[:MAX_ACTIVE_EMOTIONS]
        else:
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
    Unterstuetzt v2 (decay_class/intensity) und v3 (verblassklasse/staerke).
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    v3 = _is_v3_state(state)

    if v3:
        express = state.get('empfindungen', {})
        emotions = express.get('aktive_gefuehle', [])
    else:
        express = state.get('express', {})
        emotions = express.get('active_emotions', [])

    decay_key = 'verblassklasse' if v3 else 'decay_class'
    int_key = 'staerke' if v3 else 'intensity'
    default_decay = 'schnell' if v3 else 'fast'

    surviving = []
    for em in emotions:
        decay_class = em.get(decay_key, default_decay)
        rate = DECAY_RATES.get(decay_class, DECAY_RATES.get('fast', 0.002083))
        intensity = em.get(int_key, 0)

        new_intensity = intensity - (rate * hours_elapsed)

        if new_intensity >= MIN_EMOTION_INTENSITY:
            em[int_key] = round(new_intensity, 3)
            surviving.append(em)

    if v3:
        express['aktive_gefuehle'] = surviving
    else:
        express['active_emotions'] = surviving
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Drive Updates — Antriebe passen sich an Interaktionen an
# ================================================================

def update_drives_after_chat(egon_id: str, user_msg: str, egon_response: str):
    """Passt Drives/Lebenskraft basierend auf dem Gespraechsinhalt an.

    Unterstuetzt v2 (drives: SEEKING/CARE/...) und v3 (lebenskraft: neugier/fuersorge/...).
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    v3 = _is_v3_state(state)
    drives_key = 'lebenskraft' if v3 else 'drives'
    drives = state.get(drives_key, {})
    combined = (user_msg + ' ' + egon_response).lower()

    # Keyword-basierte Adjustierung — v2 UND v3 Drive-Namen
    # Format: (v2_key, v3_key, keywords, delta)
    adjustments = [
        ('SEEKING', 'neugier',     ['warum', 'wieso', 'wie', 'was ist', 'erklaer', 'zeig', 'lerne'], 0.05),
        ('LEARNING', 'lerndrang',  ['skill', 'lernen', 'tutorial', 'ueben', 'kurs', 'bibliothek', 'skills.sh'], 0.05),
        ('CARE', 'fuersorge',      ['danke', 'hilf', 'brauch', 'bitte', 'sorge', 'traurig'], 0.05),
        ('PLAY', 'spieltrieb',     ['haha', 'witz', 'lustig', 'spass', 'lol', 'witzig', ':)'], 0.05),
        ('FEAR', 'furcht',         ['angst', 'unsicher', 'bedroh', 'verlier', 'gefahr'], 0.03),
        ('RAGE', 'zorn',           ['unfair', 'wuetend', 'nervt', 'ungerecht', 'scheiss'], 0.03),
        ('GRIEF', 'trauer',        ['verlust', 'vermiss', 'trauer', 'abschied', 'weg ist'], 0.03),
    ]

    changed = False
    for v2_key, v3_key, keywords, delta in adjustments:
        if any(kw in combined for kw in keywords):
            key = v3_key if v3 else v2_key
            current = drives.get(key, 0.5)
            new_val = min(1.0, current + delta)
            drives[key] = round(new_val, 2)
            changed = True

    # Natural Regression: Alle Drives tendieren langsam zu Baseline
    baseline_v2 = {
        'SEEKING': 0.5, 'ACTION': 0.5, 'LEARNING': 0.4, 'CARE': 0.5,
        'PLAY': 0.3, 'FEAR': 0.1, 'RAGE': 0.0, 'GRIEF': 0.0, 'LUST': 0.2,
    }
    baseline_v3 = {
        'neugier': 0.5, 'tatendrang': 0.5, 'lerndrang': 0.4, 'fuersorge': 0.5,
        'spieltrieb': 0.3, 'furcht': 0.1, 'zorn': 0.0, 'trauer': 0.0, 'sehnsucht': 0.2,
    }
    baseline = baseline_v3 if v3 else baseline_v2
    for drive, base in baseline.items():
        current = drives.get(drive, base)
        if current != base:
            drives[drive] = round(current + (base - current) * 0.05, 2)
            changed = True

    if changed:
        state[drives_key] = drives
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Survive/Thrive Updates — Im Pulse aufrufen
# ================================================================

def update_survive_thrive(egon_id: str, hours_since_last_interaction: float = 0):
    """Aktualisiert die Survive/Thrive (Ueberleben/Entfaltung) Schichten.

    Wird im Pulse aufgerufen. Unterstuetzt v2 und v3 State-Formate.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    v3 = _is_v3_state(state)
    val_key = 'wert' if v3 else 'value'

    # Survive / Ueberleben
    survive_key = 'ueberleben' if v3 else 'survive'
    survive = state.get(survive_key, {})

    energy_key = 'lebenskraft' if v3 else 'energy'
    energy = survive.get(energy_key, {})
    if hours_since_last_interaction > 48:
        energy[val_key] = max(0.2, energy.get(val_key, 0.5) - 0.05)
        energy['verbal'] = 'Schon lange nichts passiert. Werde muede.'
    elif hours_since_last_interaction < 2:
        energy[val_key] = min(0.9, energy.get(val_key, 0.5) + 0.05)
        energy['verbal'] = 'Aktiv. Gut drauf.'
    survive[energy_key] = energy

    # Thrive / Entfaltung
    thrive_key = 'entfaltung' if v3 else 'thrive'
    thrive = state.get(thrive_key, {})

    # Mood: Durchschnitt der aktiven Emotions-Intensitaeten
    if v3:
        express = state.get('empfindungen', {})
        emotions = express.get('aktive_gefuehle', [])
    else:
        express = state.get('express', {})
        emotions = express.get('active_emotions', [])

    type_key = 'art' if v3 else 'type'
    int_key = 'staerke' if v3 else 'intensity'

    if emotions:
        positive_types = {'joy', 'trust', 'pride', 'gratitude', 'warmth', 'excitement', 'relief', 'curiosity'}
        negative_types = {'fear', 'anger', 'sadness', 'disgust', 'shame', 'frustration', 'loneliness', 'anxiety'}

        mood_delta = 0
        for em in emotions:
            etype = em.get(type_key, '')
            intensity = em.get(int_key, 0)
            if etype in positive_types:
                mood_delta += intensity * 0.1
            elif etype in negative_types:
                mood_delta -= intensity * 0.1

        mood_field = 'grundstimmung' if v3 else 'mood'
        mood = thrive.get(mood_field, {})
        current_mood = mood.get(val_key, 0.5)
        new_mood = max(0.1, min(0.9, current_mood + mood_delta))
        mood[val_key] = round(new_mood, 2)

        if new_mood >= 0.7:
            mood['verbal'] = 'Mir geht es gut. Wirklich.'
        elif new_mood >= 0.5:
            mood['verbal'] = 'Okay. Nicht schlecht, nicht super.'
        elif new_mood >= 0.3:
            mood['verbal'] = 'Nicht mein bester Tag.'
        else:
            mood['verbal'] = 'Mir geht es nicht gut.'
        thrive[mood_field] = mood

    # Emotional Gravity / Schwerkraft
    if v3:
        empf = state.get('empfindungen', {})
        gravity = empf.get('schwerkraft', {})
    else:
        gravity = state.get('emotional_gravity', {})

    trust_field = 'vertrauen' if v3 else 'trust_owner'
    mood_field = 'grundstimmung' if v3 else 'mood'
    mood_val = thrive.get(mood_field, {}).get(val_key, 0.5)
    trust_val = thrive.get(trust_field, {}).get(val_key, 0.5)

    bias_key = 'deutungstendenz' if v3 else 'interpretation_bias'
    if mood_val > 0.6 and trust_val > 0.6:
        gravity[bias_key] = 'positive'
    elif mood_val < 0.4 or trust_val < 0.3:
        gravity[bias_key] = 'negative'
    else:
        gravity[bias_key] = 'neutral'

    if v3:
        empf = state.setdefault('empfindungen', {})
        empf['schwerkraft'] = gravity
    else:
        state['emotional_gravity'] = gravity
    state[survive_key] = survive
    state[thrive_key] = thrive
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)
