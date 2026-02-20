"""Profile API — Adams Profil-Daten fuer die App."""

import os
import re
from fastapi import APIRouter
from config import EGON_DATA_DIR
from engine.visibility import get_visible_files

router = APIRouter()


def _read_file(egon_id: str, filename: str) -> str:
    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
    if not os.path.isfile(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _count_entries(content: str) -> int:
    return len([e for e in re.split(r'\n---\n', content) if 'date:' in e])


@router.get('/egon/{egon_id}/profile')
async def get_profile(egon_id: str):
    """Profil-Daten fuer die App (respektiert Sichtbarkeits-Matrix)."""
    visible = get_visible_files('owner_dashboard')

    soul = _read_file(egon_id, 'soul.md') if 'soul.md' in visible else ''
    memory = _read_file(egon_id, 'memory.md') if 'memory.md' in visible else ''
    markers = _read_file(egon_id, 'markers.md') if 'markers.md' in visible else ''
    bonds = _read_file(egon_id, 'bonds.md') if 'bonds.md' in visible else ''
    skills = _read_file(egon_id, 'skills.md') if 'skills.md' in visible else ''

    # Name + ID aus Soul
    name = 'Adam'
    agent_id = '#001'
    name_match = re.search(r'Name:\s*(.+)', soul)
    id_match = re.search(r'ID:\s*(.+)', soul)
    if name_match:
        name = name_match.group(1).strip()
    if id_match:
        agent_id = id_match.group(1).strip()

    # Bond-Score extrahieren
    bond_match = re.search(r'bond_score:\s*([\d.]+)', bonds)
    bond_score = float(bond_match.group(1)) if bond_match else 0.0

    # Aktiver Mood aus Markers
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
        'total_memories': _count_entries(memory),
        'total_markers': _count_entries(markers),
        'skills': skills,
    }
