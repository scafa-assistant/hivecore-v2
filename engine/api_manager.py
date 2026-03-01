"""API Manager — Tageslimits und Kosten-Tracking.

EGONs haben verschiedene Denkwege. Manche sind schnell und leicht.
Manche sind tief und teuer. Alles laeuft ueber Moonshot / Kimi K2.5.

Deshalb:
- Tageslimits (config/api_limits.yaml)
- Kosten-Tracking in wallet.yaml
- Bezugsmensch-Benachrichtigung bei Warnungen und Limits
- Kosten-Tracking in wallet.yaml
"""

import os
import yaml
from datetime import datetime, date
from pathlib import Path

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, write_yaml_organ


# ================================================================
# Config laden
# ================================================================

_LIMITS_PATH = Path(__file__).parent.parent / 'config' / 'api_limits.yaml'


def _load_limits() -> dict:
    """Laedt api_limits.yaml."""
    if not _LIMITS_PATH.is_file():
        return {}
    try:
        with open(_LIMITS_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


# ================================================================
# Usage Tracking (In-Memory + wallet.yaml Persist)
# ================================================================

# In-Memory Cache fuer den aktuellen Tag
_daily_usage: dict[str, dict[str, int]] = {}
_usage_date: str = ''


def _get_today() -> str:
    return date.today().isoformat()


def _ensure_fresh_usage(egon_id: str) -> dict:
    """Stellt sicher dass die Usage-Daten vom heutigen Tag sind."""
    global _daily_usage, _usage_date

    today = _get_today()
    if _usage_date != today:
        # Neuer Tag → Reset
        _daily_usage = {}
        _usage_date = today

    if egon_id not in _daily_usage:
        _daily_usage[egon_id] = {
            'tier1_local': 0,
            'tier2_cloud': 0,
            'tier3_premium': 0,
        }

    return _daily_usage[egon_id]


# ================================================================
# Tier Mapping (numeric ↔ config key)
# ================================================================

TIER_TO_KEY = {
    1: 'tier1_local',
    2: 'tier2_cloud',
    3: 'tier3_premium',
}

KEY_TO_TIER = {v: k for k, v in TIER_TO_KEY.items()}


# ================================================================
# Core: Limit Check + Downgrade
# ================================================================

def check_and_track_call(egon_id: str, tier: int) -> dict:
    """Prueft ob ein Call auf dem gewuenschten Tier erlaubt ist.

    Returns:
        {
            'allowed': True/False,
            'tier': int (evtl. downgraded),
            'tier_key': str,
            'downgraded': bool,
            'warning': str or None,
            'blocked': bool,
        }
    """
    limits = _load_limits()
    tiers_config = limits.get('api_tiers', {})
    downgrade_chain = limits.get('downgrade_chain', {})
    usage = _ensure_fresh_usage(egon_id)

    tier_key = TIER_TO_KEY.get(tier, 'tier1_local')
    original_tier = tier
    downgraded = False
    warning = None

    # Versuche den gewuenschten Tier
    while tier_key:
        tier_config = tiers_config.get(tier_key, {})
        daily_limit = tier_config.get('daily_limit')
        used = usage.get(tier_key, 0)

        if daily_limit is None or used < daily_limit:
            # Limit nicht erreicht — Call erlaubt

            # Warning pruefen
            warning_at = tier_config.get('warning_at')
            if warning_at and used >= warning_at:
                remaining = daily_limit - used if daily_limit else '∞'
                warning = (
                    f'Ich habe heute {used} von {daily_limit} '
                    f'{tier_config.get("model", tier_key)}-Calls verbraucht. '
                    f'Noch {remaining} uebrig.'
                )

            # Usage tracken
            usage[tier_key] = used + 1

            return {
                'allowed': True,
                'tier': KEY_TO_TIER.get(tier_key, 1),
                'tier_key': tier_key,
                'downgraded': downgraded,
                'original_tier': original_tier,
                'warning': warning,
                'blocked': False,
            }

        # Limit erreicht — Downgrade versuchen
        next_key = downgrade_chain.get(tier_key)
        if next_key:
            tier_key = next_key
            downgraded = True
            warning = (
                f'Mein {tiers_config.get(TIER_TO_KEY.get(original_tier, ""), {}).get("model", "")} '
                f'Limit ist erreicht. Arbeite mit guenstigerem Tier weiter.'
            )
        else:
            # Kein weiterer Fallback — blockiert
            return {
                'allowed': False,
                'tier': original_tier,
                'tier_key': TIER_TO_KEY.get(original_tier, 'tier1_local'),
                'downgraded': False,
                'original_tier': original_tier,
                'warning': None,
                'blocked': True,
                'message': (
                    'Alle meine API-Limits sind fuer heute aufgebraucht. '
                    'Kann ich mehr Budget bekommen?'
                ),
            }

    # Fallback: Erlauben auf Tier 1
    usage['tier1_local'] = usage.get('tier1_local', 0) + 1
    return {
        'allowed': True,
        'tier': 1,
        'tier_key': 'tier1_local',
        'downgraded': tier != 1,
        'original_tier': original_tier,
        'warning': warning,
        'blocked': False,
    }


# ================================================================
# Kosten-Tracking → wallet.yaml
# ================================================================

def track_cost(egon_id: str, tier_key: str) -> None:
    """Trackt die Kosten eines API-Calls in wallet.yaml."""
    limits = _load_limits()
    tier_config = limits.get('api_tiers', {}).get(tier_key, {})
    cost = tier_config.get('cost_per_call', 0)

    if cost <= 0:
        return

    wallet = read_yaml_organ(egon_id, 'capabilities', 'wallet.yaml')
    if not wallet:
        return

    # api_costs Struktur sicherstellen
    if 'api_costs' not in wallet:
        wallet['api_costs'] = {
            'today': {
                'date': _get_today(),
                'tier1_calls': 0, 'tier1_cost': 0.0,
                'tier2_calls': 0, 'tier2_cost': 0.0,
                'tier3_calls': 0, 'tier3_cost': 0.0,
                'total_cost': 0.0,
            },
            'this_month': {
                'month': datetime.now().strftime('%Y-%m'),
                'total_cost': 0.0,
            },
        }

    api_costs = wallet['api_costs']
    today_data = api_costs.get('today', {})

    # Reset wenn neuer Tag
    if today_data.get('date') != _get_today():
        today_data = {
            'date': _get_today(),
            'tier1_calls': 0, 'tier1_cost': 0.0,
            'tier2_calls': 0, 'tier2_cost': 0.0,
            'tier3_calls': 0, 'tier3_cost': 0.0,
            'total_cost': 0.0,
        }

    # Tier-spezifisch tracken
    tier_num = KEY_TO_TIER.get(tier_key, 1)
    calls_key = f'tier{tier_num}_calls'
    cost_key = f'tier{tier_num}_cost'

    today_data[calls_key] = today_data.get(calls_key, 0) + 1
    today_data[cost_key] = round(today_data.get(cost_key, 0.0) + cost, 4)
    today_data['total_cost'] = round(today_data.get('total_cost', 0.0) + cost, 4)

    api_costs['today'] = today_data

    # Monatlich
    month_data = api_costs.get('this_month', {})
    current_month = datetime.now().strftime('%Y-%m')
    if month_data.get('month') != current_month:
        month_data = {'month': current_month, 'total_cost': 0.0}
    month_data['total_cost'] = round(month_data.get('total_cost', 0.0) + cost, 4)
    api_costs['this_month'] = month_data

    wallet['api_costs'] = api_costs
    write_yaml_organ(egon_id, 'capabilities', 'wallet.yaml', wallet)

    # Balance-Abzug — echte Kosten von Balance abziehen
    try:
        from engine.wallet_bridge import deduct_cost
        deduct_cost(egon_id, cost, f'api_call_tier{tier_num}')
    except Exception:
        pass  # Wallet-Bridge darf track_cost nie blockieren


# ================================================================
# Usage Summary (fuer Prompts und Dashboard)
# ================================================================

def get_usage_summary(egon_id: str) -> dict:
    """Gibt eine Zusammenfassung der heutigen API-Nutzung zurueck."""
    usage = _ensure_fresh_usage(egon_id)
    limits = _load_limits()
    tiers_config = limits.get('api_tiers', {})

    summary = {}
    for tier_key, count in usage.items():
        config = tiers_config.get(tier_key, {})
        limit = config.get('daily_limit')
        summary[tier_key] = {
            'used': count,
            'limit': limit,
            'remaining': (limit - count) if limit else None,
            'model': config.get('model', '?'),
        }

    return summary


def get_daily_cost(egon_id: str) -> float:
    """Gibt die heutigen Gesamtkosten zurueck."""
    wallet = read_yaml_organ(egon_id, 'capabilities', 'wallet.yaml')
    if not wallet:
        return 0.0
    return wallet.get('api_costs', {}).get('today', {}).get('total_cost', 0.0)
