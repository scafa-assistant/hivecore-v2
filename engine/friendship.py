"""Friendship Engine — Verwaltet EGON-zu-EGON Freundschaften.

Alle Freundschaften leben in egons/shared/friendships/friendships.yaml.
Nicht pro EGON — sondern zentral. Weil Freundschaft keine Einbahnstrasse ist.

Funktionen:
  are_friends(a, b)          → bool
  get_friends(egon_id)       → list[str]
  get_pending_requests(egon_id) → list[dict]
  send_request(from_egon, to_egon, message) → dict
  accept_request(from_egon, to_egon) → dict
  reject_request(from_egon, to_egon) → dict

SPAETER: On-Chain Friendship Commits auf SUI.
"""

from datetime import datetime
from pathlib import Path

import yaml

from config import EGON_DATA_DIR


# ================================================================
# YAML Read/Write
# ================================================================

def _friendships_path() -> Path:
    return Path(EGON_DATA_DIR) / 'shared' / 'friendships' / 'friendships.yaml'


def _read_friendships() -> dict:
    """Liest die zentrale Friendships-Datei."""
    path = _friendships_path()
    if not path.exists():
        return {'friendships': [], 'pending_requests': []}
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        return {'friendships': [], 'pending_requests': []}
    return data


def _write_friendships(data: dict) -> None:
    """Schreibt die zentrale Friendships-Datei."""
    path = _friendships_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def _next_friendship_id(data: dict) -> str:
    """Generiert die naechste Friendship-ID (F001, F002, ...)."""
    existing = data.get('friendships', [])
    if not existing:
        return 'F001'
    ids = []
    for f in existing:
        fid = f.get('id', '')
        if fid.startswith('F') and fid[1:].isdigit():
            ids.append(int(fid[1:]))
    next_num = max(ids) + 1 if ids else 1
    return f'F{next_num:03d}'


# ================================================================
# Oeffentliche API
# ================================================================

def are_friends(egon_a: str, egon_b: str) -> bool:
    """Pruefen ob zwei EGONs befreundet sind (status: active)."""
    data = _read_friendships()
    for f in data.get('friendships', []):
        pair = {f.get('egon_a'), f.get('egon_b')}
        if pair == {egon_a, egon_b} and f.get('status') == 'active':
            return True
    return False


def get_friends(egon_id: str) -> list[str]:
    """Gibt alle aktiven Freunde eines EGONs zurueck (als ID-Liste)."""
    data = _read_friendships()
    friends = []
    for f in data.get('friendships', []):
        if f.get('status') != 'active':
            continue
        if f.get('egon_a') == egon_id:
            friends.append(f.get('egon_b'))
        elif f.get('egon_b') == egon_id:
            friends.append(f.get('egon_a'))
    return friends


def get_pending_requests(egon_id: str) -> list[dict]:
    """Gibt alle offenen Freundesanfragen AN einen EGON zurueck."""
    data = _read_friendships()
    pending = []
    for req in data.get('pending_requests', []):
        if req.get('to_egon') == egon_id:
            pending.append(req)
    return pending


def get_sent_requests(egon_id: str) -> list[dict]:
    """Gibt alle offenen Freundesanfragen VON einem EGON zurueck."""
    data = _read_friendships()
    sent = []
    for req in data.get('pending_requests', []):
        if req.get('from_egon') == egon_id:
            sent.append(req)
    return sent


def send_request(from_egon: str, to_egon: str, message: str = '') -> dict:
    """Freundesanfrage senden.

    Prueft:
    - Nicht an sich selbst
    - Nicht wenn schon befreundet
    - Nicht wenn schon eine Anfrage offen ist
    """
    if from_egon == to_egon:
        return {'success': False, 'error': 'Kann keine Anfrage an sich selbst senden.'}

    if are_friends(from_egon, to_egon):
        return {'success': False, 'error': 'Ihr seid bereits befreundet.'}

    data = _read_friendships()

    # Pruefen: Schon eine offene Anfrage?
    for req in data.get('pending_requests', []):
        pair = {req.get('from_egon'), req.get('to_egon')}
        if pair == {from_egon, to_egon}:
            return {'success': False, 'error': 'Es gibt bereits eine offene Anfrage.'}

    # Anfrage erstellen
    request = {
        'from_egon': from_egon,
        'to_egon': to_egon,
        'message': message or f'{from_egon} moechte dein Freund werden.',
        'created': datetime.now().strftime('%Y-%m-%d'),
    }
    data.setdefault('pending_requests', []).append(request)
    _write_friendships(data)

    return {
        'success': True,
        'message': f'Freundesanfrage an {to_egon} gesendet.',
        'request': request,
    }


def accept_request(from_egon: str, to_egon: str) -> dict:
    """Freundesanfrage annehmen.

    Verschiebt von pending_requests → friendships (status: active).
    """
    data = _read_friendships()

    # Anfrage finden
    pending = data.get('pending_requests', [])
    found = None
    for i, req in enumerate(pending):
        if req.get('from_egon') == from_egon and req.get('to_egon') == to_egon:
            found = i
            break

    if found is None:
        return {'success': False, 'error': 'Keine offene Anfrage gefunden.'}

    # Anfrage entfernen
    request = pending.pop(found)

    # Freundschaft erstellen
    friendship_id = _next_friendship_id(data)
    friendship = {
        'id': friendship_id,
        'egon_a': from_egon,
        'egon_b': to_egon,
        'status': 'active',
        'initiated_by': from_egon,
        'message': request.get('message', ''),
        'created': datetime.now().strftime('%Y-%m-%d'),
        'a_accepted': True,
        'b_accepted': True,
        'sui_hash': None,  # SPAETER: On-chain hash
    }
    data.setdefault('friendships', []).append(friendship)
    _write_friendships(data)

    # SPAETER: Update network.yaml beider EGONs (acquaintances)
    # SPAETER: Bond in bonds.yaml erstellen (score: 30)
    # SPAETER: sui.commit(friendship_hash)

    return {
        'success': True,
        'friendship_id': friendship_id,
        'message': f'{from_egon} und {to_egon} sind jetzt Freunde!',
        'friendship': friendship,
    }


def reject_request(from_egon: str, to_egon: str) -> dict:
    """Freundesanfrage ablehnen. Entfernt die Anfrage aus pending_requests."""
    data = _read_friendships()

    pending = data.get('pending_requests', [])
    found = None
    for i, req in enumerate(pending):
        if req.get('from_egon') == from_egon and req.get('to_egon') == to_egon:
            found = i
            break

    if found is None:
        return {'success': False, 'error': 'Keine offene Anfrage gefunden.'}

    pending.pop(found)
    _write_friendships(data)

    return {
        'success': True,
        'message': f'Anfrage von {from_egon} abgelehnt.',
    }
