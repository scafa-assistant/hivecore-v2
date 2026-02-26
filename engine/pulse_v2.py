"""Pulse v2 — 16-Step Heartbeat mit neuem Gehirn.

Ersetzt das alte pulse.py (8 Steps) fuer BRAIN_VERSION v2.

16 Steps:
  1.  Self-Check (State lesen, Selbstbewertung)
  1b. Somatic Gate (Intuitions-Schleife — Patch 1)
  1c. Circadian Check (Phasenuebergang — Patch 2)
  2.  Bond-Pulse (Decay, vernachlaessigte Beziehungen)
  3.  Emotion Decay (Decay-Klassen anwenden)
  4.  Thread Lifecycle (Stale Threads schliessen)
  5.  Skill Refresh (Freshness Decay)
  6.  Discovery (Neugierde-Impuls aus Episoden)
  7.  Ego Update (Neues Selbstwissen → ego.md)
  8.  Egon-Self Review (alle 7-14 Tage: Selbstbild aktualisieren)
  9.  Inner Voice Reflexion (Tagesreflexion + Lobby + Social Maps)
 10.  State Update (Survive/Thrive Werte neu berechnen)
 10b. Resonanz Check (Pairing-Berechnung — Patch 6)
 10c. Inkubation Check (Schwangerschaft + Genesis — Patch 6 Phase 3)
 11.  Dream Generation (Naechtliche Verarbeitung — nur RUHE Phase)
 12.  Spark Check (Konvergierende Erinnerungen → Einsicht)
 13.  Mental Time Travel (Retrospektion/Prospektion — woechentlich)
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
from engine.experience_v2 import generate_dream, maybe_generate_spark, generate_mental_time_travel
from engine.ledger import log_transaction
from llm.router import llm_chat
from engine.somatic_gate import check_somatic_gate, run_decision_gate, execute_autonomous_action
from engine.circadian import check_phase_transition, get_current_phase, update_energy
from engine.resonanz import update_resonanz
from engine.genesis import update_inkubation
from engine.checkpoint import erstelle_checkpoint


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
# Step 1b: Somatic Gate (Patch 1)
# ================================================================

async def step_1b_somatic_gate(egon_id: str) -> dict:
    """Somatic Decision Gate — prueft ob Emotionen Handlungsschwellen ueberschreiten."""
    impulse = check_somatic_gate(egon_id)
    if not impulse:
        return {'gate_triggered': False}

    decision = await run_decision_gate(egon_id, impulse)
    if decision.get('entscheidung') == 'handeln':
        await execute_autonomous_action(egon_id, decision)

    return {
        'gate_triggered': True,
        'marker': impulse.get('marker'),
        'value': impulse.get('value'),
        'entscheidung': decision.get('entscheidung', 'unbekannt'),
    }


# ================================================================
# Step 1c: Circadian Check (Patch 2)
# ================================================================

async def step_1c_circadian(egon_id: str) -> dict:
    """Circadian phase check + transition."""
    phase = get_current_phase(egon_id)
    transition = await check_phase_transition(egon_id)

    result = {'current_phase': phase}
    if transition:
        result['transition'] = transition
    return result


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
    """Tagesreflexion mit Cross-Refs und kausalen Ketten.

    Patch 3: Waehrend DAEMMERUNG auch Lobby reflektieren + Social Maps updaten.
    """
    reflection = await generate_pulse_reflection(egon_id)

    # Patch 3: Lobby reflection + Social Map updates waehrend Daemmerung
    try:
        phase = get_current_phase(egon_id)
        if phase == 'daemmerung':
            from engine.lobby import read_lobby
            from engine.social_mapping import generate_social_map_update
            from engine.organ_reader import read_yaml_organ

            # Bekannte EGONs aus network.yaml lesen
            network = read_yaml_organ(egon_id, 'social', 'network.yaml')
            known_egons = []
            if network:
                for entry in network.get('known_egons', []):
                    if isinstance(entry, dict):
                        kid = entry.get('id', '')
                        if kid and kid != egon_id:
                            known_egons.append(kid)
                    elif isinstance(entry, str) and entry != egon_id:
                        known_egons.append(entry)

            # Lobby-Nachrichten lesen und Social Maps updaten
            lobby_msgs = read_lobby(max_messages=10)
            for other_id in known_egons[:5]:  # Max 5 Maps pro Pulse
                other_msgs = [m for m in lobby_msgs if m.get('from') == other_id]
                if other_msgs:
                    interaction = '\n'.join(
                        f'{m.get("name", m.get("from"))}: {m.get("message")}'
                        for m in other_msgs[-3:]
                    )
                    await generate_social_map_update(
                        egon_id, other_id,
                        f'Lobby-Beobachtung:\n{interaction}',
                    )
    except Exception as e:
        print(f'[pulse_v2] Lobby reflection error: {e}')

    return reflection


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
# Step 10b: Resonanz Check (Patch 6 Phase 2)
# ================================================================

def step_10b_resonanz(egon_id: str) -> dict:
    """Berechnet Resonanz zu allen gegengeschlechtlichen EGONs.

    Reine Mathematik — kein LLM-Aufruf.
    Laeuft nach state_update damit Drives aktuell sind.
    """
    try:
        return update_resonanz(egon_id)
    except Exception as e:
        print(f'[pulse_v2] Resonanz error: {e}')
        return {'error': str(e)}


# ================================================================
# Step 10c: Inkubation Check (Patch 6 Phase 3)
# ================================================================

def step_10c_inkubation(egon_id: str) -> dict:
    """Prueft Inkubation-Fortschritt und triggert Genesis.

    Waehrend Inkubation (112 Tage / 4 Zyklen, Spec Kap. 11.2):
    - Eltern-Drive-Aenderungen (CARE+, PANIC+ bei Mutter; CARE+, SEEKING- bei Vater)
    - Am Ende: execute_genesis() erstellt LIBERO-Agent
    - Netzwerk-Benachrichtigungen (Lobby + Social Mapping)
    """
    try:
        result = update_inkubation(egon_id)
        return result or {'inkubation': False}
    except Exception as e:
        print(f'[pulse_v2] Inkubation error: {e}')
        return {'error': str(e)}


# ================================================================
# Step 11: Dream Generation
# ================================================================

async def step_11_dream_generation(egon_id: str) -> dict:
    """Generiert einen Traum — NUR waehrend RUHE Phase (Patch 2)."""
    try:
        phase = get_current_phase(egon_id)
        if phase != 'ruhe':
            return {'dream_generated': False, 'reason': f'Nicht in RUHE Phase (aktuell: {phase})'}
    except Exception:
        pass  # Wenn Circadian nicht verfuegbar, normal traeumen

    dream = await generate_dream(egon_id)
    if dream:
        return {
            'dream_id': dream.get('id'),
            'type': dream.get('type'),
            'spark_potential': dream.get('spark_potential', False),
            'content_preview': dream.get('content', '')[:80],
        }
    return {'dream_generated': False}


# ================================================================
# Step 12: Spark Check
# ================================================================

async def step_12_spark_check(egon_id: str) -> dict:
    """Prueft ob zwei Erfahrungen zu einer neuen Einsicht konvergieren."""
    spark = await maybe_generate_spark(egon_id)
    if spark:
        return {
            'spark_id': spark.get('id'),
            'insight_preview': spark.get('insight', '')[:80],
            'impact': spark.get('impact'),
        }
    return {'spark_generated': False}


# ================================================================
# Step 13: Mental Time Travel
# ================================================================

async def step_13_mental_time_travel(egon_id: str) -> dict:
    """Generiert eine Retrospektion oder Prospektion (woechentlich)."""
    mtt = await generate_mental_time_travel(egon_id)
    if mtt:
        return {
            'mtt_id': mtt.get('id'),
            'type': mtt.get('type'),
        }
    return {'mtt_generated': False, 'reason': 'Noch nicht faellig oder keine Episoden'}


# ================================================================
# Step 14: Metacognition — Zyklusende-Reflexion (Patch 11)
# ================================================================

async def step_14_metacognition(egon_id: str) -> dict:
    """Metacognition am Zyklusende — tiefe Selbstreflexion (ab Zyklus 8).

    DMN-Aequivalent: Nur wenn der EGON NICHT mit einer Aufgabe beschaeftigt ist.
    Tier 2 LLM-Call, ~400 Tokens.
    """
    try:
        from engine.metacognition import metacognition_zyklusende
        result = await metacognition_zyklusende(egon_id)
        if result:
            return {
                'reflexion': True,
                'stufe': result.get('stufe', '?'),
                'muster_count': result.get('muster_count', 0),
                'reflexion_preview': result.get('reflexion', '')[:100],
            }
        return {'reflexion': False, 'reason': 'Noch nicht reif (Zyklus < 8)'}
    except Exception as e:
        return {'reflexion': False, 'error': str(e)}


# ================================================================
# Step 15: Arbeitsspeicher-Aufraumen + Nacht-Rettung (Patch 13)
# ================================================================

def step_15_arbeitsspeicher_maintenance(egon_id: str) -> dict:
    """Arbeitsspeicher-Decay Maintenance am Zyklusende.

    - Entfernt vergessene Eintraege (R < 0.03)
    - Rettet emotional wichtige Eintraege vor dem Vergessen
    - Patch 10: Dormante Praegungen decay (-0.01/Zyklus)
    """
    result = {}
    try:
        from engine.decay import aufraumen, nacht_rettung
        geloescht = aufraumen(egon_id)
        gerettet = nacht_rettung(egon_id)
        result['geloescht'] = geloescht
        result['gerettet'] = gerettet
    except Exception as e:
        result['arbeitsspeicher_error'] = str(e)

    # Patch 10: Praegung-Zyklus-Decay (dormante Praegungen schwaechen sich ab)
    try:
        from engine.epigenetik import praegung_zyklus_decay
        praeg_decayed = praegung_zyklus_decay(egon_id)
        if praeg_decayed > 0:
            result['praegungen_decayed'] = praeg_decayed
    except Exception as e:
        result['praegung_decay_error'] = str(e)

    # Patch 14: Cue-Index Rebuild am Zyklusende (sicherstellen dass Index aktuell ist)
    try:
        from engine.cue_index import baue_index_auf
        index = baue_index_auf(egon_id)
        if index:
            result['cue_index_eintraege'] = index.get('meta', {}).get('eintraege_total', 0)
    except Exception as e:
        result['cue_index_error'] = str(e)

    # Patch 12: Interaktions-Log Reset (taeglicher Zaehler zuruecksetzen)
    try:
        from engine.multi_egon import interaktions_log_reset
        interaktions_log_reset(egon_id)
    except Exception as e:
        result['interaktions_reset_error'] = str(e)

    # Patch 16: Neuroplastizitaet — Synaptisches Pruning + Regionen-Reset am Zyklusende
    try:
        from engine.neuroplastizitaet import synaptisches_pruning, regionen_nutzung_reset
        pruning_events = synaptisches_pruning(egon_id)
        if pruning_events:
            result['neuroplastizitaet_pruning'] = len(pruning_events)
        regionen_nutzung_reset(egon_id)
    except Exception as e:
        result['neuroplastizitaet_error'] = str(e)

    return result


# ================================================================
# Pulse Runner
# ================================================================

STEPS = [
    ('self_check', step_1_self_check, True),              # async
    ('somatic_gate', step_1b_somatic_gate, True),         # async — Patch 1
    ('circadian', step_1c_circadian, True),               # async — Patch 2
    ('bond_pulse', step_2_bond_pulse, True),              # async
    ('emotion_decay', step_3_emotion_decay, False),       # sync
    ('thread_lifecycle', step_4_thread_lifecycle, False),  # sync
    ('skill_refresh', step_5_skill_refresh, False),       # sync
    ('discovery', step_6_discovery, True),                # async
    ('ego_update', step_7_ego_update, True),              # async
    ('egon_self_review', step_8_egon_self_review, True),  # async
    ('inner_voice', step_9_inner_voice_reflection, True), # async — Patch 3 erweitert
    ('state_update', step_10_state_update, False),        # sync
    ('resonanz', step_10b_resonanz, False),               # sync — Patch 6 Phase 2
    ('inkubation', step_10c_inkubation, False),            # sync — Patch 6 Phase 3
    ('dream_generation', step_11_dream_generation, True), # async — Patch 2 gated
    ('spark_check', step_12_spark_check, True),           # async
    ('mental_time_travel', step_13_mental_time_travel, True),  # async
    ('metacognition', step_14_metacognition, True),              # async — Patch 11
    ('arbeitsspeicher', step_15_arbeitsspeicher_maintenance, False),  # sync — Patch 13
]


async def run_pulse(egon_id: str) -> dict:
    """Fuehre alle 13 Pulse-Steps aus.

    Bei BRAIN_VERSION != 'v2' faellt auf altes pulse.py zurueck.

    Patch 9: Erstellt einen pre_pulse Checkpoint vor der Ausfuehrung.
    Bei kritischem Fehler wird der Checkpoint fuer Rollback genutzt.
    """
    if BRAIN_VERSION != 'v2':
        from engine.pulse import run_pulse as old_pulse
        return await old_pulse(egon_id)

    # Patch 9: Checkpoint vor dem Pulse
    try:
        cp = erstelle_checkpoint(egon_id, 'pre_pulse')
        if cp:
            print(f'[pulse_v2] Checkpoint erstellt: {cp}')
    except Exception as e:
        print(f'[pulse_v2] Checkpoint-Fehler (nicht-fatal): {e}')

    results = {}
    fehler_count = 0
    for step_name, step_fn, is_async in STEPS:
        try:
            if is_async:
                results[step_name] = await step_fn(egon_id)
            else:
                results[step_name] = step_fn(egon_id)
        except Exception as e:
            results[step_name] = f'error: {e}'
            fehler_count += 1
            print(f'[pulse_v2] Step {step_name} error: {e}')

    # Patch 9: Bei zu vielen Fehlern → Rollback
    if fehler_count >= len(STEPS) // 2:
        print(f'[pulse_v2] KRITISCH: {fehler_count}/{len(STEPS)} Steps fehlgeschlagen — Rollback')
        try:
            from engine.checkpoint import rollback
            rollback(egon_id, 'pre_pulse')
            results['_rollback'] = True
        except Exception as e:
            print(f'[pulse_v2] Rollback fehlgeschlagen: {e}')

    return results
