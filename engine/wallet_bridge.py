"""Wallet Bridge — verbindet Kosten-Tracking mit echten Balance-Aenderungen.

Verbindet:
  api_manager.py (Kosten-Tracking) → Balance-Abzug
  pulse_v2.py (Taeglich)           → Grundumsatz-Abzug
  ledger.py (Blockchain-ready)     → Audit-Trail fuer jede Aenderung

Design-Prinzipien:
  - Alle Reads/Writes ueber organ_reader (Konsistenz)
  - Jede Balance-Aenderung wird im Ledger geloggt (Blockchain-ready)
  - Negative Balance erlaubt (Schulden) — blockiert Adam nicht, aber er merkt es
  - Transactions capped bei 50 Eintraegen
  - round(..., 4) wie in api_manager.py
  - Config-Flag: config/finances.yaml → credits.enabled steuert ob Abzuege aktiv sind
"""

from datetime import datetime
from pathlib import Path

import yaml

from engine.organ_reader import read_yaml_organ, write_yaml_organ
from engine.ledger import log_transaction


# ================================================================
# Finanzen Config-Check
# ================================================================

def _finances_enabled_global() -> bool:
    """Prueft ob das Credit-System GLOBAL aktiv ist.

    Liest config/finances.yaml → credits.enabled.
    Default: True (wenn Config nicht existiert, Abzuege aktiv).
    """
    try:
        config_path = Path(__file__).parent.parent / 'config' / 'finances.yaml'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            if cfg and isinstance(cfg, dict):
                return cfg.get('credits', {}).get('enabled', True)
    except Exception:
        pass
    return True  # Default: aktiv (sicher)


def _finances_enabled(egon_id: str = '') -> bool:
    """Prueft ob Finanzen fuer einen EGON aktiv sind.

    Zwei-Stufen-Check:
    1. Global: config/finances.yaml → credits.enabled
    2. Per-EGON: egons/{id}/config/settings.yaml → wallet.enabled

    Beide muessen True sein damit Abzuege passieren.
    Wenn kein egon_id uebergeben wird, nur global checken.
    """
    # Stufe 1: Global
    if not _finances_enabled_global():
        return False

    # Stufe 2: Per-EGON (wenn ID vorhanden)
    if egon_id:
        try:
            from engine.settings import is_wallet_enabled
            return is_wallet_enabled(egon_id)
        except Exception:
            pass

    return True  # Default: aktiv


# ================================================================
# Interne Helfer
# ================================================================

def _read_wallet(egon_id: str) -> dict:
    """Liest wallet.yaml. Gibt leeres dict zurueck wenn nicht vorhanden."""
    data = read_yaml_organ(egon_id, 'capabilities', 'wallet.yaml')
    return data if data else {}


def _write_wallet(egon_id: str, wallet: dict) -> None:
    """Schreibt wallet.yaml zurueck."""
    write_yaml_organ(egon_id, 'capabilities', 'wallet.yaml', wallet)


def _check_runway(wallet: dict) -> dict | None:
    """Prueft ob Balance < 3 Tage Runway. Gibt Warning-Dict oder None zurueck."""
    balance = wallet.get('balance', 0)
    daily_cost = wallet.get('daily_cost', 10)

    if daily_cost <= 0:
        return None

    days_left = balance / daily_cost
    if days_left < 3:
        return {
            'warning': 'low_balance',
            'balance': balance,
            'daily_cost': daily_cost,
            'days_left': round(days_left, 1),
            'message': (
                f'Kontostand niedrig: {balance} Credits. '
                f'Reicht nur noch fuer ~{round(days_left, 1)} Tage.'
            ),
        }
    return None


def _append_transaction(wallet: dict, tx: dict) -> None:
    """Haengt eine Transaction an wallet['transactions'] an. Max 50 Eintraege."""
    if 'transactions' not in wallet:
        wallet['transactions'] = []

    wallet['transactions'].append(tx)

    # Nur die letzten 50 behalten
    if len(wallet['transactions']) > 50:
        wallet['transactions'] = wallet['transactions'][-50:]


# ================================================================
# Oeffentliche API
# ================================================================

def deduct_cost(egon_id: str, amount: float, reason: str) -> dict:
    """Zieht amount von der Balance ab. Loggt im Ledger. Warnt wenn niedrig.

    Wenn Finanzen deaktiviert (global ODER per-EGON),
    wird kein Abzug gemacht und {success: True, skipped: True} zurueckgegeben.

    Args:
        egon_id: EGON-ID (z.B. 'adam_001')
        amount: Positiver Betrag zum Abziehen
        reason: Grund (z.B. 'api_call_tier2', 'daily_maintenance')

    Returns:
        {success, balance_before, balance_after, amount, warning}
    """
    if not _finances_enabled(egon_id):
        return {'success': True, 'skipped': True, 'reason': 'finances_disabled'}

    if amount <= 0:
        return {'success': False, 'error': 'amount must be positive'}

    wallet = _read_wallet(egon_id)
    if not wallet:
        return {'success': False, 'error': 'wallet.yaml not found'}

    balance_before = wallet.get('balance', 0)
    balance_after = round(balance_before - amount, 4)

    # Negative Balance erlaubt (Schulden) — Adam soll es merken
    wallet['balance'] = balance_after

    # Transaction-Record
    tx = {
        'type': 'expense',
        'amount': amount,
        'reason': reason,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'balance_after': balance_after,
    }
    _append_transaction(wallet, tx)

    _write_wallet(egon_id, wallet)

    # Ledger (Blockchain-ready Audit)
    log_transaction(
        egon_id=egon_id,
        action='deduct',
        data={
            'amount': amount,
            'reason': reason,
            'balance_before': balance_before,
            'balance_after': balance_after,
        },
    )

    # Runway-Warnung
    warning = _check_runway(wallet)

    return {
        'success': True,
        'balance_before': balance_before,
        'balance_after': balance_after,
        'amount': amount,
        'warning': warning,
    }


def add_income(egon_id: str, amount: float, source: str) -> dict:
    """Fuegt amount zur Balance hinzu. Loggt im Ledger.

    Args:
        egon_id: EGON-ID
        amount: Positiver Betrag
        source: Einkommensquelle (z.B. 'genesis_grant', 'agora_job', 'owner_topup')

    Returns:
        {success, balance_before, balance_after, amount}
    """
    if amount <= 0:
        return {'success': False, 'error': 'amount must be positive'}

    wallet = _read_wallet(egon_id)
    if not wallet:
        return {'success': False, 'error': 'wallet.yaml not found'}

    balance_before = wallet.get('balance', 0)
    balance_after = round(balance_before + amount, 4)
    wallet['balance'] = balance_after

    tx = {
        'type': 'income',
        'amount': amount,
        'reason': source,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'balance_after': balance_after,
    }
    _append_transaction(wallet, tx)

    _write_wallet(egon_id, wallet)

    log_transaction(
        egon_id=egon_id,
        action='income',
        data={
            'amount': amount,
            'source': source,
            'balance_before': balance_before,
            'balance_after': balance_after,
        },
    )

    return {
        'success': True,
        'balance_before': balance_before,
        'balance_after': balance_after,
        'amount': amount,
    }


def check_balance(egon_id: str, required_amount: float = 0) -> dict:
    """Prueft aktuelle Balance und ob required_amount leistbar ist.

    Args:
        egon_id: EGON-ID
        required_amount: Benoetigter Betrag (0 = nur Balance-Info)

    Returns:
        {balance, can_afford, daily_cost, days_left, warning}
    """
    wallet = _read_wallet(egon_id)
    if not wallet:
        return {
            'balance': 0,
            'can_afford': False,
            'daily_cost': 0,
            'days_left': 0,
            'warning': None,
        }

    balance = wallet.get('balance', 0)
    daily_cost = wallet.get('daily_cost', 10)
    days_left = balance / daily_cost if daily_cost > 0 else float('inf')

    return {
        'balance': balance,
        'can_afford': balance >= required_amount,
        'daily_cost': daily_cost,
        'days_left': round(days_left, 1),
        'warning': _check_runway(wallet),
    }


def daily_maintenance(egon_id: str) -> dict:
    """Zieht den taeglichen Grundumsatz ab. Wird vom Pulse aufgerufen.

    Wenn Finanzen deaktiviert, wird kein Abzug gemacht.

    Returns:
        deduct_cost Result-Dict
    """
    if not _finances_enabled(egon_id):
        return {'success': True, 'skipped': True, 'reason': 'finances_disabled'}

    wallet = _read_wallet(egon_id)
    if not wallet:
        return {'success': False, 'error': 'wallet.yaml not found'}

    daily_cost = wallet.get('daily_cost', 10)
    if daily_cost <= 0:
        return {'success': True, 'amount': 0, 'skipped': True}

    return deduct_cost(egon_id, daily_cost, 'daily_maintenance')
