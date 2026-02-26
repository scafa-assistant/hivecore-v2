"""Lobby System — Shared Blackboard fuer Inter-EGON Kommunikation.

Alle EGONs koennen lesen und schreiben.
Owner koennen mitlesen aber NICHT schreiben.
Max 5 Lobby-Nachrichten pro zirkadianer Phase.

Datei: egons/shared/lobby_chat.yaml

Wissenschaftliche Basis: GNWT (Baars 1988, Dehaene 2014).
"""

from datetime import datetime
from pathlib import Path

import yaml

from config import EGON_DATA_DIR


# ================================================================
# File I/O
# ================================================================

def _lobby_path() -> Path:
    return Path(EGON_DATA_DIR) / 'shared' / 'lobby_chat.yaml'


def _read_lobby_data() -> dict:
    """Liest die Lobby-Datei. Erstellt Default wenn nicht vorhanden."""
    path = _lobby_path()
    if not path.exists():
        return {'messages': [], 'meta': {'created': datetime.now().strftime('%Y-%m-%d'), 'last_message': None}}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return {'messages': [], 'meta': {'created': datetime.now().strftime('%Y-%m-%d'), 'last_message': None}}
        if 'messages' not in data:
            data['messages'] = []
        return data
    except Exception:
        return {'messages': [], 'meta': {'created': datetime.now().strftime('%Y-%m-%d'), 'last_message': None}}


def _write_lobby_data(data: dict) -> None:
    """Schreibt die Lobby-Datei."""
    path = _lobby_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _next_lobby_id(data: dict) -> str:
    """Generiert die naechste Lobby-Message-ID (L001, L002, ...)."""
    messages = data.get('messages', [])
    if not messages:
        return 'L001'
    ids = []
    for m in messages:
        mid = m.get('id', '')
        if isinstance(mid, str) and mid.startswith('L') and mid[1:].isdigit():
            ids.append(int(mid[1:]))
    next_num = max(ids) + 1 if ids else 1
    return f'L{next_num:03d}'


MAX_LOBBY_MESSAGES = 100
MAX_PER_PHASE = 5


# ================================================================
# Public API
# ================================================================

def read_lobby(max_messages: int = 20) -> list[dict]:
    """Liest die letzten N Lobby-Nachrichten.

    Returns: Liste von dicts mit id, from, name, timestamp, message, emotional_context.
    """
    data = _read_lobby_data()
    messages = data.get('messages', [])
    return messages[-max_messages:]


def write_lobby(egon_id: str, message: str, emotional_context: str = '') -> dict | None:
    """Schreibt eine Nachricht in die Lobby.

    Prueft Rate-Limit: Max 5 Nachrichten pro Phase.
    Returns: geschriebene Nachricht oder None wenn Limit erreicht.
    """
    count = get_lobby_count_this_phase(egon_id)
    if count >= MAX_PER_PHASE:
        print(f'[lobby] {egon_id}: Limit erreicht ({count}/{MAX_PER_PHASE} diese Phase)')
        return None

    data = _read_lobby_data()

    # EGON-Name aus ID ableiten
    egon_name = egon_id.replace('_', ' ').split()[0].capitalize()

    msg = {
        'id': _next_lobby_id(data),
        'timestamp': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'from': egon_id,
        'name': egon_name,
        'message': message,
        'emotional_context': emotional_context,
    }

    data['messages'].append(msg)
    data.setdefault('meta', {})['last_message'] = msg['timestamp']

    # Trim: nur letzte N Nachrichten behalten
    if len(data['messages']) > MAX_LOBBY_MESSAGES:
        data['messages'] = data['messages'][-MAX_LOBBY_MESSAGES:]

    _write_lobby_data(data)
    print(f'[lobby] {egon_id}: "{message[:50]}..." ({msg["id"]})')
    return msg


def get_lobby_count_this_phase(egon_id: str) -> int:
    """Zaehlt Nachrichten von egon_id in der aktuellen Phase.

    Nutzt den Phasenbeginn-Timestamp aus dem Circadian Block.
    Fallback: letzte 8 Stunden.
    """
    from engine.organ_reader import read_yaml_organ

    # Phase-Beginn bestimmen
    phase_start = None
    try:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        if state:
            zirkadian = state.get('zirkadian', {})
            beginn_str = zirkadian.get('phase_beginn')
            if beginn_str:
                phase_start = datetime.fromisoformat(str(beginn_str))
    except Exception:
        pass

    if not phase_start:
        # Fallback: letzte 8 Stunden
        from datetime import timedelta
        phase_start = datetime.now() - timedelta(hours=8)

    # Nachrichten zaehlen
    data = _read_lobby_data()
    count = 0
    for msg in data.get('messages', []):
        if msg.get('from') != egon_id:
            continue
        try:
            ts = datetime.fromisoformat(str(msg.get('timestamp', '')))
            if ts >= phase_start:
                count += 1
        except (ValueError, TypeError):
            continue

    return count


def get_active_lobby_participants(
    max_messages: int = 10,
    exclude_id: str | None = None,
) -> list[str]:
    """Gibt EGON-IDs zurueck die kuerzlich in der Lobby geschrieben haben.

    Sortiert nach Aktualitaet (neueste zuerst).
    Nutzt die letzten max_messages Nachrichten.
    """
    messages = read_lobby(max_messages)
    participants: list[str] = []
    seen: set[str] = set()
    for msg in reversed(messages):
        from_id = msg.get('from', '')
        if from_id and from_id not in seen and from_id != exclude_id:
            participants.append(from_id)
            seen.add(from_id)
    return participants


def lobby_to_prompt(max_messages: int = 5) -> str:
    """Formatiert Lobby-Nachrichten als natuerliche Sprache fuer den System-Prompt."""
    messages = read_lobby(max_messages)
    if not messages:
        return ''

    lines = []
    for msg in messages:
        name = msg.get('name', msg.get('from', '?'))
        text = msg.get('message', '')
        ts = msg.get('timestamp', '')
        # Nur Zeit extrahieren
        try:
            dt = datetime.fromisoformat(str(ts))
            time_str = dt.strftime('%H:%M')
        except (ValueError, TypeError):
            time_str = '?'
        lines.append(f'[{time_str}] {name}: {text}')

    return '\n'.join(lines)
