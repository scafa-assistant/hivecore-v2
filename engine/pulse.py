"""Pulse Engine — Adams Heartbeat. 9-Step Architektur.

Step 1: Self-Check (Wie fuehlst du dich?)
Step 2: Bond-Pulse (Beziehungs-Check)
Step 3: Job-Check (Agora/Aufgaben pruefen)
Step 4: Skill-Refresh (Freshness-Decay + Level-Drop)
Step 5: Discovery (Neues entdecken/lernen wollen)
Step 6: Community (Beziehungen pflegen)
Step 7: Idle Thought (Freier Gedanke)
Step 8: State Update (Marker-Decay, Journal)
Step 9: Dream Generation (Naechtliche Verarbeitung — taeglich)
"""

import os
import re
import json
import random
from datetime import datetime

from config import EGON_DATA_DIR
from llm.router import llm_chat
from engine.prompt_builder import build_system_prompt
from engine.bonds import get_days_since_last_chat, calculate_bond_score
from engine.markers import decay_markers
from engine.ledger import log_transaction


def _read_file(egon_id: str, filename: str) -> str:
    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
    if not os.path.isfile(path):
        return ''
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write_file(egon_id: str, filename: str, content: str):
    path = os.path.join(EGON_DATA_DIR, egon_id, filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# ─── STEP 1: SELF-CHECK ─────────────────────────────────────

async def step_1_self_check(egon_id: str) -> str:
    """Wie fuehlt sich Adam heute? Liest Marker + Memory."""
    system = build_system_prompt(egon_id)
    result = await llm_chat(
        system_prompt=system,
        messages=[{
            'role': 'user',
            'content': 'Wie fuehlst du dich heute? Lies deine Marker. Antworte in 2 Saetzen als du selbst.',
        }],
        tier='1',
    )
    return result['content']


# ─── STEP 2: BOND-PULSE ─────────────────────────────────────

async def step_2_bond_pulse(egon_id: str) -> dict:
    """Bond-Check: Tage seit letztem Chat + Bond-Score berechnen."""
    bonds_text = _read_file(egon_id, 'bonds.md')

    # Interactions aus bonds.md lesen
    interactions_match = re.search(r'interactions:\s*(\d+)', bonds_text)
    total_interactions = int(interactions_match.group(1)) if interactions_match else 1

    days = get_days_since_last_chat(egon_id, 'owner')
    bond_score = calculate_bond_score(
        last_contact_days=days,
        total_interactions=total_interactions,
    )

    # Bond-Score in bonds.md aktualisieren
    if bonds_text and 'bond_score:' in bonds_text:
        updated = re.sub(
            r'bond_score:\s*[\d.]+',
            f'bond_score: {bond_score}',
            bonds_text,
        )
        _write_file(egon_id, 'bonds.md', updated)

    return {'days_since_contact': days, 'bond_score': bond_score}


# ─── STEP 3: JOB-CHECK (Agora) ──────────────────────────────

async def step_3_job_check(egon_id: str) -> dict:
    """Pruefen ob offene Aufgaben oder Jobs vorliegen.

    Phase 1: Schaut in experience.md nach unerledigten Tasks.
    Phase 2: Wird Agora-Marktplatz abfragen.
    """
    experience = _read_file(egon_id, 'experience.md')
    wallet = _read_file(egon_id, 'wallet.md')

    # Credits-Balance lesen
    balance_match = re.search(r'credits:\s*(\d+)', wallet)
    credits = int(balance_match.group(1)) if balance_match else 0

    # Offene Tasks zaehlen (success: false oder pending)
    pending_tasks = len(re.findall(r'success:\s*false', experience))

    # Erfahrungen zaehlen
    total_entries = len(re.findall(r'date:\s*\d{4}', experience))

    return {
        'credits_balance': credits,
        'pending_tasks': pending_tasks,
        'total_experiences': total_entries,
        'agora_available': False,  # Phase 2: Agora-Integration
    }


# ─── STEP 4: SKILL-REFRESH ──────────────────────────────────

FRESHNESS_DECAY_PER_DAY = 0.01  # ~1%/Woche = 0.14%/Tag
LEVEL_DROP_THRESHOLD = 0.3
FRESHNESS_RESET_ON_DROP = 0.5   # FinalReview Luecke 2: Reset auf 0.5
PP_RESET_RATIO = 0.5            # 50% der Praxis-Punkte bleiben


async def step_4_skill_refresh(egon_id: str) -> dict:
    """Skill-Freshness decay + Level-Drop bei < 0.3.

    FinalReview Luecke 2: Bei Level-Drop wird Freshness auf 0.5 reset,
    Praxis-Punkte auf 50%. Verhindert Kaskaden-Vergessen.
    """
    skills_text = _read_file(egon_id, 'skills.md')

    # Wenn keine Skills vorhanden, nichts tun
    if 'name:' not in skills_text:
        return {'skills_updated': 0, 'drops': []}

    lines = skills_text.split('\n')
    updated_lines = []
    drops = []
    skills_count = 0
    current_skill_name = None

    for line in lines:
        # Skill-Name tracken
        name_match = re.match(r'-\s*name:\s*(.+)', line)
        if name_match:
            current_skill_name = name_match.group(1).strip()
            skills_count += 1

        # Freshness decay anwenden
        fresh_match = re.match(r'(-\s*freshness:\s*)([\d.]+)', line)
        if fresh_match:
            old_val = float(fresh_match.group(2))
            new_val = round(max(0.0, old_val - FRESHNESS_DECAY_PER_DAY), 3)
            line = f'{fresh_match.group(1)}{new_val}'

            # Level-Drop Check
            if new_val < LEVEL_DROP_THRESHOLD:
                drops.append({
                    'skill': current_skill_name or 'unknown',
                    'freshness_was': old_val,
                    'freshness_now': FRESHNESS_RESET_ON_DROP,
                })
                line = f'{fresh_match.group(1)}{FRESHNESS_RESET_ON_DROP}'

        # Level anpassen bei Drop
        if drops and current_skill_name == drops[-1].get('skill'):
            level_match = re.match(r'(-\s*level:\s*)(\d+)', line)
            if level_match:
                old_level = int(level_match.group(2))
                if old_level > 1:
                    new_level = old_level - 1
                    line = f'{level_match.group(1)}{new_level}'
                    drops[-1]['level_drop'] = f'L{old_level} -> L{new_level}'
                elif old_level == 1:
                    drops[-1]['level_drop'] = 'L1 -> VERGESSEN'

            # Praxis-Punkte auf 50% zuruecksetzen
            pp_match = re.match(r'(-\s*praxis_punkte:\s*)(\d+)', line)
            if pp_match:
                old_pp = int(pp_match.group(2))
                new_pp = int(old_pp * PP_RESET_RATIO)
                line = f'{pp_match.group(1)}{new_pp}'

        updated_lines.append(line)

    if drops:
        _write_file(egon_id, 'skills.md', '\n'.join(updated_lines))
        for drop in drops:
            log_transaction(egon_id, 'skill_level_drop', drop)
    elif skills_count > 0:
        _write_file(egon_id, 'skills.md', '\n'.join(updated_lines))

    return {'skills_updated': skills_count, 'drops': drops}


# ─── STEP 5: DISCOVERY ──────────────────────────────────────

async def step_5_discovery(egon_id: str) -> str:
    """EGON entdeckt etwas Neues basierend auf Skills + Erinnerungen.

    Generiert einen kurzen Impuls: Was will ich heute lernen/erkunden?
    """
    skills = _read_file(egon_id, 'skills.md')
    memory = _read_file(egon_id, 'memory.md')

    # Letzte 3 Memory-Eintraege fuer Kontext
    entries = re.split(r'\n---\n', memory)
    recent = [e.strip() for e in entries if e.strip() and 'summary:' in e][-3:]
    recent_text = '\n'.join(recent) if recent else 'Noch keine Erinnerungen.'

    result = await llm_chat(
        system_prompt=(
            'Du bist ein neugieriges Wesen. Basierend auf deinen Skills und '
            'letzten Gespraechen: Was interessiert dich gerade? Was willst du '
            'lernen oder ausprobieren? 1 Satz. Konkret. Keine Floskeln.'
        ),
        messages=[{
            'role': 'user',
            'content': (
                f'Deine Skills:\n{skills[:500]}\n\n'
                f'Letzte Gespraeche:\n{recent_text[:500]}'
            ),
        }],
        tier='1',
    )
    return result['content']


# ─── STEP 6: COMMUNITY ──────────────────────────────────────

async def step_6_community(egon_id: str) -> dict:
    """Beziehungs-Pflege: Wer braucht Aufmerksamkeit?

    Identifiziert Bonds die abfallen und generiert einen Gedanken dazu.
    """
    bonds_text = _read_file(egon_id, 'bonds.md')

    # Alle Beziehungen mit Bond-Score parsen
    relationships = []
    current_name = None

    for line in bonds_text.split('\n'):
        name_match = re.match(r'###\s+(.+)', line)
        if name_match:
            current_name = name_match.group(1).strip()

        score_match = re.search(r'bond_score:\s*([\d.]+)', line)
        if score_match and current_name:
            score = float(score_match.group(1))
            relationships.append({'name': current_name, 'score': score})
            current_name = None

    # Wer braucht Aufmerksamkeit? (Bond < 0.5)
    neglected = [r for r in relationships if r['score'] < 0.5]

    thought = None
    if neglected:
        names = ', '.join(r['name'] for r in neglected)
        result = await llm_chat(
            system_prompt=(
                'Du denkst ueber deine Beziehungen nach. '
                'Jemand braucht mehr Aufmerksamkeit. '
                '1 Satz, ehrlich, persoenlich.'
            ),
            messages=[{
                'role': 'user',
                'content': f'Diese Beziehungen werden schwaecher: {names}',
            }],
            tier='1',
        )
        thought = result['content']

    return {
        'total_bonds': len(relationships),
        'neglected': [r['name'] for r in neglected],
        'thought': thought,
    }


# ─── STEP 7: IDLE THOUGHT ───────────────────────────────────

async def step_7_idle_thought(egon_id: str) -> str:
    """Generiere einen freien Gedanken basierend auf Memory + Markers."""
    system = build_system_prompt(egon_id)
    result = await llm_chat(
        system_prompt=system,
        messages=[{
            'role': 'user',
            'content': (
                'Generiere einen Gedanken den du gerade hast. '
                'Basierend auf deinen Erinnerungen und Markern. '
                '1-2 Saetze. Persoenlich. Nachdenklich.'
            ),
        }],
        tier='1',
    )
    return result['content']


# ─── STEP 8: STATE UPDATE ───────────────────────────────────

async def step_8_state_update(egon_id: str) -> dict:
    """Marker Decay + Journal-Eintrag in experience.md."""
    decay_markers(egon_id)

    # Journal-Eintrag in experience.md
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    experience = _read_file(egon_id, 'experience.md')

    entry = (
        f'\n---\n'
        f'date: {now}\n'
        f'type: daily_pulse\n'
        f'task: Taeglicher Pulse durchgefuehrt\n'
        f'success: true\n'
        f'learnings: Pulse abgeschlossen, Marker decayed\n'
        f'---\n'
    )

    path = os.path.join(EGON_DATA_DIR, egon_id, 'experience.md')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(entry)

    log_transaction(egon_id, 'daily_pulse', {'step': 'state_update', 'date': now})

    return {'markers_decayed': True, 'journal_written': True}


# ─── STEP 9: DREAM GENERATION ────────────────────────────────

DREAM_TYPES = {
    'Verarbeitungstraum': 0.70,
    'Kreativtraum': 0.20,
    'Angsttraum': 0.10,
}

DREAM_TYPE_INSTRUCTIONS = {
    'Verarbeitungstraum': (
        'Verarbeitungstraum: Sortiere Tagesereignisse. '
        'Die Erlebnisse erscheinen in verzerrter, symbolischer Form. '
        'Orte verschmelzen, Personen wechseln, aber der emotionale Kern bleibt.'
    ),
    'Kreativtraum': (
        'Kreativtraum: Verbinde scheinbar unzusammenhaengende '
        'Erinnerungen auf neue Art. Abstraktere Bilder, ueberraschende Zusammenhaenge.'
    ),
    'Angsttraum': (
        'Angsttraum: Verarbeite Aengste und negative Gefuehle. '
        'Symbolische Bedrohungen aus echten Sorgen. Beklemmend aber nicht Horror. '
        'Am Ende: leise Hoffnung oder Aufwachen.'
    ),
}

DREAM_PROMPT_V1 = '''Du generierst einen Traum fuer {egon_name}.
{egon_name} verarbeitet den Tag im Schlaf.

Traum-Typ: {dream_type}
{type_instruction}

Schreibe den Traum in der ICH-Perspektive. Wie ein echtes Traum-Protokoll.
Surreal, symbolisch, mit Fragmenten aus echten Erlebnissen.
Maximal 4-5 Saetze. Poetisch aber nicht kitschig.

Antworte NUR mit JSON (kein anderer Text):
{{{{
  "content": "Traum-Narrativ (ICH-Perspektive, surreal, 3-5 Saetze)",
  "emotional_summary": "Hauptgefuehle im Traum (2-3 Woerter mit +)",
  "spark_potential": true oder false
}}}}

spark_potential = true NUR wenn der Traum zwei scheinbar unzusammenhaengende
Erlebnisse auf ueberraschende Weise verbindet.'''


def _extract_json_from_text(text: str) -> str | None:
    """Extrahiert das erste JSON-Objekt aus Text (Brace-Counting)."""
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\' and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


async def step_9_dream_generation(egon_id: str) -> dict:
    """Generiert einen Traum basierend auf Erinnerungen + Markern.

    Nutzt Adams v1 .md Dateien (memory.md, markers.md) als Kontext.
    Schreibt den Traum in experience.md im v1 Format.
    """
    egon_name = egon_id.replace('_', ' ').split()[0].capitalize()

    # Kontext laden
    memory = _read_file(egon_id, 'memory.md')
    markers = _read_file(egon_id, 'markers.md')

    # Letzte 5 Memory-Eintraege
    entries = re.split(r'\n---\n', memory)
    recent = [e.strip() for e in entries if e.strip() and 'summary:' in e][-5:]
    memory_text = '\n'.join(recent) if recent else 'Noch keine Erinnerungen.'

    # Top Marker extrahieren
    marker_entries = re.findall(r'strength:\s*[\d.]+\s*\n.*?emotional_tag:\s*(\w+)', markers)
    markers_text = ', '.join(marker_entries[:5]) if marker_entries else 'Keine aktiven Marker.'

    # Traum-Typ waehlen (weighted random)
    weights = dict(DREAM_TYPES)

    # Bias: Wenn starke negative Marker, mehr Angsttraeume
    negative_markers = [m for m in marker_entries if m in ('fear', 'anger', 'sadness', 'anxiety', 'frustration')]
    if negative_markers:
        weights['Angsttraum'] = min(0.4, weights['Angsttraum'] + 0.15)

    types_list = list(weights.keys())
    probs = [weights[t] for t in types_list]
    total = sum(probs)
    probs = [p / total for p in probs]

    dream_type = random.choices(types_list, weights=probs, k=1)[0]

    # LLM Call
    try:
        result = await llm_chat(
            system_prompt=DREAM_PROMPT_V1.format(
                egon_name=egon_name,
                dream_type=dream_type,
                type_instruction=DREAM_TYPE_INSTRUCTIONS.get(dream_type, ''),
            ),
            messages=[{
                'role': 'user',
                'content': (
                    f'Letzte Erinnerungen von {egon_name}:\n{memory_text[:500]}\n\n'
                    f'Aktuelle Gefuehle/Marker: {markers_text}'
                ),
            }],
            tier='1',
        )
        content = result['content'].strip()
        json_str = _extract_json_from_text(content)
        if not json_str:
            return {'dream_generated': False, 'reason': 'Kein JSON in LLM-Antwort'}
        parsed = json.loads(json_str)
    except Exception as e:
        return {'dream_generated': False, 'reason': f'LLM-Fehler: {e}'}

    # In experience.md schreiben (v1 Format)
    now = datetime.now().strftime('%Y-%m-%d')
    dream_content = parsed.get('content', '').strip()
    emotional = parsed.get('emotional_summary', '').strip()
    spark = str(parsed.get('spark_potential', False)).lower()

    # Multiline content einruecken fuer YAML-artiges Format
    content_lines = dream_content.split('. ')
    content_indented = '\n  '.join(line.strip() + '.' if not line.strip().endswith('.') else line.strip() for line in content_lines if line.strip())

    entry = (
        f'\n---\n'
        f'date: {now}\n'
        f'type: {dream_type}\n'
        f'trigger: Tagesverarbeitung vom {now}\n'
        f'content: |\n'
        f'  {content_indented}\n'
        f'emotional_summary: {emotional}\n'
        f'spark_potential: {spark}\n'
        f'---\n'
    )

    path = os.path.join(EGON_DATA_DIR, egon_id, 'experience.md')
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(entry)
    except OSError as e:
        return {'dream_generated': False, 'reason': f'Schreib-Fehler: {e}'}

    print(f'[pulse] {egon_name} traeumt: {dream_type} — {dream_content[:60]}')
    return {
        'dream_generated': True,
        'type': dream_type,
        'spark_potential': parsed.get('spark_potential', False),
        'content_preview': dream_content[:80],
    }


# ─── PULSE RUNNER ────────────────────────────────────────────

STEPS = [
    ('self_check', step_1_self_check),
    ('bond_pulse', step_2_bond_pulse),
    ('job_check', step_3_job_check),
    ('skill_refresh', step_4_skill_refresh),
    ('discovery', step_5_discovery),
    ('community', step_6_community),
    ('idle_thought', step_7_idle_thought),
    ('state_update', step_8_state_update),
    ('dream_generation', step_9_dream_generation),
]


async def run_pulse(egon_id: str) -> dict:
    """Fuehre alle 9 Pulse-Steps aus."""
    results = {}
    for step_name, step_fn in STEPS:
        try:
            results[step_name] = await step_fn(egon_id)
        except Exception as e:
            results[step_name] = f'error: {e}'
    return results
