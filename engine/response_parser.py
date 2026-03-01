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
    """
    body = None
    display_text = text

    if '###BODY###' in text:
        try:
            parts = text.split('###BODY###')
            display_text = parts[0].strip()
            body_json = parts[1].split('###END_BODY###')[0].strip()
            body = json.loads(body_json)

            # Validierung: words (Liste) ODER bones (Dict) muss vorhanden sein
            has_words = isinstance(body.get('words'), list)
            has_bones = isinstance(body.get('bones'), dict)
            if not has_words and not has_bones:
                body = None
            else:
                # Defaults setzen
                body.setdefault('intensity', 0.5)
                body.setdefault('reason', '')

                # Rest nach ###END_BODY### zurueck an display_text haengen
                # (falls noch ###ACTION### oder anderer Text folgt)
                after_body = parts[1].split('###END_BODY###')
                if len(after_body) > 1:
                    remainder = after_body[1].strip()
                    if remainder:
                        display_text = display_text + '\n' + remainder

        except (IndexError, json.JSONDecodeError):
            # Parsing fehlgeschlagen — Text bereinigen, kein Body
            display_text = text.replace('###BODY###', '').replace('###END_BODY###', '').strip()
            body = None

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
