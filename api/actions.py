"""Actions API — Action-Log und Emergency-Stop fuer EGONs.

Zeigt alle ausgefuehrten Aktionen (SMS, Anrufe, URLs, Alarme)
und bietet einen Notfall-Stopp um alles sofort zu beenden.
"""

from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, write_yaml_organ

router = APIRouter()


@router.get('/egon/{egon_id}/action-log')
async def get_action_log(egon_id: str, limit: int = 50):
    """Gibt das Action-Log eines EGONs zurueck.

    Liest aus capabilities/action_log.yaml oder dem Ledger.
    """
    egon_path = Path(EGON_DATA_DIR) / egon_id
    if not egon_path.exists():
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden.')

    # Versuche action_log.yaml zu lesen
    action_log = read_yaml_organ(egon_id, 'capabilities', 'action_log.yaml')
    entries = action_log.get('actions', [])

    # Falls kein Log existiert, versuche aus dem Ledger zu lesen
    if not entries:
        ledger_path = egon_path / 'memory' / 'ledger.yaml'
        if ledger_path.is_file():
            try:
                with open(ledger_path, 'r', encoding='utf-8') as f:
                    ledger = yaml.safe_load(f) or {}
                entries = ledger.get('entries', [])
                # Nur Actions filtern
                entries = [e for e in entries if e.get('type') == 'action']
            except yaml.YAMLError:
                entries = []

    # Sortiere nach Timestamp (neueste zuerst), limitiere
    entries = sorted(
        entries,
        key=lambda e: e.get('timestamp', e.get('date', '')),
        reverse=True,
    )[:limit]

    return {
        'egon_id': egon_id,
        'total': len(entries),
        'actions': entries,
    }


@router.post('/egon/{egon_id}/emergency-stop')
async def emergency_stop(egon_id: str):
    """Notfall-Stopp — Beendet ALLE laufenden Aktionen sofort.

    Setzt ein Flag in state.yaml das alle Aktionen blockiert.
    Der Owner kann dies in der App triggern.
    """
    egon_path = Path(EGON_DATA_DIR) / egon_id
    if not egon_path.exists():
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden.')

    # Emergency-Stop Flag setzen
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    state['emergency_stop'] = {
        'active': True,
        'triggered_at': datetime.now().isoformat(),
        'reason': 'Owner triggered emergency stop from app',
    }
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    # Action ins Log schreiben
    action_log = read_yaml_organ(egon_id, 'capabilities', 'action_log.yaml')
    actions = action_log.get('actions', [])
    actions.append({
        'type': 'emergency_stop',
        'timestamp': datetime.now().isoformat(),
        'details': 'Alle Aktionen gestoppt durch Owner.',
        'source': 'app',
    })
    action_log['actions'] = actions
    write_yaml_organ(egon_id, 'capabilities', 'action_log.yaml', action_log)

    return {
        'success': True,
        'message': f'NOTFALL-STOPP fuer {egon_id} aktiviert. Alle Aktionen gestoppt.',
        'timestamp': datetime.now().isoformat(),
    }


@router.post('/egon/{egon_id}/emergency-stop/release')
async def release_emergency_stop(egon_id: str):
    """Hebt den Notfall-Stopp auf. EGON kann wieder Aktionen ausfuehren."""
    egon_path = Path(EGON_DATA_DIR) / egon_id
    if not egon_path.exists():
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden.')

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if 'emergency_stop' in state:
        state['emergency_stop']['active'] = False
        state['emergency_stop']['released_at'] = datetime.now().isoformat()
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return {
        'success': True,
        'message': f'Notfall-Stopp fuer {egon_id} aufgehoben.',
    }


@router.post('/egon/{egon_id}/log-action')
async def log_action(egon_id: str, action: dict):
    """Loggt eine ausgefuehrte Aktion (intern, vom Agent Loop aufgerufen)."""
    egon_path = Path(EGON_DATA_DIR) / egon_id
    if not egon_path.exists():
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden.')

    action_log = read_yaml_organ(egon_id, 'capabilities', 'action_log.yaml')
    actions = action_log.get('actions', [])

    entry = {
        'type': action.get('action', 'unknown'),
        'timestamp': datetime.now().isoformat(),
        'details': action.get('details', ''),
        'params': action.get('params', {}),
        'source': action.get('source', 'agent'),
        'success': action.get('success', True),
    }
    actions.append(entry)

    # Max 1000 Eintraege behalten
    if len(actions) > 1000:
        actions = actions[-1000:]

    action_log['actions'] = actions
    write_yaml_organ(egon_id, 'capabilities', 'action_log.yaml', action_log)

    return {'success': True, 'logged': entry}
