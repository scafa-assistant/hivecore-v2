"""Profile API — Adams Profil-Daten fuer die App.

v2: Liest aus 5-Schichten-Organ-Struktur statt flat .md Files.
v1 Fallback: Altes Verhalten fuer BRAIN_VERSION=v1.
"""

import os
import re
from fastapi import APIRouter
from config import EGON_DATA_DIR, BRAIN_VERSION
from engine.organ_reader import read_yaml_organ, read_md_organ, list_contact_cards

router = APIRouter()


# ================================================================
# v1: Altes Profile (flat .md Files)
# ================================================================

def _read_file(egon_id: str, filename: str) -> str:
    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
    if not os.path.isfile(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _count_entries(content: str) -> int:
    return len([e for e in re.split(r'\n---\n', content) if 'date:' in e])


def _build_profile_v1(egon_id: str) -> dict:
    """Altes Profile aus flat .md Files."""
    from engine.visibility import get_visible_files
    visible = get_visible_files('owner_dashboard')

    soul = _read_file(egon_id, 'soul.md') if 'soul.md' in visible else ''
    memory = _read_file(egon_id, 'memory.md') if 'memory.md' in visible else ''
    markers = _read_file(egon_id, 'markers.md') if 'markers.md' in visible else ''
    bonds = _read_file(egon_id, 'bonds.md') if 'bonds.md' in visible else ''
    skills = _read_file(egon_id, 'skills.md') if 'skills.md' in visible else ''

    name = 'Adam'
    agent_id = '#001'
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
        'total_memories': _count_entries(memory),
        'total_markers': _count_entries(markers),
        'skills': skills,
    }


# ================================================================
# v2: Neues Profile aus 5-Schichten-Organen
# ================================================================

def _build_profile_v2(egon_id: str) -> dict:
    """Profil aus der neuen 5-Schichten-Organ-Struktur."""
    # Core: Identity + State
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')

    # Social: Bonds + Network
    bonds = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
    network = read_yaml_organ(egon_id, 'social', 'network.yaml')

    # Memory: Episodes
    episodes = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')

    # Capabilities: Skills + Wallet
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    wallet = read_yaml_organ(egon_id, 'capabilities', 'wallet.yaml')

    # Contacts
    contacts = list_contact_cards(egon_id, 'active')

    # Owner Info aus Network
    owner_info = network.get('owner', {})
    owner_name = owner_info.get('name', 'Unbekannt')

    # Mood aus State
    mood = 'neutral'
    thrive = state.get('thrive', {})
    mood_entry = thrive.get('mood', {})
    mood_value = mood_entry.get('value', 0.5)
    if mood_value > 0.7:
        mood = 'gut drauf'
    elif mood_value > 0.4:
        mood = 'okay'
    elif mood_value > 0.2:
        mood = 'gedrueckt'
    else:
        mood = 'schlecht'

    # Aktive Emotionen
    express = state.get('express', {})
    active_emotions = express.get('active_emotions', [])
    if active_emotions:
        top_emotion = active_emotions[0]
        mood = top_emotion.get('type', mood)

    # Bond Score (Owner Bond)
    bond_list = bonds.get('bonds', [])
    owner_bond = None
    for b in bond_list:
        if b.get('id') == 'OWNER_CURRENT':
            owner_bond = b
            break
    bond_score = owner_bond.get('score', 0) if owner_bond else 0.0

    # Counts
    ep_list = episodes.get('episodes', [])
    total_episodes = len(ep_list) if isinstance(ep_list, list) else 0
    total_emotions = len(active_emotions)

    # Skills Summary
    skill_list = skills_data.get('skills', [])
    skills_summary = []
    for sk in skill_list:
        skills_summary.append({
            'name': sk.get('name', '?'),
            'level': sk.get('level', 0),
            'max_level': sk.get('max_level', 5),
        })

    # Survive/Thrive Values
    survive = state.get('survive', {})
    energy = survive.get('energy', {}).get('value', 0.5)
    safety = survive.get('safety', {}).get('value', 0.5)
    belonging = thrive.get('belonging', {}).get('value', 0.5)
    trust = thrive.get('trust_owner', {}).get('value', 0.5)

    # Drives
    drives = state.get('drives', {})
    active_drives = {
        k: v for k, v in drives.items()
        if isinstance(v, (int, float)) and v > 0.3
    }

    # Name aus dna.md lesen
    dna = read_md_organ(egon_id, 'core', 'dna.md')
    name = 'Unknown'
    agent_id = egon_id
    import re as _re
    name_match = _re.search(r'Name:\s*(.+)', dna)
    id_match = _re.search(r'ID:\s*(.+)', dna)
    if name_match:
        name = name_match.group(1).strip()
    if id_match:
        agent_id = id_match.group(1).strip()

    # Skills als Text fuer die App
    skills_text = ', '.join(sk.get('name', '?') for sk in skill_list) if skill_list else ''

    return {
        'egon_id': egon_id,
        'name': name,
        'id': agent_id,
        'owner_name': owner_name,
        'mood': mood,
        'bond_score': bond_score,
        # App-kompatible Felder
        'total_memories': total_episodes,
        'total_markers': total_emotions,
        'active_markers': total_emotions,
        'skills_count': len(skill_list),
        'skills': skills_text,
        # v2 erweiterte Felder
        'total_episodes': total_episodes,
        'total_emotions': total_emotions,
        'total_contacts': len(contacts),
        'skills_detail': skills_summary,
        'wallet_balance': wallet.get('balance', 0),
        'wallet_currency': wallet.get('currency', 'EGON Credits'),
        'vitals': {
            'energy': energy,
            'safety': safety,
            'belonging': belonging,
            'trust_owner': trust,
            'mood_value': mood_value,
        },
        'drives': active_drives,
        'self_assessment': state.get('self_assessment', {}).get('verbal', ''),
    }


# ================================================================
# Endpoint: Dispatched nach BRAIN_VERSION
# ================================================================

@router.get('/egon/{egon_id}/profile')
async def get_profile(egon_id: str):
    """Profil-Daten fuer die App (respektiert Sichtbarkeits-Matrix)."""
    if BRAIN_VERSION == 'v2':
        return _build_profile_v2(egon_id)
    else:
        return _build_profile_v1(egon_id)
