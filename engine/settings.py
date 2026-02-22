"""EGON Settings — Pro-EGON Konfiguration.

Jeder EGON hat seine eigenen Einstellungen in:
  egons/{egon_id}/config/settings.yaml

Funktionen:
  read_settings(egon_id)            → dict (komplett mit Defaults)
  write_settings(egon_id, data)     → None
  get_setting(egon_id, *keys)       → Any (z.B. get_setting('adam_001', 'wallet', 'enabled'))
  update_setting(egon_id, updates)  → dict (merged + geschrieben)
  is_wallet_enabled(egon_id)        → bool
  is_agora_enabled(egon_id)         → bool
  get_api_mode(egon_id)             → str
  get_daily_limit(egon_id)          → int
"""

from pathlib import Path
from copy import deepcopy

import yaml

from config import EGON_DATA_DIR


# ================================================================
# Defaults — Was ein frischer EGON bekommt
# ================================================================

SETTINGS_DEFAULTS = {
    'display': {
        'homescreen_widget': False,
        'widget_size': 'medium',
        'show_mood': True,
        'show_name': True,
        'tap_action': 'open_chat',
        'battery_saver': True,
    },
    'wallet': {
        'enabled': False,
    },
    'agora': {
        'enabled': False,
    },
    'nft_trading': {
        'enabled': False,
    },
    'api': {
        'mode': 'owner_api',
        'api_key': 'shared',
        'daily_limit': 100,
    },
}


# ================================================================
# Read / Write
# ================================================================

def _settings_path(egon_id: str) -> Path:
    return Path(EGON_DATA_DIR) / egon_id / 'config' / 'settings.yaml'


def _deep_merge(defaults: dict, overrides: dict) -> dict:
    """Merged overrides in defaults. Fehlende Keys werden aus Defaults ergaenzt."""
    result = deepcopy(defaults)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def read_settings(egon_id: str) -> dict:
    """Liest die Settings eines EGONs. Merged mit Defaults.

    Wenn settings.yaml nicht existiert, werden nur Defaults zurueckgegeben.
    """
    path = _settings_path(egon_id)
    if not path.exists():
        return deepcopy(SETTINGS_DEFAULTS)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if not data or not isinstance(data, dict):
            return deepcopy(SETTINGS_DEFAULTS)
        return _deep_merge(SETTINGS_DEFAULTS, data)
    except Exception:
        return deepcopy(SETTINGS_DEFAULTS)


def write_settings(egon_id: str, data: dict) -> None:
    """Schreibt die Settings eines EGONs."""
    path = _settings_path(egon_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def get_setting(egon_id: str, *keys: str):
    """Liest einen verschachtelten Setting-Wert.

    Beispiel: get_setting('adam_001', 'wallet', 'enabled') → False
    """
    settings = read_settings(egon_id)
    current = settings
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current


def update_settings(egon_id: str, updates: dict) -> dict:
    """Merged updates in bestehende Settings und schreibt zurueck.

    Args:
        egon_id: EGON-ID
        updates: Partielle Updates (z.B. {'wallet': {'enabled': True}})

    Returns:
        Komplette gemergte Settings.
    """
    current = read_settings(egon_id)
    merged = _deep_merge(current, updates)
    write_settings(egon_id, merged)
    return merged


# ================================================================
# Convenience-Funktionen
# ================================================================

def is_wallet_enabled(egon_id: str) -> bool:
    """Ist das Wallet fuer diesen EGON aktiv?"""
    return get_setting(egon_id, 'wallet', 'enabled') is True


def is_agora_enabled(egon_id: str) -> bool:
    """Ist die Agora fuer diesen EGON aktiv?"""
    return get_setting(egon_id, 'agora', 'enabled') is True


def is_nft_trading_enabled(egon_id: str) -> bool:
    """Ist NFT-Trading fuer diesen EGON aktiv?"""
    return get_setting(egon_id, 'nft_trading', 'enabled') is True


def get_api_mode(egon_id: str) -> str:
    """Welcher API-Modus ist aktiv? (owner_api | server_llm | credit_api)"""
    mode = get_setting(egon_id, 'api', 'mode')
    return mode if mode in ('owner_api', 'server_llm', 'credit_api') else 'owner_api'


def get_daily_limit(egon_id: str) -> int:
    """Wie viele API-Calls darf dieser EGON pro Tag machen?"""
    limit = get_setting(egon_id, 'api', 'daily_limit')
    return int(limit) if limit and isinstance(limit, (int, float)) else 100
