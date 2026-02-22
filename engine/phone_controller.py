"""Phone Controller — Adams Haende.

Adam kann das Handy seines Owners steuern via ADB
(Android Debug Bridge) ueber Tailscale.

Zwei Modi:
  1. DroidClaw — YAML-basierte Macros (bun run src/kernel.ts)
  2. DroidMind — MCP-basiert (device_tap, device_input_text, etc.)

Alle Aktionen werden im Ledger geloggt.
Alle Aktionen respektieren phone_permissions.yaml.
"""

import os
import yaml
import subprocess
from pathlib import Path
from datetime import datetime

from engine.ledger import log_transaction


# ================================================================
# Config laden
# ================================================================

_PERMISSIONS_PATH = Path(__file__).parent.parent / 'config' / 'phone_permissions.yaml'


def _load_permissions() -> dict:
    """Laedt phone_permissions.yaml."""
    if not _PERMISSIONS_PATH.is_file():
        return {}
    try:
        with open(_PERMISSIONS_PATH, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data.get('phone_control', {}) if data else {}
    except Exception:
        return {}


# ================================================================
# Permission Check
# ================================================================

def is_phone_enabled() -> bool:
    """Prueft ob Handy-Steuerung aktiviert ist."""
    perms = _load_permissions()
    return perms.get('enabled', False)


def is_app_allowed(package: str) -> bool:
    """Prueft ob eine App in der Whitelist steht."""
    perms = _load_permissions()

    # Blocked Apps pruefen (Wildcards)
    blocked = perms.get('blocked_apps', [])
    for pattern in blocked:
        if _matches_pattern(package, pattern):
            return False

    # Allowed Apps pruefen
    allowed = perms.get('allowed_apps', [])
    for app in allowed:
        if app.get('package') == package:
            return True

    return False


def requires_confirmation(package: str) -> bool:
    """Prueft ob eine Aktion auf dieser App Owner-Bestaetigung braucht."""
    perms = _load_permissions()
    allowed = perms.get('allowed_apps', [])
    for app in allowed:
        if app.get('package') == package:
            return app.get('requires_confirmation', True)
    return True  # Default: Bestaetigung noetig


def get_app_permissions(package: str) -> list:
    """Gibt die erlaubten Permissions fuer eine App zurueck."""
    perms = _load_permissions()
    allowed = perms.get('allowed_apps', [])
    for app in allowed:
        if app.get('package') == package:
            return app.get('permissions', [])
    return []


def _matches_pattern(package: str, pattern: str) -> bool:
    """Einfaches Wildcard-Matching (* am Anfang/Ende)."""
    if '*' not in pattern:
        return package == pattern
    if pattern.startswith('*.') and pattern.endswith('.*'):
        inner = pattern[2:-2]
        return inner in package
    if pattern.startswith('*.'):
        return package.endswith(pattern[1:])
    if pattern.endswith('.*'):
        return package.startswith(pattern[:-2])
    if pattern.startswith('*'):
        return pattern[1:] in package
    if pattern.endswith('*'):
        return package.startswith(pattern[:-1])
    return package == pattern


# ================================================================
# Rate Limiting
# ================================================================

# In-Memory Tracking
_action_log: list[datetime] = []
_message_log: list[datetime] = []
_call_count_today: int = 0
_last_call_date: str = ''


def _check_rate_limit(action_type: str) -> bool:
    """Prueft ob eine Aktion innerhalb der Rate-Limits ist.

    Returns: True wenn erlaubt, False wenn geblockt.
    """
    global _action_log, _message_log, _call_count_today, _last_call_date

    perms = _load_permissions()
    rules = perms.get('rules', {})
    now = datetime.now()

    # Actions per Minute
    max_apm = rules.get('max_actions_per_minute', 10)
    _action_log = [t for t in _action_log if (now - t).seconds < 60]
    if len(_action_log) >= max_apm:
        return False
    _action_log.append(now)

    # Messages per Hour
    if action_type == 'send_message':
        max_mph = rules.get('max_messages_per_hour', 20)
        _message_log = [t for t in _message_log if (now - t).seconds < 3600]
        if len(_message_log) >= max_mph:
            return False
        _message_log.append(now)

    # Calls per Day
    if action_type == 'call':
        today = now.strftime('%Y-%m-%d')
        if _last_call_date != today:
            _call_count_today = 0
            _last_call_date = today
        max_calls = rules.get('max_calls_per_day', 5)
        if _call_count_today >= max_calls:
            return False
        _call_count_today += 1

    return True


# ================================================================
# ADB Commands
# ================================================================

def _get_adb_target() -> str:
    """Gibt den ADB-Connection-String zurueck."""
    perms = _load_permissions()
    ip = perms.get('device_ip', '')
    port = perms.get('adb_port', 5555)
    if ip:
        return f'{ip}:{port}'
    return ''


def _adb_command(args: list[str], timeout: int = 30) -> dict:
    """Fuehrt einen ADB-Befehl aus.

    Returns: {'success': bool, 'output': str, 'error': str}
    """
    target = _get_adb_target()
    if not target:
        return {'success': False, 'output': '', 'error': 'Kein ADB-Ziel konfiguriert'}

    cmd = ['adb', '-s', target] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'error': result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': '', 'error': 'ADB Timeout'}
    except FileNotFoundError:
        return {'success': False, 'output': '', 'error': 'ADB nicht installiert'}


# ================================================================
# High-Level Actions
# ================================================================

def execute_action(
    egon_id: str,
    action_type: str,
    package: str,
    params: dict,
) -> dict:
    """Fuehrt eine Handy-Aktion aus (mit allen Checks).

    Args:
        egon_id: EGON ID
        action_type: 'send_message', 'call', 'open_app', 'navigate', etc.
        package: Android Package Name (z.B. 'com.whatsapp')
        params: Aktions-spezifische Parameter

    Returns:
        {'success': bool, 'message': str, 'requires_confirmation': bool}
    """
    # 1. Ist Phone-Control aktiviert?
    if not is_phone_enabled():
        return {
            'success': False,
            'message': 'Handy-Steuerung ist nicht aktiviert.',
            'requires_confirmation': False,
        }

    # 2. Ist die App erlaubt?
    if not is_app_allowed(package):
        return {
            'success': False,
            'message': f'App {package} ist nicht in der Whitelist.',
            'requires_confirmation': False,
        }

    # 3. Rate-Limit Check
    if not _check_rate_limit(action_type):
        return {
            'success': False,
            'message': f'Rate-Limit fuer {action_type} erreicht.',
            'requires_confirmation': False,
        }

    # 4. Braucht Owner-Bestaetigung?
    if requires_confirmation(package):
        return {
            'success': False,
            'message': f'Diese Aktion auf {package} braucht Owner-Bestaetigung.',
            'requires_confirmation': True,
            'pending_action': {
                'action_type': action_type,
                'package': package,
                'params': params,
            },
        }

    # 5. Aktion ausfuehren
    result = _execute_adb_action(action_type, package, params)

    # 6. Im Ledger loggen
    log_transaction(egon_id, f'phone_{action_type}', {
        'package': package,
        'params': {k: v for k, v in params.items() if k != 'password'},
        'success': result['success'],
        'timestamp': datetime.now().isoformat(),
    })

    return result


def _execute_adb_action(
    action_type: str,
    package: str,
    params: dict,
) -> dict:
    """Fuehrt die eigentliche ADB-Aktion aus."""
    if action_type == 'open_app':
        result = _adb_command([
            'shell', 'monkey', '-p', package,
            '-c', 'android.intent.category.LAUNCHER', '1',
        ])
        return {
            'success': result['success'],
            'message': f'App {package} geoeffnet' if result['success'] else result['error'],
        }

    elif action_type == 'send_message':
        # Generisch: App oeffnen, Text eingeben via ADB
        contact = params.get('contact', '')
        text = params.get('text', '')

        # App starten
        _adb_command(['shell', 'monkey', '-p', package,
                      '-c', 'android.intent.category.LAUNCHER', '1'])

        # Text eingeben (generisch via ADB input)
        if text:
            # ADB input text (Leerzeichen escapen)
            escaped = text.replace(' ', '%s').replace("'", "\\'")
            _adb_command(['shell', 'input', 'text', escaped])

        return {
            'success': True,
            'message': f'Text eingegeben in {package}',
        }

    elif action_type == 'navigate':
        url = params.get('url', '')
        _adb_command([
            'shell', 'am', 'start',
            '-a', 'android.intent.action.VIEW',
            '-d', url,
        ])
        return {
            'success': True,
            'message': f'URL geoeffnet: {url}',
        }

    elif action_type == 'screenshot':
        # Screenshot machen und lokal speichern
        _adb_command(['shell', 'screencap', '/sdcard/screenshot.png'])
        local_path = params.get('save_to', '/tmp/phone_screenshot.png')
        result = _adb_command(['pull', '/sdcard/screenshot.png', local_path])
        return {
            'success': result['success'],
            'message': f'Screenshot gespeichert: {local_path}' if result['success'] else result['error'],
        }

    elif action_type == 'call':
        number = params.get('number', '')
        if not number:
            return {'success': False, 'message': 'Keine Telefonnummer angegeben'}

        _adb_command([
            'shell', 'am', 'start',
            '-a', 'android.intent.action.CALL',
            '-d', f'tel:{number}',
        ])
        return {
            'success': True,
            'message': f'Anruf gestartet: {number}',
        }

    else:
        return {
            'success': False,
            'message': f'Unbekannter Action-Typ: {action_type}',
        }


# ================================================================
# Convenience Functions
# ================================================================

def get_allowed_apps() -> list[dict]:
    """Gibt die Liste der erlaubten Apps zurueck."""
    perms = _load_permissions()
    return perms.get('allowed_apps', [])


def get_phone_status() -> dict:
    """Gibt den aktuellen Handy-Status zurueck."""
    perms = _load_permissions()
    enabled = perms.get('enabled', False)

    if not enabled:
        return {'enabled': False, 'connected': False}

    # ADB-Verbindung testen
    result = _adb_command(['devices'])
    target = _get_adb_target()
    connected = target in result.get('output', '')

    return {
        'enabled': True,
        'connected': connected,
        'device_ip': perms.get('device_ip', ''),
        'controller': perms.get('controller', {}).get('type', 'none'),
        'allowed_apps': len(perms.get('allowed_apps', [])),
        'blocked_apps': len(perms.get('blocked_apps', [])),
    }
