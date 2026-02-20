"""Blockchain-Ready Logging — jede Aktion wird gehasht.

DESIGN-PRINZIP: Blockchain-ready OHNE Blockchain.
Jede Aktion wird mit SHA256-Hash + Timestamp geloggt.
SPAETER wird jeder Hash on-chain committed (SUI Transaction).
Migration: Nur Schritt 5-6 hinzufuegen. Schritte 1-4 aendern sich NIE.
"""

import hashlib
import json
import os
from datetime import datetime
from config import EGON_DATA_DIR


def log_transaction(
    egon_id: str,
    action: str,
    data: dict,
    counterparty: str = None,
) -> dict:
    """Loggt eine Aktion blockchain-ready."""
    entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'egon_id': egon_id,
        'action': action,
        'data': data,
        'counterparty': counterparty,
    }

    # Hash berechnen
    entry_json = json.dumps(entry, sort_keys=True)
    entry['hash'] = hashlib.sha256(entry_json.encode()).hexdigest()

    # In wallet.md appenden
    path = os.path.join(EGON_DATA_DIR, egon_id, 'wallet.md')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(f'\n## TX {entry["hash"][:12]}\n')
        f.write(f'action: {action}\n')
        f.write(f'data: {json.dumps(data)}\n')
        f.write(f'time: {entry["timestamp"]}\n')
        f.write(f'hash: {entry["hash"]}\n')
        if counterparty:
            f.write(f'counterparty: {counterparty}\n')

    # SPAETER: await sui.commit(entry['hash'])
    return entry
