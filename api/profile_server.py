"""Profile API — EGON Profil-Daten fuer die App.

Server-kompatible Version (keine organ_reader Abhaengigkeit).
Liest v1 flat .md Files mit Fallback auf v2 core/ Dateien.
"""

import os
import re
from fastapi import APIRouter
from config import EGON_DATA_DIR
from engine.visibility import get_visible_files

router = APIRouter()


def _read_file(egon_id: str, filename: str) -> str:
    """Lese eine Datei aus dem EGON-Ordner (v1 Root oder v2 Unterordner)."""
    # v1 Pfad (Root)
    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    # v2 Pfad (core/ Unterordner) — fuer dna.md, ego.md
    v2_path = os.path.join(EGON_DATA_DIR, egon_id, 'core', filename)
    if os.path.isfile(v2_path):
        with open(v2_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


@router.get('/egon/{egon_id}/profile')
async def get_profile(egon_id: str):
    """Profil eines EGONs abrufen (Dashboard-Ansicht)."""
    visible = get_visible_files('owner_dashboard')

    soul = _read_file(egon_id, 'soul.md') if 'soul.md' in visible else ''
    # v2 Fallback: dna.md statt soul.md
    if not soul:
        soul = _read_file(egon_id, 'dna.md')

    memory = _read_file(egon_id, 'memory.md') if 'memory.md' in visible else ''
    markers = _read_file(egon_id, 'markers.md') if 'markers.md' in visible else ''
    bonds = _read_file(egon_id, 'bonds.md') if 'bonds.md' in visible else ''
    skills = _read_file(egon_id, 'skills.md') if 'skills.md' in visible else ''

    # Name aus soul.md/dna.md extrahieren, Fallback: aus egon_id ableiten
    name = egon_id.split('_')[0].capitalize() if egon_id else 'Unknown'
    agent_id = egon_id or '#001'
    name_match = re.search(r'Name:\s*(.+)', soul)
    id_match = re.search(r'ID:\s*(.+)', soul)
    if name_match:
        name = name_match.group(1).strip()
    if id_match:
        agent_id = id_match.group(1).strip()

    bond_match = re.search(r'bond_score:\s*([\d.]+)', bonds)
    bond_score = float(bond_match.group(1)) if bond_match else 0.0

    mood = 'neutral'
    marker_types = re.findall(r'type:\s*(\S+)', markers)
    if marker_types:
        mood = marker_types[0]

    return {
        'egon_id': egon_id,
        'name': name,
        'id': agent_id,
        'mood': mood,
        'bond_score': bond_score,
        'skills': skills[:500] if skills else '',
        'version': 'v1',
    }
