"""Tool Executor — Fuehrt Adams Werkzeuge aus.

Dispatched Tool-Calls zu den richtigen Handlern.
Nutzt bestehende Workspace-Logik (safe_path, Size-Limits).
Jeder Handler ist async und gibt ein dict zurueck.
"""

import json
import traceback
from pathlib import Path
from config import EGON_DATA_DIR


# ================================================================
# Workspace Helpers (aus api/workspace.py extrahierte Logik)
# ================================================================

MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB pro EGON


def _workspace_root(egon_id: str) -> Path:
    return Path(EGON_DATA_DIR) / egon_id / 'workspace'


def _safe_path(egon_id: str, filepath: str) -> Path:
    """Sichere Pfadberechnung. Wirft ValueError bei Traversal-Versuch."""
    base = _workspace_root(egon_id)
    full = (base / filepath).resolve()
    if not str(full).startswith(str(base.resolve())):
        raise ValueError('Pfad ausserhalb Workspace! Zugriff verweigert.')
    return full


def _get_workspace_size(egon_id: str) -> int:
    root = _workspace_root(egon_id)
    if not root.exists():
        return 0
    return sum(f.stat().st_size for f in root.rglob('*') if f.is_file())


# ================================================================
# Tool Handlers
# ================================================================

async def _handle_workspace_write(egon_id: str, params: dict) -> dict:
    path = params.get('path', '')
    content = params.get('content', '')

    if not path:
        return {'error': 'Kein Pfad angegeben.'}
    if not content:
        return {'error': 'Kein Inhalt angegeben.'}

    target = _safe_path(egon_id, path)

    # Speicher-Limit
    new_size = len(content.encode('utf-8'))
    current_size = _get_workspace_size(egon_id)
    existing_size = target.stat().st_size if target.exists() else 0
    if current_size - existing_size + new_size > MAX_SIZE_BYTES:
        return {
            'error': f'Speicher-Limit erreicht! Max {MAX_SIZE_BYTES // (1024*1024)} MB.',
            'used_mb': round(current_size / (1024 * 1024), 2),
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')

    return {
        'status': 'ok',
        'path': path,
        'size': new_size,
        'message': f'Datei {path} erstellt ({new_size} Bytes).',
    }


async def _handle_workspace_read(egon_id: str, params: dict) -> dict:
    path = params.get('path', '')
    if not path:
        return {'error': 'Kein Pfad angegeben.'}

    target = _safe_path(egon_id, path)
    if not target.exists() or not target.is_file():
        return {'error': f'Datei {path} nicht gefunden.'}

    content = target.read_text(encoding='utf-8')
    # Truncate bei sehr grossen Dateien (Context-Budget!)
    max_chars = 10000
    truncated = len(content) > max_chars
    return {
        'content': content[:max_chars],
        'path': path,
        'size': len(content),
        'truncated': truncated,
    }


async def _handle_workspace_list(egon_id: str, params: dict) -> dict:
    folder = params.get('folder', '')
    base = _safe_path(egon_id, folder) if folder else _workspace_root(egon_id)

    if not base.exists() or not base.is_dir():
        return {'files': [], 'folder': folder}

    files = []
    for f in sorted(base.iterdir()):
        files.append({
            'name': f.name,
            'type': 'dir' if f.is_dir() else 'file',
            'size': f.stat().st_size if f.is_file() else 0,
        })

    return {'files': files, 'folder': folder, 'count': len(files)}


async def _handle_workspace_delete(egon_id: str, params: dict) -> dict:
    path = params.get('path', '')
    if not path:
        return {'error': 'Kein Pfad angegeben.'}

    target = _safe_path(egon_id, path)
    if not target.exists():
        return {'error': f'Datei {path} nicht gefunden.'}

    if target.is_file():
        target.unlink()
        return {'status': 'deleted', 'path': path}
    elif target.is_dir() and not any(target.iterdir()):
        target.rmdir()
        return {'status': 'deleted', 'path': path}
    else:
        return {'error': 'Ordner ist nicht leer.'}


async def _handle_web_fetch(egon_id: str, params: dict) -> dict:
    """Web-Fetch — Phase B. Gibt Platzhalter zurueck wenn engine/web.py nicht existiert."""
    try:
        from engine.web import fetch_url
        return await fetch_url(
            url=params.get('url', ''),
            max_chars=params.get('max_chars', 5000),
        )
    except ImportError:
        return {'error': 'Web-Browsing ist noch nicht installiert (Phase B).'}


async def _handle_web_search(egon_id: str, params: dict) -> dict:
    """Web-Search — Phase B."""
    try:
        from engine.web import web_search
        return await web_search(query=params.get('query', ''))
    except ImportError:
        return {'error': 'Web-Suche ist noch nicht installiert (Phase B).'}


async def _handle_skill_search(egon_id: str, params: dict) -> dict:
    """Skill-Search — Phase C."""
    try:
        import asyncio
        from engine.skill_installer import search_skills
        # search_skills() ist synchron (npx CLI) — in Thread wrappen
        results = await asyncio.to_thread(search_skills, params.get('query', ''))
        return {'results': results}
    except (ImportError, Exception) as e:
        return {'error': f'Skill-Suche fehlgeschlagen: {e}'}


async def _handle_skill_install(egon_id: str, params: dict) -> dict:
    """Skill-Install — Phase C."""
    try:
        from engine.skill_installer import install_skill
        result = await install_skill(egon_id, params.get('skill_url', ''))
        return result
    except (ImportError, Exception) as e:
        return {'error': f'Skill-Installation fehlgeschlagen: {e}'}


# ================================================================
# Handler Registry
# ================================================================

HANDLERS = {
    'workspace_write': _handle_workspace_write,
    'workspace_read': _handle_workspace_read,
    'workspace_list': _handle_workspace_list,
    'workspace_delete': _handle_workspace_delete,
    'web_fetch': _handle_web_fetch,
    'web_search': _handle_web_search,
    'skill_search': _handle_skill_search,
    'skill_install': _handle_skill_install,
}


# ================================================================
# Main Dispatch
# ================================================================

async def execute_tool(egon_id: str, tool_name: str, params: dict) -> dict:
    """Fuehre ein Tool aus. Gibt immer ein dict zurueck (nie Exception).

    Args:
        egon_id: EGON-ID (z.B. 'adam')
        tool_name: Name des Tools (z.B. 'workspace_write')
        params: Parameter als dict

    Returns:
        Ergebnis-dict. Bei Fehler: {'error': 'Beschreibung'}
    """
    handler = HANDLERS.get(tool_name)

    if not handler:
        return {'error': f'Unbekanntes Tool: {tool_name}'}

    try:
        result = await handler(egon_id, params)
        return result
    except ValueError as e:
        return {'error': str(e)}
    except Exception as e:
        print(f'[tool_executor] Error in {tool_name}: {traceback.format_exc()}')
        return {'error': f'Tool-Fehler: {str(e)}'}
