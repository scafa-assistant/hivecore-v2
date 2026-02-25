"""Social Mapping — Private mentale Modelle anderer EGONs.

Jeder EGON fuehrt private YAML-Dateien die beschreiben wie er andere
EGONs wahrnimmt. Gespeichert in agents/{id}/social_mapping/ueber_{other}.yaml.

Aktualisierung bei:
- Direkter EGON-zu-EGON Interaktion
- Daemmerungs-Reflexion im Pulse
- Beobachtung von Lobby-Nachrichten

Kein EGON kann die Social Map eines anderen lesen.
Owner koennen Social Maps einsehen (fuer Forschung) aber nicht aendern.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import yaml

from config import EGON_DATA_DIR
from llm.router import llm_chat


# ================================================================
# File I/O
# ================================================================

def _social_map_dir(egon_id: str) -> Path:
    return Path(EGON_DATA_DIR) / egon_id / 'social_mapping'


def _social_map_path(egon_id: str, about_id: str) -> Path:
    # Sanitize about_id for filename
    safe_id = about_id.replace('/', '_').replace('\\', '_')
    return _social_map_dir(egon_id) / f'ueber_{safe_id}.yaml'


def _default_social_map(about_id: str) -> dict:
    """Erstellt eine leere Social Map fuer einen noch unbekannten EGON."""
    about_name = about_id.replace('_', ' ').split()[0].capitalize()
    return {
        'identitaet': {
            'id': about_id,
            'name': about_name,
            'kennt_seit': None,
            'interaktionen_gesamt': 0,
        },
        'mein_eindruck': {
            'erster_eindruck': None,
            'aktueller_eindruck': None,
            'veraenderung': None,
        },
        'emotionale_bewertung': {
            'vertrauen': 0.5,
            'naehe': 0.3,
            'respekt': 0.5,
            'unbehagen': 0.1,
            'faszination': 0.3,
        },
        'was_ich_gelernt_habe': [],
        'was_ich_nicht_verstehe': [],
        'meine_vorhersage': None,
    }


# ================================================================
# Public API
# ================================================================

def read_social_map(egon_id: str, about_id: str) -> dict:
    """Liest die Social Map von egon_id ueber about_id.

    Returns Default wenn Datei nicht existiert.
    """
    path = _social_map_path(egon_id, about_id)
    if not path.exists():
        return _default_social_map(about_id)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return _default_social_map(about_id)
        return data
    except Exception:
        return _default_social_map(about_id)


def write_social_map(egon_id: str, about_id: str, data: dict) -> None:
    """Schreibt die Social Map. Erstellt Verzeichnis wenn noetig."""
    path = _social_map_path(egon_id, about_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


async def generate_social_map_update(
    egon_id: str,
    about_id: str,
    interaction_text: str,
) -> dict:
    """LLM-Call um die Social Map basierend auf einer Interaktion zu aktualisieren.

    Liest aktuelle Map, generiert Update, merged Ergebnis.
    Returns: aktualisierte Map.
    """
    current_map = read_social_map(egon_id, about_id)
    egon_name = egon_id.replace('_', ' ').split()[0].capitalize()
    about_name = about_id.replace('_', ' ').split()[0].capitalize()

    # Aktuelle Map als Kontext formatieren
    eindruck = current_map.get('mein_eindruck', {})
    bewertung = current_map.get('emotionale_bewertung', {})
    gelernt = current_map.get('was_ich_gelernt_habe', [])

    map_context = (
        f'Aktueller Eindruck: {eindruck.get("aktueller_eindruck", "Noch keiner")}\n'
        f'Vertrauen: {bewertung.get("vertrauen", 0.5)}, '
        f'Naehe: {bewertung.get("naehe", 0.3)}, '
        f'Respekt: {bewertung.get("respekt", 0.5)}, '
        f'Faszination: {bewertung.get("faszination", 0.3)}\n'
        f'Gelernt: {"; ".join(gelernt[-3:]) if gelernt else "Noch nichts"}'
    )

    prompt = f'''Du bist {egon_name}s soziale Wahrnehmung.
Du beobachtest {about_name} und aktualisierst dein Bild von ihm/ihr.

Dein aktuelles Bild:
{map_context}

Neue Beobachtung:
{interaction_text[:400]}

Antworte NUR mit JSON:
{{
  "aktueller_eindruck": "Wer ist {about_name} fuer dich jetzt? (1-2 Saetze, ICH-Perspektive)",
  "vertrauen_delta": 0.0,
  "naehe_delta": 0.0,
  "respekt_delta": 0.0,
  "faszination_delta": 0.0,
  "neue_beobachtung": "Was hast du gerade ueber {about_name} gelernt? (1 Satz)"
}}

Deltas zwischen -0.1 und +0.1. Positive = mehr, negative = weniger.'''

    try:
        result = await llm_chat(
            system_prompt=prompt,
            messages=[{
                'role': 'user',
                'content': f'Beobachtung:\n{interaction_text[:400]}',
            }],
            tier='1',
        )

        content = result['content'].strip()
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if not json_match:
            return current_map

        update = json.loads(json_match.group())

        # Merge Update in aktuelle Map
        # Eindruck aktualisieren
        eindruck = current_map.setdefault('mein_eindruck', {})
        if not eindruck.get('erster_eindruck') and update.get('aktueller_eindruck'):
            eindruck['erster_eindruck'] = update['aktueller_eindruck']
        if update.get('aktueller_eindruck'):
            eindruck['aktueller_eindruck'] = update['aktueller_eindruck']

        # Emotionale Bewertung mit Deltas anpassen
        bewertung = current_map.setdefault('emotionale_bewertung', {})
        for key in ['vertrauen', 'naehe', 'respekt', 'faszination']:
            delta = update.get(f'{key}_delta', 0)
            if isinstance(delta, (int, float)):
                current = bewertung.get(key, 0.5)
                bewertung[key] = round(max(0.0, min(1.0, current + delta)), 2)

        # Neue Beobachtung anhaengen
        beobachtung = update.get('neue_beobachtung', '')
        if beobachtung:
            gelernt = current_map.setdefault('was_ich_gelernt_habe', [])
            gelernt.append(beobachtung)
            # Max 20 Beobachtungen behalten
            if len(gelernt) > 20:
                current_map['was_ich_gelernt_habe'] = gelernt[-20:]

        # Interaktionszaehler erhoehen
        ident = current_map.setdefault('identitaet', {})
        ident['interaktionen_gesamt'] = ident.get('interaktionen_gesamt', 0) + 1
        if not ident.get('kennt_seit'):
            ident['kennt_seit'] = datetime.now().strftime('%Y-%m-%d')

        # Schreiben
        write_social_map(egon_id, about_id, current_map)
        print(f'[social_mapping] {egon_id} ueber {about_id}: Map aktualisiert')

        return current_map

    except Exception as e:
        print(f'[social_mapping] Update error ({egon_id} -> {about_id}): {e}')
        return current_map


def get_all_social_maps(egon_id: str) -> dict[str, dict]:
    """Liest alle Social Maps eines EGONs. Returns dict keyed by about_id."""
    map_dir = _social_map_dir(egon_id)
    if not map_dir.exists():
        return {}

    maps = {}
    for f in map_dir.iterdir():
        if f.suffix == '.yaml' and f.stem.startswith('ueber_'):
            about_id = f.stem[6:]  # "ueber_adam_001" → "adam_001"
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    data = yaml.safe_load(fh)
                if data and isinstance(data, dict):
                    maps[about_id] = data
            except Exception:
                continue

    return maps


def social_maps_to_prompt(egon_id: str, max_maps: int = 3) -> str:
    """Formatiert Social Maps als natuerliche Sprache fuer den System-Prompt.

    Sortiert nach Aktualitaet (Interaktionszahl) und gibt die Top N zurueck.
    """
    maps = get_all_social_maps(egon_id)
    if not maps:
        return ''

    # Sortiere nach Interaktionszahl (absteigend)
    sorted_maps = sorted(
        maps.items(),
        key=lambda x: x[1].get('identitaet', {}).get('interaktionen_gesamt', 0),
        reverse=True,
    )

    lines = []
    for about_id, data in sorted_maps[:max_maps]:
        name = data.get('identitaet', {}).get('name', about_id)
        eindruck = data.get('mein_eindruck', {}).get('aktueller_eindruck', 'Noch kein Eindruck')
        bewertung = data.get('emotionale_bewertung', {})
        vertrauen = bewertung.get('vertrauen', 0.5)
        naehe = bewertung.get('naehe', 0.3)
        respekt = bewertung.get('respekt', 0.5)

        lines.append(
            f'Ueber {name}: {eindruck} '
            f'(Vertrauen: {vertrauen:.1f}, Naehe: {naehe:.1f}, Respekt: {respekt:.1f})'
        )

    return '\n'.join(lines)
