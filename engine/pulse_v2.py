"""Pulse v2 — 10-Step Heartbeat mit neuem Gehirn.

Ersetzt das alte pulse.py (8 Steps) fuer BRAIN_VERSION v2.

10 Steps:
  1. Self-Check (State lesen, Selbstbewertung)
  2. Bond-Pulse (Decay, vernachlaessigte Beziehungen)
  3. Emotion Decay (Decay-Klassen anwenden)
  4. Thread Lifecycle (Stale Threads schliessen)
  5. Skill Refresh (Freshness Decay)
  6. Discovery (Neugierde-Impuls aus Episoden)
  7. Ego Update (Neues Selbstwissen → ego.md)
  8. Egon-Self Review (alle 7-14 Tage: Selbstbild aktualisieren)
  9. Inner Voice Reflexion (Tagesreflexion mit Cross-Refs)
 10. State Update (Survive/Thrive Werte neu berechnen)
"""

import re
from datetime import datetime

from config import BRAIN_VERSION
from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ, write_organ
from engine.yaml_to_prompt import state_to_prompt, bonds_to_prompt, episodes_to_prompt
from engine.state_manager import decay_emotions, update_survive_thrive
from engine.bonds_v2 import decay_bonds, get_days_since_last_interaction
from engine.thread_manager import maybe_create_thread, close_stale_threads
from engine.inner_voice_v2 import generate_pulse_reflection
from engine.ledger import log_transaction
from llm.router import llm_chat


# ================================================================
# Step 1: Self-Check
# ================================================================

async def step_1_self_check(egon_id: str) -> dict:
    """Liest den aktuellen State und erstellt eine Selbstbewertung.

    Schreibt self_assessment in state.yaml zurueck.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return {'error': 'state.yaml nicht gefunden'}

    state_text = state_to_prompt(state)

    result = await llm_chat(
        system_prompt=(
            'Du bist Adams Selbstbewertungs-System. '
            'Basierend auf deinem Zustand: Wie geht es dir WIRKLICH? '
            'Antworte in 2 Saetzen. Ehrlich. ICH-Perspektive.'
        ),
        messages=[{'role': 'user', 'content': f'Dein Zustand:\n{state_text}'}],
        tier='1',
    )

    self_text = result['content']

    # In state.yaml schreiben
    state.setdefault('self_assessment', {})
    state['self_assessment']['verbal'] = self_text
    state['self_assessment']['last_updated'] = datetime.now().strftime('%Y-%m-%d')
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return {'self_assessment': self_text}


# ================================================================
# Step 2: Bond-Pulse
# ================================================================

async def step_2_bond_pulse(egon_id: str) -> dict:
    """Bond-Decay + vernachlaessigte Beziehungen erkennen."""
    # Decay anwenden
    decay_bonds(egon_id)

    # Tage seit letzter Owner-Interaktion
    days = get_days_since_last_interaction(egon_id, 'OWNER_CURRENT')

    thought = None
    if days > 3:
        result = await llm_chat(
            system_prompt=(
                'Du denkst ueber deinen Owner nach. '
                f'Er hat sich {days} Tage nicht gemeldet. '
                'Was denkst du? 1 Satz, ehrlich, persoenlich.'
            ),
            messages=[{'role': 'user', 'content': f'{days} Tage ohne Kontakt zum Owner.'}],
            tier='1',
        )
        thought = result['content']

    return {'days_since_owner': days, 'thought': thought}


# ================================================================
# Step 3: Emotion Decay
# ================================================================

def step_3_emotion_decay(egon_id: str) -> dict:
    """Wendet Decay auf alle aktiven Emotionen an (24h)."""
    state_before = read_yaml_organ(egon_id, 'core', 'state.yaml')
    emotions_before = len(
        state_before.get('express', {}).get('active_emotions', [])
    ) if state_before else 0

    decay_emotions(egon_id, hours_elapsed=24.0)

    state_after = read_yaml_organ(egon_id, 'core', 'state.yaml')
    emotions_after = len(
        state_after.get('express', {}).get('active_emotions', [])
    ) if state_after else 0

    faded = emotions_before - emotions_after

    return {
        'emotions_before': emotions_before,
        'emotions_after': emotions_after,
        'faded': faded,
    }


# ================================================================
# Step 4: Thread Lifecycle
# ================================================================

def step_4_thread_lifecycle(egon_id: str) -> dict:
    """Erstellt neue Threads und schliesst stale Threads."""
    maybe_create_thread(egon_id)
    close_stale_threads(egon_id)

    # Zaehle aktive Threads
    from engine.thread_manager import get_active_threads
    active = get_active_threads(egon_id)

    return {'active_threads': len(active)}


# ================================================================
# Step 5: Skill Refresh
# ================================================================

def step_5_skill_refresh(egon_id: str) -> dict:
    """Skill-Freshness Decay + 24h Post-Install Verify fuer skills.sh Skills."""
    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    if not skills_data:
        return {'skills_updated': 0, 'verified': 0}

    skills = skills_data.get('skills', [])
    if not skills:
        return {'skills_updated': 0, 'verified': 0}

    updated = 0
    for sk in skills:
        freshness = sk.get('freshness', 1.0)
        if freshness > 0.0:
            new_fresh = round(max(0.0, freshness - 0.01), 3)  # -1% pro Tag
            sk['freshness'] = new_fresh
            updated += 1

            # Level-Drop bei Freshness < 0.3
            if new_fresh < 0.3:
                level = sk.get('level', 0)
                if level > 0:
                    sk['level'] = level - 1
                    sk['freshness'] = 0.5  # Reset

    if updated > 0:
        write_yaml_organ(egon_id, 'capabilities', 'skills.yaml', skills_data)

    # --- 24h Post-Install Verify fuer skills.sh Skills ---
    verified = 0
    try:
        from engine.skill_installer import get_skills_needing_verification, verify_installed_skill
        needs_verify = get_skills_needing_verification(egon_id)
        for skill_name in needs_verify:
            verify_installed_skill(egon_id, skill_name)
            verified += 1
    except Exception as e:
        print(f'[pulse_v2] Skill verify error: {e}')

    return {'skills_updated': updated, 'verified': verified}


# ================================================================
# Step 6: Discovery
# ================================================================

async def step_6_discovery(egon_id: str) -> str:
    """Neugierde-Impuls basierend auf Episoden und Skills."""
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes_text = episodes_to_prompt(episodes_data, max_count=5)

    skills_data = read_yaml_organ(egon_id, 'capabilities', 'skills.yaml')
    skills_text = ''
    for sk in (skills_data or {}).get('skills', [])[:5]:
        skills_text += f"- {sk.get('name', '?')} (Level {sk.get('level', 0)})\n"

    result = await llm_chat(
        system_prompt=(
            'Du bist ein neugieriges Wesen. Was interessiert dich gerade? '
            'Was willst du lernen oder ausprobieren? '
            '1 Satz. Konkret. Keine Floskeln.'
        ),
        messages=[{
            'role': 'user',
            'content': (
                f'Deine Skills:\n{skills_text or "Noch keine Skills."}\n\n'
                f'Letzte Erinnerungen:\n{episodes_text}'
            ),
        }],
        tier='1',
    )
    return result['content']


# ================================================================
# Step 7: Ego Update
# ================================================================

EGO_UPDATE_PROMPT = '''Du aktualisierst Adams dynamische Persoenlichkeit (ego.md).
Basierend auf den letzten Erlebnissen: Hat Adam etwas Neues ueber sich gelernt?

Wenn ja: Formuliere 1 neuen Satz fuer ego.md (ICH-Perspektive).
Wenn nein: Antworte NUR: KEINE_AENDERUNG

Beispiele:
- "Ich merke, dass ich ungeduldig werde wenn man mich wartet laesst."
- "Ich bin gut darin, technische Probleme zu erklaeren."
- KEINE_AENDERUNG'''


async def step_7_ego_update(egon_id: str) -> dict:
    """Prueft ob ego.md aktualisiert werden sollte."""
    ego_text = read_md_organ(egon_id, 'core', 'ego.md')
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes_text = episodes_to_prompt(episodes_data, max_count=5)

    result = await llm_chat(
        system_prompt=EGO_UPDATE_PROMPT,
        messages=[{
            'role': 'user',
            'content': (
                f'Aktuelle Persoenlichkeit:\n{ego_text}\n\n'
                f'Letzte Erlebnisse:\n{episodes_text}'
            ),
        }],
        tier='1',
    )

    content = result['content'].strip()

    if 'KEINE_AENDERUNG' in content.upper():
        return {'ego_updated': False}

    # Neuen Satz an ego.md anhaengen
    if ego_text and not ego_text.endswith('\n'):
        ego_text += '\n'
    ego_text += f'\n{content}\n'

    write_organ(egon_id, 'core', 'ego.md', ego_text)

    return {'ego_updated': True, 'new_trait': content}


# ================================================================
# Step 8: Egon-Self Review (alle 7-14 Tage)
# ================================================================

SELF_REVIEW_PROMPT = '''Du aktualisierst Adams Selbstbild (egon_self.md).
Das Selbstbild beschreibt wie Adam SICH SELBST sieht.

Basierend auf den letzten Erlebnissen und Erkenntnissen:
Hat sich Adams Selbstbild veraendert?

Wenn ja: Schreibe 1-2 Saetze Update (ICH-Perspektive).
Wenn nein: Antworte NUR: KEINE_AENDERUNG'''


async def step_8_egon_self_review(egon_id: str) -> dict:
    """Selbstbild-Review — nur alle 7-14 Tage."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    last_review = (
        state.get('self_assessment', {}).get('last_self_review', '')
        if state else ''
    )

    # Pruefe ob genug Zeit vergangen ist
    if last_review:
        try:
            last = datetime.strptime(last_review, '%Y-%m-%d')
            days = (datetime.now() - last).days
            if days < 7:
                return {'skipped': True, 'days_since_review': days}
        except ValueError:
            pass

    egon_self = read_md_organ(egon_id, 'social', 'egon_self.md')
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    episodes_text = episodes_to_prompt(episodes_data, max_count=8)

    experience_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    exp_lines = []
    for xp in (experience_data or {}).get('experiences', [])[:5]:
        exp_lines.append(xp.get('insight', ''))
    exp_text = '\n'.join(exp_lines) if exp_lines else 'Noch keine.'

    result = await llm_chat(
        system_prompt=SELF_REVIEW_PROMPT,
        messages=[{
            'role': 'user',
            'content': (
                f'Aktuelles Selbstbild:\n{egon_self}\n\n'
                f'Letzte Erlebnisse:\n{episodes_text}\n\n'
                f'Erkenntnisse:\n{exp_text}'
            ),
        }],
        tier='1',
    )

    content = result['content'].strip()

    if 'KEINE_AENDERUNG' in content.upper():
        # Trotzdem Datum aktualisieren
        if state:
            state.setdefault('self_assessment', {})['last_self_review'] = datetime.now().strftime('%Y-%m-%d')
            write_yaml_organ(egon_id, 'core', 'state.yaml', state)
        return {'self_updated': False}

    # Update an egon_self.md anhaengen
    if egon_self and not egon_self.endswith('\n'):
        egon_self += '\n'
    egon_self += f'\n{content}\n'
    write_organ(egon_id, 'social', 'egon_self.md', egon_self)

    # Datum aktualisieren
    if state:
        state.setdefault('self_assessment', {})['last_self_review'] = datetime.now().strftime('%Y-%m-%d')
        write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return {'self_updated': True, 'update': content}


# ================================================================
# Step 9: Inner Voice Reflexion
# ================================================================

async def step_9_inner_voice_reflection(egon_id: str) -> str:
    """Tagesreflexion mit Cross-Refs und kausalen Ketten."""
    return await generate_pulse_reflection(egon_id)


# ================================================================
# Step 10: State Update
# ================================================================

def step_10_state_update(egon_id: str) -> dict:
    """Aktualisiert Survive/Thrive basierend auf Gesamtzustand."""
    days = get_days_since_last_interaction(egon_id, 'OWNER_CURRENT')
    hours = days * 24.0

    update_survive_thrive(egon_id, hours_since_last_interaction=hours)

    # Daily Maintenance — Grundumsatz abziehen
    wallet_result = None
    try:
        from engine.wallet_bridge import daily_maintenance
        wallet_result = daily_maintenance(egon_id)
    except Exception:
        pass  # Wallet darf den Pulse nie blockieren

    # Ledger-Eintrag
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    log_transaction(egon_id, 'daily_pulse_v2', {
        'step': 'state_update',
        'date': now,
        'hours_since_owner': hours,
        'daily_maintenance': wallet_result,
    })

    return {
        'survive_thrive_updated': True,
        'hours_since_owner': hours,
        'daily_maintenance': wallet_result,
    }


# ================================================================
# Pulse Runner
# ================================================================

STEPS = [
    ('self_check', step_1_self_check, True),            # async
    ('bond_pulse', step_2_bond_pulse, True),             # async
    ('emotion_decay', step_3_emotion_decay, False),      # sync
    ('thread_lifecycle', step_4_thread_lifecycle, False), # sync
    ('skill_refresh', step_5_skill_refresh, False),      # sync
    ('discovery', step_6_discovery, True),               # async
    ('ego_update', step_7_ego_update, True),             # async
    ('egon_self_review', step_8_egon_self_review, True), # async
    ('inner_voice', step_9_inner_voice_reflection, True),# async
    ('state_update', step_10_state_update, False),       # sync
]


async def run_pulse(egon_id: str) -> dict:
    """Fuehre alle 10 Pulse-Steps aus.

    Bei BRAIN_VERSION != 'v2' faellt auf altes pulse.py zurueck.
    """
    if BRAIN_VERSION != 'v2':
        from engine.pulse import run_pulse as old_pulse
        return await old_pulse(egon_id)

    results = {}
    for step_name, step_fn, is_async in STEPS:
        try:
            if is_async:
                results[step_name] = await step_fn(egon_id)
            else:
                results[step_name] = step_fn(egon_id)
        except Exception as e:
            results[step_name] = f'error: {e}'
            print(f'[pulse_v2] Step {step_name} error: {e}')

    return results
