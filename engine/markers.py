"""Marker System — Somatische Marker mit Lifecycle Management.

FALLE: Marker-Inflation. Nach 100 Chats hat Adam 80 Marker.
LOESUNG: Max 12 aktive Marker, Decay 0.03/Tag, Min 0.2.
"""

import os
import re
import json
from datetime import datetime
from config import EGON_DATA_DIR
from llm.router import llm_chat

MAX_ACTIVE_MARKERS = 12
MIN_INTENSITY = 0.2
DECAY_PER_DAY = 0.03

SIGNIFICANCE_PROMPT = '''War dieses Gespraech emotional bedeutsam?
Antworte NUR: JA oder NEIN.'''

MARKER_PROMPT = '''Basierend auf diesem Gespraech:
Hat der EGON ein neues Gefuehl entwickelt?
Wenn JA, antworte mit JSON:
{"type": "...", "trigger": "...", "intensity": 0.5}
Wenn NEIN, antworte nur: NONE'''


async def maybe_generate_marker(egon_id: str, user_msg: str, response: str):
    """Nur Marker generieren wenn Gespraech BEDEUTSAM war."""
    # PRE-CHECK: War das Gespraech emotional/wichtig?
    check = await llm_chat(
        system_prompt=SIGNIFICANCE_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:150]}\nEGON: {response[:150]}',
        }],
    )
    if 'NEIN' in check['content'].upper():
        return  # Small-Talk ignorieren

    # Marker generieren
    result = await llm_chat(
        system_prompt=MARKER_PROMPT,
        messages=[{
            'role': 'user',
            'content': f'User: {user_msg[:200]}\nEGON: {response[:200]}',
        }],
    )

    content = result['content'].strip()
    if content == 'NONE' or '{' not in content:
        return

    try:
        # JSON aus der Antwort extrahieren
        json_match = re.search(r'\{[^}]+\}', content)
        if not json_match:
            return
        marker = json.loads(json_match.group())

        path = os.path.join(EGON_DATA_DIR, egon_id, 'markers.md')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'\n---\n')
            f.write(f'type: {marker.get("type", "unknown")}\n')
            f.write(f'trigger: {marker.get("trigger", "")}\n')
            f.write(f'intensity: {marker.get("intensity", 0.5)}\n')
            f.write(f'origin: {datetime.now().strftime("%Y-%m-%d")}\n')
            f.write(f'decay_rate: {DECAY_PER_DAY}\n')
            f.write(f'---\n')
    except (json.JSONDecodeError, KeyError):
        pass  # LLM gab kein valides JSON


def decay_markers(egon_id: str):
    """Taeglicher Marker-Zerfall (im Pulse aufrufen)."""
    path = os.path.join(EGON_DATA_DIR, egon_id, 'markers.md')
    if not os.path.isfile(path):
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Header behalten
    header_lines = []
    for line in content.split('\n'):
        if line.startswith('#') or (not line.strip() and not header_lines):
            header_lines.append(line)
        elif line.startswith('#'):
            header_lines.append(line)
        else:
            break

    entries = re.split(r'\n---\n', content)
    alive = []
    for entry in entries:
        entry = entry.strip()
        if not entry or 'intensity:' not in entry:
            continue

        intensity_match = re.search(r'intensity:\s*([\d.]+)', entry)
        if not intensity_match:
            continue

        intensity = float(intensity_match.group(1)) - DECAY_PER_DAY
        if intensity >= MIN_INTENSITY:
            entry = re.sub(
                r'intensity:\s*[\d.]+',
                f'intensity: {round(intensity, 3)}',
                entry,
            )
            alive.append((intensity, entry))

    # Sortiere nach Intensitaet, behalte Top 12
    alive.sort(key=lambda x: x[0], reverse=True)
    alive = alive[:MAX_ACTIVE_MARKERS]

    header = '\n'.join(header_lines)
    entries_text = '\n---\n'.join(e[1] for e in alive)
    new_content = f'{header}\n\n---\n{entries_text}\n---\n' if alive else f'{header}\n'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
