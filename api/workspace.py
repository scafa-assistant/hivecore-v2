"""Workspace API — Adams Haende. Er kann Dateien erstellen, lesen, auflisten, loeschen.

Sandbox: Jeder EGON bleibt in seinem eigenen Workspace-Ordner.
Kein Directory Traversal moeglich (safe_path).
100 MB Speicher-Limit pro EGON.
"""

import os
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import EGON_DATA_DIR

router = APIRouter()

MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB pro EGON


def _workspace_root(egon_id: str) -> Path:
    """Basis-Pfad zum Workspace eines EGONs."""
    return Path(EGON_DATA_DIR) / egon_id / 'workspace'


def safe_path(egon_id: str, filepath: str) -> Path:
    """Verhindert Directory Traversal Angriffe.
    Stellt sicher dass der EGON nur in SEINEM Workspace arbeitet."""
    base = _workspace_root(egon_id)
    full = (base / filepath).resolve()
    if not str(full).startswith(str(base.resolve())):
        raise HTTPException(
            status_code=403,
            detail='Pfad ausserhalb Workspace! Zugriff verweigert.',
        )
    return full


def _get_workspace_size(egon_id: str) -> int:
    """Berechne aktuelle Workspace-Groesse in Bytes."""
    root = _workspace_root(egon_id)
    if not root.exists():
        return 0
    total = 0
    for f in root.rglob('*'):
        if f.is_file():
            total += f.stat().st_size
    return total


class WriteRequest(BaseModel):
    egon_id: str = 'adam_001'
    path: str
    content: str


class DeleteRequest(BaseModel):
    egon_id: str = 'adam_001'
    path: str


@router.post('/workspace/write')
async def write_file(req: WriteRequest):
    """Adam erstellt oder ueberschreibt eine Datei in seinem Workspace."""
    target = safe_path(req.egon_id, req.path)

    # Speicher-Limit pruefen
    new_size = len(req.content.encode('utf-8'))
    current_size = _get_workspace_size(req.egon_id)
    existing_size = target.stat().st_size if target.exists() else 0
    if current_size - existing_size + new_size > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f'Speicher-Limit erreicht! Max {MAX_SIZE_BYTES // (1024*1024)} MB.',
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding='utf-8')
    return {
        'status': 'ok',
        'path': req.path,
        'size': new_size,
        'egon_id': req.egon_id,
    }


@router.get('/workspace/read')
async def read_file(egon_id: str = 'adam_001', path: str = ''):
    """Adam liest eine seiner Dateien."""
    target = safe_path(egon_id, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail='Datei nicht gefunden.')
    return {
        'content': target.read_text(encoding='utf-8'),
        'path': path,
        'egon_id': egon_id,
    }


@router.get('/workspace/list')
async def list_files(egon_id: str = 'adam_001', folder: str = ''):
    """Adam sieht was in seinem Workspace liegt."""
    base = safe_path(egon_id, folder) if folder else _workspace_root(egon_id)
    if not base.exists() or not base.is_dir():
        return {'files': [], 'folder': folder, 'egon_id': egon_id}

    files = []
    for f in sorted(base.iterdir()):
        files.append({
            'name': f.name,
            'type': 'dir' if f.is_dir() else 'file',
            'size': f.stat().st_size if f.is_file() else 0,
        })
    return {'files': files, 'folder': folder, 'egon_id': egon_id}


@router.delete('/workspace/delete')
async def delete_file(req: DeleteRequest):
    """Adam loescht eine Datei oder einen leeren Ordner."""
    target = safe_path(req.egon_id, req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail='Datei nicht gefunden.')

    if target.is_file():
        target.unlink()
    elif target.is_dir() and not any(target.iterdir()):
        target.rmdir()
    else:
        raise HTTPException(
            status_code=400,
            detail='Ordner ist nicht leer. Erst Inhalt loeschen.',
        )

    return {'status': 'deleted', 'path': req.path, 'egon_id': req.egon_id}


@router.get('/workspace/usage')
async def workspace_usage(egon_id: str = 'adam_001'):
    """Wie viel Speicher hat Adam verbraucht?"""
    used = _get_workspace_size(egon_id)
    return {
        'egon_id': egon_id,
        'used_bytes': used,
        'used_mb': round(used / (1024 * 1024), 2),
        'max_mb': MAX_SIZE_BYTES // (1024 * 1024),
        'percent': round(used / MAX_SIZE_BYTES * 100, 1),
    }
