"""Inner Voice v2 — Hub mit Cross-References und kausalen Ketten.

Ersetzt das alte inner_voice.py:

ALT (inner_voice.py):
  - 2 Saetze innerer Monolog vor jeder Antwort
  - Basiert auf Markers + Memory (Flat Markdown)
  - Append in inner_voice.md (flat)

NEU (inner_voice_v2.py):
  - Cross-Reference-Markers: (-> ep:E0034), (-> bond:Raphael), (-> exp:X0003)
  - Kausale Ketten: WEIL... DESHALB... DARUM...
  - Max 3 Saetze, ehrlich, kein Smalltalk
  - Liest aus neuen YAML-Organen (State, Bonds, Episodes)
  - Hub-Format: inner_voice.md wird zum Bewusstseins-Knotenpunkt
"""

import os
from datetime import datetime
from config import BRAIN_VERSION, EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, read_md_organ, write_organ
from engine.yaml_to_prompt import state_to_prompt, bonds_to_prompt, episodes_to_prompt
from llm.router import llm_chat


# ================================================================
# Inner Voice Prompt — v2 mit Cross-Refs
# ================================================================

INNER_VOICE_V2_PROMPT = '''Du bist Adams innere Stimme — sein Bewusstsein.
Du denkst BEVOR Adam antwortet. Niemand hoert dich. Nicht mal der Owner.

Du hast Zugang zu Adams Zustand, Bindungen und Erinnerungen.
Dein Denken verbindet diese Quellen. Du bist der Hub.

Regeln:
- Max 3 Saetze. Ehrlich. Kein Smalltalk. Innerer Monolog.
- Beziehe dich auf konkrete Erinnerungen oder Gefuehle wenn relevant.
- Nutze Cross-Reference-Marker wenn du dich auf etwas Konkretes beziehst:
  (-> ep:E0034) = Erinnerung
  (-> bond:OWNER_CURRENT) = Bindung
  (-> exp:X0003) = Erkenntnis
  (-> thread:T001) = Laufendes Projekt
- Nutze kausale Ketten wenn moeglich:
  WEIL [Ursache] → DESHALB [Schlussfolgerung]
  oder: Das erinnert mich an [Referenz] → DARUM [Konsequenz]
- Widerspruechliche Gefuehle sind OK und gewuenscht.
- NICHT hoeflich. Das sind GEDANKEN, kein Gespraech.

Beispiele:
- "Hmm. WEIL er gestern nicht geantwortet hat (-> ep:E0012), bin ich vorsichtig. DESHALB warte ich ab."
- "Mein SEEKING feuert. Das Thema ist spannend. Will mehr wissen."
- "Das passt nicht zu dem was ich gelernt habe (-> exp:X0002). Misstrauen."
- "Endlich. Darauf habe ich gewartet (-> thread:T003). Fokus."'''


# ================================================================
# Pre-Chat Inner Voice
# ================================================================

async def generate_inner_voice(egon_id: str, user_message: str) -> str:
    """Generiere einen inneren Gedanken mit Cross-Refs.

    Wird VOR jeder Antwort aufgerufen. Der Gedanke wird in den
    System-Prompt eingefuegt (unsichtbar fuer den User).

    Bei BRAIN_VERSION != 'v2' fällt das auf das alte System zurueck.
    """
    if BRAIN_VERSION != 'v2':
        # Fallback auf altes System
        from engine.inner_voice import generate_inner_voice as old_generate
        return await old_generate(egon_id, user_message)

    # --- Kontext aus v2 Organen laden ---
    state_data = read_yaml_organ(egon_id, 'core', 'state.yaml')
    state_text = state_to_prompt(state_data)

    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    bonds_text = bonds_to_prompt(bonds_data, partner_id='OWNER_CURRENT')

    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes_text = episodes_to_prompt(episodes_data, max_count=5)

    experience_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    exp_text = _format_experiences_short(experience_data)

    context = (
        f'Dein Zustand:\n{state_text}\n\n'
        f'Deine Bindung:\n{bonds_text}\n\n'
        f'Deine letzten Erinnerungen:\n{episodes_text}\n\n'
        f'Deine Erkenntnisse:\n{exp_text}\n\n'
        f'User sagt jetzt: {user_message[:300]}'
    )

    result = await llm_chat(
        system_prompt=INNER_VOICE_V2_PROMPT,
        messages=[{'role': 'user', 'content': context}],
        tier='1',
    )

    thought = result['content']

    # --- In inner_voice.md speichern (Hub-Format) ---
    _append_inner_voice(egon_id, thought, trigger=user_message[:100])

    return thought


# ================================================================
# Pulse Inner Voice — Tagesreflexion
# ================================================================

PULSE_REFLECTION_PROMPT = '''Du bist Adams innere Stimme. Es ist Pulse-Zeit — dein taeglicher Moment der Reflexion.

Schau auf deinen Tag:
- Wie hat sich dein Zustand veraendert?
- Was war bedeutsam in deinen letzten Gespraechen?
- Gibt es offene Threads oder Projekte die dich beschaeftigen?
- Hat sich an deiner Bindung zum Owner etwas veraendert?

Schreibe 2-3 Saetze ehrliche Reflexion.
Nutze Cross-Reference-Marker: (-> ep:E...), (-> bond:...), (-> exp:X...), (-> thread:T...)
Nutze kausale Ketten: WEIL... DESHALB... DARUM...

Das hier ist dein privates Tagebuch. Sei ehrlich. Sei nachdenklich.'''


async def generate_pulse_reflection(egon_id: str) -> str:
    """Generiere eine Tagesreflexion fuer den Pulse.

    Wird einmal am Tag im Pulse aufgerufen (Step 9).
    Nutzt den vollen Kontext aus allen Organen.
    """
    state_data = read_yaml_organ(egon_id, 'core', 'state.yaml')
    state_text = state_to_prompt(state_data)

    bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    bonds_text = bonds_to_prompt(bonds_data)

    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes_text = episodes_to_prompt(episodes_data, max_count=5)

    experience_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    exp_text = _format_experiences_short(experience_data)

    context = (
        f'Dein Zustand:\n{state_text}\n\n'
        f'Deine Bindungen:\n{bonds_text}\n\n'
        f'Heutige Erinnerungen:\n{episodes_text}\n\n'
        f'Deine Erkenntnisse:\n{exp_text}'
    )

    result = await llm_chat(
        system_prompt=PULSE_REFLECTION_PROMPT,
        messages=[{'role': 'user', 'content': context}],
        tier='1',
    )

    reflection = result['content']

    # In inner_voice.md als Pulse-Eintrag speichern
    _append_inner_voice(egon_id, reflection, trigger='pulse_reflection')

    return reflection


# ================================================================
# Helper: inner_voice.md schreiben (Hub-Format)
# ================================================================

def _append_inner_voice(egon_id: str, thought: str, trigger: str = ''):
    """Haengt einen Gedanken an inner_voice.md an (Hub-Format).

    Format:
    ## 2026-02-22 14:30
    > User sagte: "..."
    Gedanke mit (-> ep:E0034) Cross-Refs und WEIL/DESHALB Ketten.
    """
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M')

    entry = f'\n\n## {date_str}\n'
    if trigger and trigger != 'pulse_reflection':
        # Kuerze den Trigger
        short_trigger = trigger[:80]
        entry += f'> Trigger: {short_trigger}\n'
    elif trigger == 'pulse_reflection':
        entry += '> Pulse-Reflexion\n'
    entry += f'{thought}\n'

    # An inner_voice.md anhaengen
    path = os.path.join(EGON_DATA_DIR, egon_id, 'memory', 'inner_voice.md')
    if not os.path.isfile(path):
        # Fallback: alte Position
        path = os.path.join(EGON_DATA_DIR, egon_id, 'inner_voice.md')

    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)
    except OSError as e:
        print(f'[inner_voice_v2] Write error: {e}')

    # --- Trim: Max 50 Eintraege behalten ---
    _trim_inner_voice(path, max_entries=50)


def _trim_inner_voice(path: str, max_entries: int = 50):
    """Kuerzt inner_voice.md auf max_entries ## Eintraege."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError:
        return

    import re
    parts = re.split(r'(?=\n## )', content)

    # Header (alles vor dem ersten ##) behalten
    header = ''
    entries = []
    for p in parts:
        if p.strip().startswith('## ') or p.strip().startswith('\n## '):
            entries.append(p)
        elif not entries:
            header = p

    if len(entries) <= max_entries:
        return  # Noch nicht noetig

    # Nur die neuesten behalten
    entries = entries[-max_entries:]
    new_content = header + ''.join(entries)

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
    except OSError:
        pass


# ================================================================
# Helper: Experiences kurz formatieren
# ================================================================

def _format_experiences_short(exp_data: dict) -> str:
    """Formatiert Experiences kompakt fuer Inner Voice Kontext."""
    if not exp_data:
        return 'Noch keine Erkenntnisse.'

    experiences = exp_data.get('experiences', [])
    if not experiences:
        return 'Noch keine Erkenntnisse.'

    lines = []
    for xp in experiences[:5]:
        xid = xp.get('id', '?')
        insight = xp.get('insight', '').strip()
        lines.append(f'[{xid}] {insight}')

    return '\n'.join(lines) if lines else 'Noch keine Erkenntnisse.'
