"""Formatting Preference Detector.

Erkennt und speichert Formatierungs-Wuensche des Owners.
Z.B. "keine Sternchen", "schreib normal", "kein Markdown".

Wird nach jedem Chat getriggert (wie owner_portrait.py).
Praeferenzen werden in settings.yaml persistiert und im
System-Prompt als Regel injiziert.
"""

import re
from engine.settings import read_settings, update_settings


# ================================================================
# Patterns die auf Formatierungs-Praeferenzen hindeuten
# (regex_pattern, dict_mit_praeferenzen)
# ================================================================

FORMAT_PATTERNS = [
    (r'keine?\s+sternchen', {'use_bold_italic': False}),
    (r'kein\s+markdown', {'use_markdown': False}),
    (r'kein(e)?\s+emojis?', {'use_emojis': False}),
    (r'schreib\s+normal', {'use_markdown': False, 'use_bold_italic': False}),
    (r'ohne\s+formatierung', {'use_markdown': False, 'use_bold_italic': False}),
    (r'nicht\s+fett\s+schreiben', {'use_bold_italic': False}),
    (r'kein(e)?\s+aufzaehlungen', {'use_markdown': False}),
    (r'benutz(e)?\s+emojis?', {'use_emojis': True}),
    (r'mit\s+markdown', {'use_markdown': True}),
    (r'mit\s+formatierung', {'use_markdown': True, 'use_bold_italic': True}),
    (r'darfst\s+sternchen', {'use_bold_italic': True}),
]


def detect_formatting_preference(user_message: str) -> dict | None:
    """Prueft ob die Nachricht eine Formatierungs-Praeferenz enthaelt.

    Returns:
        Dict mit Praeferenzen (z.B. {'use_bold_italic': False}) oder None.
    """
    msg_lower = user_message.lower()
    for pattern, prefs in FORMAT_PATTERNS:
        if re.search(pattern, msg_lower):
            return prefs
    return None


async def maybe_update_formatting(egon_id: str, user_message: str) -> bool:
    """Prueft und speichert Formatierungs-Praeferenzen.

    Wird nach jedem Chat aufgerufen. Erkennt Muster wie
    "keine Sternchen" und speichert die Praeferenz persistent
    in settings.yaml.

    Returns:
        True wenn etwas aktualisiert wurde.
    """
    prefs = detect_formatting_preference(user_message)
    if not prefs:
        return False

    # Aktuelle Settings laden
    current = read_settings(egon_id)
    formatting = current.get('formatting', {})

    # Neue Praeferenzen mergen
    formatting.update(prefs)

    # Original-Nachricht als custom_rule speichern (fuer komplexere Wuensche)
    custom_rules = formatting.get('custom_rules', [])
    rule_text = user_message.strip()[:100]
    # Nicht doppelt speichern
    if rule_text not in custom_rules:
        custom_rules.append(rule_text)
        # Max 5 custom rules behalten
        if len(custom_rules) > 5:
            custom_rules = custom_rules[-5:]
    formatting['custom_rules'] = custom_rules

    update_settings(egon_id, {'formatting': formatting})
    return True
