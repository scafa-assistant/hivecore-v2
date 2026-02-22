"""Files API — CRUD fuer .md Brain-Files."""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import EGON_DATA_DIR
from engine.visibility import get_visible_files

router = APIRouter()

ALLOWED_FILES = [
    'soul.md', 'memory.md', 'markers.md', 'bonds.md',
    'skills.md', 'wallet.md', 'inner_voice.md', 'experience.md',
]

# v1 → v2 Fallback: Wenn v1-Datei nicht existiert, v2-Pfad versuchen.
# Noetig fuer v2-EGONs (z.B. Eva) die keine v1-Root-Dateien haben.
V1_TO_V2_FALLBACK = {
    'soul.md':        'core/dna.md',
    'experience.md':  'core/ego.md',
    'markers.md':     'core/state.yaml',
    'bonds.md':       'social/bonds.yaml',
    'skills.md':      'capabilities/skills.yaml',
    'wallet.md':      'capabilities/wallet.yaml',
    'memory.md':      'memory/inner_voice.md',
    'inner_voice.md': 'memory/inner_voice.md',
}


@router.get('/egon/{egon_id}/file/{filename}')
async def read_file(egon_id: str, filename: str, context: str = 'owner_dashboard'):
    """Lese eine .md File (respektiert Sichtbarkeits-Matrix).
    Unterstuetzt v1-Dateien (Root-Ordner) mit automatischem Fallback
    auf v2-Dateien (core/, social/, etc.) fuer neuere EGONs.
    """
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail=f'File {filename} not found')

    visible = get_visible_files(context)
    if filename not in visible:
        raise HTTPException(status_code=403, detail=f'File {filename} not visible in context {context}')

    # v1-Pfad (Root-Ordner) versuchen
    path = os.path.join(EGON_DATA_DIR, egon_id, filename)

    # v2-Fallback: Wenn v1-Datei nicht existiert, v2-Pfad versuchen
    if not os.path.isfile(path) and filename in V1_TO_V2_FALLBACK:
        path = os.path.join(EGON_DATA_DIR, egon_id, V1_TO_V2_FALLBACK[filename])

    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f'File {filename} does not exist')

    with open(path, 'r', encoding='utf-8') as f:
        return {'egon_id': egon_id, 'filename': filename, 'content': f.read()}


class FileUpdate(BaseModel):
    content: str


@router.put('/egon/{egon_id}/file/{filename}')
async def update_file(egon_id: str, filename: str, body: FileUpdate):
    """Aktualisiere eine .md File."""
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail=f'File {filename} not allowed')

    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(body.content)

    return {'egon_id': egon_id, 'filename': filename, 'status': 'updated'}
