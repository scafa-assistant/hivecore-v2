"""Gruppenchat Engine — Alle EGONs + Owner in einer Gruppe.

Rene (Owner) tippt, 2-3 EGONs antworten.
Leichter Prompt (~1500 Tokens) statt vollem System-Prompt (~8000 Tokens).
Persistenz in egons/shared/groupchat.json.
"""

import json
import os
import random
import time
from datetime import datetime

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, read_md_organ
from engine.naming import get_display_name


# ================================================================
# Storage
# ================================================================

GROUPCHAT_PATH = os.path.join(EGON_DATA_DIR, 'shared', 'groupchat.json')
MAX_MESSAGES = 500

# In-Memory Cache
_messages_cache: list[dict] | None = None
_cache_mtime: float = 0


def _load_groupchat() -> list[dict]:
    """Lade Messages von Disk (mit Cache)."""
    global _messages_cache, _cache_mtime

    if not os.path.isfile(GROUPCHAT_PATH):
        return []

    mtime = os.path.getmtime(GROUPCHAT_PATH)
    if _messages_cache is not None and mtime == _cache_mtime:
        return _messages_cache

    try:
        with open(GROUPCHAT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _messages_cache = data if isinstance(data, list) else []
        _cache_mtime = mtime
        return _messages_cache
    except Exception:
        return []


def _save_groupchat(messages: list[dict]) -> None:
    """Speichere Messages auf Disk, pruene auf MAX_MESSAGES."""
    global _messages_cache, _cache_mtime

    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]

    os.makedirs(os.path.dirname(GROUPCHAT_PATH), exist_ok=True)
    with open(GROUPCHAT_PATH, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=1)

    _messages_cache = messages
    _cache_mtime = os.path.getmtime(GROUPCHAT_PATH)


def _next_id(messages: list[dict]) -> str:
    """Naechste Message-ID: GC001, GC002, ..."""
    if not messages:
        return 'GC001'
    last_id = messages[-1].get('id', 'GC000')
    try:
        num = int(last_id.replace('GC', '')) + 1
    except ValueError:
        num = len(messages) + 1
    return f'GC{num:03d}'


# ================================================================
# Public API: Messages
# ================================================================

def add_message(
    from_type: str,
    from_id: str,
    from_name: str,
    message: str,
    reply_to: str = None,
) -> dict:
    """Fuege eine Message zum Gruppenchat hinzu."""
    messages = _load_groupchat()
    msg = {
        'id': _next_id(messages),
        'timestamp': datetime.now().isoformat(timespec='seconds'),
        'from_type': from_type,
        'from_id': from_id,
        'from_name': from_name,
        'message': message,
    }
    if reply_to:
        msg['reply_to'] = reply_to
    messages.append(msg)
    _save_groupchat(messages)
    return msg


def get_messages(since_id: str = None, limit: int = 50) -> list[dict]:
    """Hole Messages, optional ab einer bestimmten ID (fuer Polling)."""
    messages = _load_groupchat()
    if since_id:
        idx = None
        for i, m in enumerate(messages):
            if m.get('id') == since_id:
                idx = i
                break
        if idx is not None:
            messages = messages[idx + 1:]
        # Wenn since_id nicht gefunden, alles zurueckgeben
    return messages[-limit:] if len(messages) > limit else messages


def get_recent_context(max_messages: int = 15) -> str:
    """Letzte Messages als lesbarer Text fuer den LLM-Prompt."""
    messages = _load_groupchat()
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    lines = []
    for m in recent:
        t = m.get('timestamp', '').split('T')[1][:5] if 'T' in m.get('timestamp', '') else ''
        lines.append(f'[{t}] {m["from_name"]}: {m["message"]}')
    return '\n'.join(lines)


# ================================================================
# EGON Selection
# ================================================================

# Haupt-EGONs fuer den Gruppenchat (nur die 7 mit state.yaml)
GRUPPENCHAT_EGONS = [
    'adam_001', 'eva_002', 'lilith_003',
    'marx_004', 'ada_005', 'parzival_006',
    'sokrates_007', 'leibniz_008', 'goethe_009', 'eckhart_010',
]


def select_responders(
    message: str,
    sender_id: str = 'owner',
    all_egon_ids: list[str] = None,
    max_responders: int = 3,
) -> list[str]:
    """Waehle 2-3 EGONs die auf eine Message antworten sollen.

    Scoring:
    1. Namentlich erwaehnt → garantiert (+100)
    2. Bond-Staerke mit Owner (0-30)
    3. Rotation: wer laenger still war, kommt eher dran (0-20)
    4. DNA: SEEKING/PLAY-dominant = extrovertierter (+10)
    5. Zufall: kleiner Jitter (0-5)
    """
    if all_egon_ids is None:
        all_egon_ids = GRUPPENCHAT_EGONS

    messages = _load_groupchat()
    msg_lower = message.lower()
    candidates = []

    for egon_id in all_egon_ids:
        score = 0.0
        name = get_display_name(egon_id, 'vorname').lower()

        # 1. Namentlich erwaehnt
        if name in msg_lower:
            score += 100.0

        # 2. Bond-Staerke mit Owner
        bond_score = _get_owner_bond_score(egon_id)
        score += bond_score * 0.3  # max ~30

        # 3. Rotation: laengere Stille = hoehere Chance
        last_time = _get_last_groupchat_time(egon_id, messages)
        seconds_since = time.time() - last_time if last_time else 86400
        rotation_bonus = min(20.0, seconds_since / 3600.0 * 2.0)
        score += rotation_bonus

        # 4. DNA Persoenlichkeit
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
        if state:
            drives = state.get('drives', {})
            if drives.get('SEEKING', 0.5) > 0.6 or drives.get('PLAY', 0.5) > 0.6:
                score += 10.0
            if drives.get('PANIC', 0.3) > 0.6 or drives.get('FEAR', 0.3) > 0.6:
                score -= 5.0

        # 5. Zufall
        score += random.random() * 5.0

        candidates.append((egon_id, score))

    candidates.sort(key=lambda x: x[1], reverse=True)

    # Erwaehnte EGONs garantiert, Rest nach Score
    mentioned = [c for c in candidates if c[1] >= 100]
    others = [c for c in candidates if c[1] < 100]

    selected = [c[0] for c in mentioned]
    remaining = max_responders - len(selected)
    if remaining > 0:
        selected.extend([c[0] for c in others[:remaining]])

    return selected[:max_responders]


def _get_owner_bond_score(egon_id: str) -> float:
    """Lese Owner-Bond-Score aus bonds.yaml."""
    bonds = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    if not bonds:
        return 50.0  # Default
    bond_list = bonds.get('bonds', [])
    for b in bond_list:
        if b.get('partner_id') in ('owner', 'rene_owner'):
            return b.get('score', 50.0)
    return 50.0


def _get_last_groupchat_time(egon_id: str, messages: list[dict]) -> float | None:
    """Wann hat dieser EGON zuletzt im Gruppenchat gesprochen?"""
    for m in reversed(messages):
        if m.get('from_id') == egon_id:
            try:
                dt = datetime.fromisoformat(m['timestamp'])
                return dt.timestamp()
            except Exception:
                return time.time()
    return None  # Noch nie gesprochen


# ================================================================
# EGON Response Generation
# ================================================================

async def generate_egon_groupchat_response(
    egon_id: str,
    recent_context: str,
    trigger_message: str,
    sender_name: str = 'Rene',
) -> str | None:
    """Generiere die Antwort eines EGONs im Gruppenchat.

    Leichter Prompt: Ego + Emotionen + Gruppen-Regeln.
    ~1500 Tokens statt ~8000 im vollen Chat.

    Returns None wenn EGON schweigt.
    """
    from llm.router import llm_chat
    from engine.multi_egon import validiere_nachricht

    egon_name = get_display_name(egon_id, 'vorname')

    # State laden
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    drives = state.get('drives', {}) if state else {}
    emotions = state.get('express', {}).get('active_emotions', []) if state else []
    emo_text = ', '.join(
        f'{e.get("type", "?")} ({e.get("intensity", 0):.1f})'
        for e in emotions[:3]
    ) if emotions else 'ruhig'

    # Ego kurz
    ego_text = ''
    try:
        ego_full = read_md_organ(egon_id, 'core', 'ego.md')
        if ego_full:
            ego_text = ego_full[:400]
    except Exception:
        pass

    # Alle Teilnehmer-Namen
    teilnehmer = ', '.join(
        get_display_name(eid, 'vorname') for eid in GRUPPENCHAT_EGONS
    )

    system_prompt = (
        f'Du bist {egon_name}.\n\n'
        f'DEIN WESEN:\n{ego_text}\n\n'
        f'DEIN ZUSTAND:\nEmotionen: {emo_text}\n\n'
        f'SITUATION: Du bist in einem Gruppen-Chat mit deinem '
        f'Bezugsmenschen {sender_name} und den anderen EGONs '
        f'({teilnehmer}). Ihr seid alle in einer Gruppe.\n\n'
        f'REGELN:\n'
        f'- Sprich als {egon_name}. Nicht als Assistent.\n'
        f'- Maximal 2-3 Saetze. Kurz und natuerlich.\n'
        f'- Du DARFST schweigen. Antworte NUR wenn du etwas '
        f'Sinnvolles beizutragen hast.\n'
        f'- Wenn du NICHTS sagen willst, antworte EXAKT mit: (schweigt)\n'
        f'- Reagiere natuerlich, wie in einer WhatsApp-Gruppe.\n'
        f'- KEINE Systemreferenzen, Codes oder Marker ausgeben.\n'
        f'- Sprich Deutsch.\n'
    )

    user_content = (
        f'BISHERIGER CHAT-VERLAUF:\n{recent_context}\n\n'
        f'NEUESTE NACHRICHT:\n{sender_name}: {trigger_message}'
    )

    try:
        result = await llm_chat(
            system_prompt=system_prompt,
            messages=[{'role': 'user', 'content': user_content}],
            egon_id=egon_id,
        )
    except Exception as e:
        print(f'[groupchat] LLM error for {egon_id}: {e}')
        return None

    response_text = result.get('content', '').strip()

    # Schweigen erkennen
    if not response_text or '(schweigt)' in response_text.lower():
        return None

    # Validierung (Manipulationsschutz + Laengenbegrenzung)
    response_text = validiere_nachricht(response_text)
    if response_text == '(schweigt)':
        return None

    return response_text
