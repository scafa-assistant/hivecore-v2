"""Action Detector — erkennt Handy-Aktionen aus User-Nachrichten.

Wie Siri/Google Assistant: Intent-Erkennung per Pattern-Matching.
100% zuverlaessig — kein LLM noetig.

Fallback wenn das LLM keinen ###ACTION### Block generiert.
"""

import re
from typing import Optional


def detect_action(message: str) -> Optional[dict]:
    """Erkennt Aktionen aus User-Nachrichten via Regex.

    Returns:
        {"action": "...", "params": {...}} oder None
    """
    msg = message.strip()
    msg_lower = msg.lower()

    # ─── MAKE_CALL ───────────────────────────
    action = _detect_call(msg, msg_lower)
    if action:
        return action

    # ─── SEND_SMS ────────────────────────────
    action = _detect_sms(msg, msg_lower)
    if action:
        return action

    # ─── SEND_EMAIL ──────────────────────────
    action = _detect_email(msg, msg_lower)
    if action:
        return action

    # ─── SET_ALARM ───────────────────────────
    action = _detect_alarm(msg_lower)
    if action:
        return action

    # ─── SET_TIMER ───────────────────────────
    action = _detect_timer(msg_lower)
    if action:
        return action

    # ─── OPEN_MAPS ───────────────────────────
    action = _detect_maps(msg, msg_lower)
    if action:
        return action

    # ─── TAKE_PHOTO ──────────────────────────
    if re.search(r'\b(foto|photo|kamera|camera|selfie|bild mach|mach.+bild|mach.+foto)\b', msg_lower):
        return {'action': 'take_photo', 'params': {}}

    # ─── OPEN_SETTINGS ───────────────────────
    if re.search(r'\b(einstellungen|settings)\s*(oeffnen|offnen|öffnen|auf)?\b', msg_lower):
        return {'action': 'open_settings', 'params': {}}

    return None


# ================================================================
# Einzelne Detektoren
# ================================================================

def _detect_call(msg: str, msg_lower: str) -> Optional[dict]:
    """Erkennt Anruf-Intent.

    Patterns:
    - "ruf Ron an"
    - "ruf mal Ron an"
    - "ruf bitte Ron an"
    - "rufe Ron an"
    - "Ron anrufen"
    - "ruf die 0175... an"
    - "ruf ihn an" (→ kein contact_name, App muss aus Kontext entscheiden)
    """
    # Pattern 1: "ruf [filler] TARGET an"
    m = re.search(
        r'\b(?:ruf|rufe?)\s+(?:mal\s+|bitte\s+|doch\s+)*(.+?)\s+an\b',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        return _make_call_from_target(target, msg)

    # Pattern 2: "TARGET anrufen"
    m = re.search(
        r'^(?:bitte\s+|kannst\s+du\s+|k[oö]nntest\s+du\s+)?(.+?)\s+anrufen',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        return _make_call_from_target(target, msg)

    # Pattern 3: "ruf an bei TARGET" / "ruf bei TARGET an"
    m = re.search(
        r'\b(?:ruf|rufe?)\s+(?:mal\s+)?(?:an\s+)?bei\s+(.+?)(?:\s+an)?\s*$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        return _make_call_from_target(target, msg)

    # Pattern 4: "anruf TARGET" / "anruf bei TARGET"
    m = re.search(
        r'\banruf\s+(?:bei\s+)?(.+?)$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        return _make_call_from_target(target, msg)

    return None


def _detect_sms(msg: str, msg_lower: str) -> Optional[dict]:
    """Erkennt SMS-Intent.

    Patterns:
    - "schick Mama ne SMS: bin gleich da"
    - "schreib Ron eine SMS bin unterwegs"
    - "sms an Ron: text here"
    - "send Ron eine nachricht: text"
    """
    # Pattern 1: "schick/sende/schreib TARGET ne/eine SMS: BODY"
    m = re.search(
        r'\b(?:schick|sende?|schreib)\s+(?:mal\s+)?(.+?)\s+(?:ne\s+|eine?\s+)?(?:sms|nachricht|message|textnachricht)\s*[:\-]?\s*(.*)$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        body = m.group(2).strip()
        name = _clean_name(target, msg)
        return {'action': 'send_sms', 'params': {'contact_name': name, 'body': body}}

    # Pattern 2: "sms an TARGET: BODY"
    m = re.search(
        r'\bsms\s+an\s+(.+?)\s*[:\-]\s*(.+)$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        body = m.group(2).strip()
        name = _clean_name(target, msg)
        return {'action': 'send_sms', 'params': {'contact_name': name, 'body': body}}

    # Pattern 3: "sms an TARGET BODY" (ohne Doppelpunkt)
    m = re.search(
        r'\bsms\s+an\s+(\w+)\s+(.+)$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        body = m.group(2).strip()
        name = _clean_name(target, msg)
        return {'action': 'send_sms', 'params': {'contact_name': name, 'body': body}}

    return None


def _detect_email(msg: str, msg_lower: str) -> Optional[dict]:
    """Erkennt E-Mail-Intent.

    Patterns:
    - "schick Ron eine email: Betreff hier"
    - "email an Ron: text"
    - "mail an mama schick ihr das"
    """
    m = re.search(
        r'\b(?:schick|sende?|schreib)\s+(?:mal\s+)?(.+?)\s+(?:ne\s+|eine?\s+)?(?:e-?mail|mail)\s*[:\-]?\s*(.*)$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        body = m.group(2).strip()
        name = _clean_name(target, msg)
        return {'action': 'send_email', 'params': {'contact_name': name, 'body': body}}

    m = re.search(
        r'\b(?:e-?mail|mail)\s+an\s+(.+?)\s*[:\-]\s*(.+)$',
        msg_lower,
    )
    if m:
        target = m.group(1).strip()
        body = m.group(2).strip()
        name = _clean_name(target, msg)
        return {'action': 'send_email', 'params': {'contact_name': name, 'body': body}}

    return None


def _detect_alarm(msg_lower: str) -> Optional[dict]:
    """Erkennt Wecker-Intent.

    Patterns:
    - "stell einen wecker auf 7"
    - "wecker auf 7:30"
    - "weck mich um 6"
    - "alarm auf 8 uhr"
    """
    m = re.search(
        r'(?:stell|setz|mach)\s+(?:mir\s+)?(?:einen?\s+)?(?:wecker|alarm)\s+(?:auf|um|f[uü]r)\s+(\d{1,2})(?::(\d{2}))?\s*(?:uhr)?',
        msg_lower,
    )
    if m:
        return {'action': 'set_alarm', 'params': {
            'hour': int(m.group(1)),
            'minute': int(m.group(2) or 0),
        }}

    m = re.search(
        r'(?:wecker|alarm)\s+(?:auf|um|f[uü]r)\s+(\d{1,2})(?::(\d{2}))?\s*(?:uhr)?',
        msg_lower,
    )
    if m:
        return {'action': 'set_alarm', 'params': {
            'hour': int(m.group(1)),
            'minute': int(m.group(2) or 0),
        }}

    m = re.search(
        r'weck\s+mich\s+(?:um|auf)\s+(\d{1,2})(?::(\d{2}))?\s*(?:uhr)?',
        msg_lower,
    )
    if m:
        return {'action': 'set_alarm', 'params': {
            'hour': int(m.group(1)),
            'minute': int(m.group(2) or 0),
        }}

    return None


def _detect_timer(msg_lower: str) -> Optional[dict]:
    """Erkennt Timer-Intent.

    Patterns:
    - "timer auf 5 minuten"
    - "stell einen timer auf 30 sekunden"
    - "timer 10 min"
    """
    m = re.search(
        r'timer\s+(?:auf\s+|von\s+|f[uü]r\s+)?(\d+)\s*(?:min(?:uten?)?|m\b)',
        msg_lower,
    )
    if m:
        return {'action': 'set_timer', 'params': {'seconds': int(m.group(1)) * 60}}

    m = re.search(
        r'timer\s+(?:auf\s+|von\s+|f[uü]r\s+)?(\d+)\s*(?:sek(?:unden?)?|s\b|sec)',
        msg_lower,
    )
    if m:
        return {'action': 'set_timer', 'params': {'seconds': int(m.group(1))}}

    m = re.search(
        r'(?:stell|setz|mach)\s+(?:einen?\s+)?timer\s+(?:auf\s+|von\s+|f[uü]r\s+)?(\d+)\s*(?:min(?:uten?)?|m\b)',
        msg_lower,
    )
    if m:
        return {'action': 'set_timer', 'params': {'seconds': int(m.group(1)) * 60}}

    return None


def _detect_maps(msg: str, msg_lower: str) -> Optional[dict]:
    """Erkennt Navigations-Intent.

    Patterns:
    - "navigiere zu Rewe"
    - "zeig mir den weg zum Bahnhof"
    - "route nach Berlin"
    """
    m = re.search(
        r'\b(?:navigier\w*|navigation|zeig.*weg|route|fahr.*zu|bring.*mich.*zu)\s+(?:zu[mr]?\s+|nach\s+)?(.+?)$',
        msg_lower,
    )
    if m:
        query = m.group(1).strip()
        if len(query) > 1:
            # Original-Gross-/Kleinschreibung aus msg extrahieren
            return {'action': 'open_maps', 'params': {'query': query}}

    return None


# ================================================================
# Hilfsfunktionen
# ================================================================

def _make_call_from_target(target_lower: str, original_msg: str) -> dict:
    """Erstellt make_call Action aus dem erkannten Target.

    Unterscheidet Telefonnummer vs. Kontaktname.
    """
    # Filler-Woerter entfernen
    cleaned = re.sub(r'^(den|die|das|dem|der|bitte|mal|doch|n|ihn|sie)\s+', '', target_lower)
    cleaned = re.sub(r'\s+(bitte|mal|doch)$', '', cleaned)
    cleaned = cleaned.strip()

    # Pronomen → leerer call (App muss entscheiden)
    if cleaned in ('ihn', 'sie', 'n', 'ihm', 'ihr', ''):
        # Kein konkreter Name — Fallback, App zeigt Dialer
        return {'action': 'make_call', 'params': {}}

    # Telefonnummer erkennen (Ziffern, Leerzeichen, +, -, /)
    if re.match(r'^[\d\s\+\-\/\(\)]{4,}$', cleaned):
        number = re.sub(r'[\s\-\/\(\)]', '', cleaned)
        return {'action': 'make_call', 'params': {'number': number}}

    # Kontaktname — Grossschreibung wiederherstellen
    name = _clean_name(cleaned, original_msg)
    return {'action': 'make_call', 'params': {'contact_name': name}}


def _clean_name(name_lower: str, original_msg: str) -> str:
    """Bereinigt den Namen und stellt Grossschreibung wieder her.

    Versucht die originale Schreibweise aus der Nachricht zu finden.
    Fallback: Title-Case.
    """
    # Filler entfernen
    cleaned = re.sub(r'^(den|die|das|dem|der|bitte|mal|doch)\s+', '', name_lower)
    cleaned = re.sub(r'\s+(bitte|mal|doch)$', '', cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        return ''

    # Versuche Original-Schreibweise im Original-Text zu finden
    pattern = re.compile(re.escape(cleaned), re.IGNORECASE)
    m = pattern.search(original_msg)
    if m:
        return m.group(0).strip()

    # Fallback: Title-Case
    return ' '.join(word.capitalize() for word in cleaned.split())
