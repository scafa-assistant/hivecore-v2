"""Response Parser — trennt Text, ###BODY### und ###ACTION### Bloecke.

LLM-Antworten koennen bis zu zwei strukturierte Bloecke enthalten:
  ###BODY###{"words": [...], "intensity": 0.7, "reason": "..."}###END_BODY###
  ###ACTION###{"action": "...", "params": {...}}###END_ACTION###

Dieser Parser extrahiert beide unabhaengig und liefert sauberen Display-Text.
"""

import json
import re
from typing import Optional


def parse_body(text: str) -> tuple[str, Optional[dict]]:
    """Extrahiert ###BODY### Block aus LLM-Antwort.

    Returns:
        (display_text, body_dict_or_None)

    body_dict Format:
        {"words": ["nicken", "gewicht_links"], "intensity": 0.5, "reason": "..."}

    Robustheit:
    - Wenn ###END_BODY### fehlt, wird trotzdem geparst
    - Wenn JSON unvollstaendig ist, wird es entfernt statt angezeigt
    - Alles ab ###BODY### wird IMMER aus dem display_text entfernt
    """
    body = None
    display_text = text

    if '###BODY###' in text:
        try:
            parts = text.split('###BODY###')
            display_text = parts[0].strip()

            # Alles nach ###BODY### ist Body-Daten — NIEMALS anzeigen
            raw_body = parts[1] if len(parts) > 1 else ''

            # ###END_BODY### vorhanden?
            if '###END_BODY###' in raw_body:
                body_json = raw_body.split('###END_BODY###')[0].strip()
                # Rest nach ###END_BODY### pruefen (koennte ###ACTION### sein)
                after_body = raw_body.split('###END_BODY###')
                if len(after_body) > 1:
                    remainder = after_body[1].strip()
                    # Nur ###ACTION### Bloecke zurueck an display_text
                    if remainder and '###ACTION###' in remainder:
                        display_text = display_text + '\n' + remainder
            else:
                # ###END_BODY### fehlt — ganzen Rest als Body-JSON versuchen
                body_json = raw_body.strip()
                print(f'[parser] WARNUNG: ###END_BODY### fehlt, versuche trotzdem zu parsen')

            # JSON parsen
            body = json.loads(body_json)

            # Validierung: words (Liste) ODER bones (Dict) muss vorhanden sein
            has_words = isinstance(body.get('words'), list)
            has_bones = isinstance(body.get('bones'), dict)
            if not has_words and not has_bones:
                body = None
            else:
                body.setdefault('intensity', 0.5)
                body.setdefault('reason', '')

        except (IndexError, json.JSONDecodeError) as e:
            print(f'[parser] BODY parse error: {e}')
            # Alles ab ###BODY### entfernen — NIEMALS rohen JSON anzeigen
            display_text = text.split('###BODY###')[0].strip()
            # Auch ###END_BODY### Reste entfernen
            display_text = display_text.replace('###END_BODY###', '').strip()
            body = None

    # Sicherheitsnetz: JSON-Fragmente die durchgerutscht sind entfernen
    # z.B. {"words": ["arme_vers  (abgeschnitten)
    if display_text and display_text.rstrip().endswith(('{', '["', '"words"')):
        # Abgeschnittenes JSON am Ende — entfernen
        for marker in ['{"words"', '{"word', '{']:
            idx = display_text.rfind(marker)
            if idx > 0 and idx > len(display_text) - 100:
                display_text = display_text[:idx].strip()
                break

    return display_text, body


def parse_action(text: str) -> tuple[str, Optional[dict]]:
    """Extrahiert ###ACTION### Block aus LLM-Antwort.

    Returns:
        (display_text, action_dict_or_None)
    """
    action = None
    display_text = text

    if '###ACTION###' in text:
        try:
            parts = text.split('###ACTION###')
            display_text = parts[0].strip()
            action_json = parts[1].split('###END_ACTION###')[0].strip()
            action = json.loads(action_json)
        except (IndexError, json.JSONDecodeError):
            display_text = text.replace('###ACTION###', '').replace('###END_ACTION###', '').strip()
            action = None

    return display_text, action


def parse_response(text: str) -> dict:
    """Parst eine komplette LLM-Antwort — extrahiert Body + Action.

    Returns:
        {
            "display_text": "Sauberer Text ohne Bloecke",
            "body": {"words": [...], "intensity": 0.7, "reason": "..."} oder None,
            "action": {"action": "...", "params": {...}} oder None,
        }
    """
    # 1. Body extrahieren (entfernt ###BODY###...###END_BODY###)
    text_after_body, body = parse_body(text)

    # 2. Action extrahieren (entfernt ###ACTION###...###END_ACTION###)
    display_text, action = parse_action(text_after_body)

    return {
        'display_text': display_text,
        'body': body,
        'action': action,
    }
