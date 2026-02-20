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


@router.get('/egon/{egon_id}/file/{filename}')
async def read_file(egon_id: str, filename: str, context: str = 'owner_dashboard'):
    """Lese eine .md File (respektiert Sichtbarkeits-Matrix)."""
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail=f'File {filename} not found')

    visible = get_visible_files(context)
    if filename not in visible:
        raise HTTPException(status_code=403, detail=f'File {filename} not visible in context {context}')

    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
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
