"""Thalamus-Gate — Relevanzfilter vor dem Post-Processing (Patch 8).

Der Thalamus sitzt zwischen Konversationsende und Post-Processing.
Er entscheidet in ~130 Tokens welcher Verarbeitungspfad gewaehlt wird:

  A_MINIMAL  (Relevanz < 0.3) — 3 Schritte,  ~200 Tokens
  B_SOZIAL   (0.3-0.7, sozial) — 6 Schritte, ~700 Tokens
  C_EMOTIONAL(0.3-0.7, emotional) — 7 Schritte, ~900 Tokens
  D_BURST    (> 0.7 oder Krise) — 10 Schritte, ~1200 Tokens

Zwei Modi:
  1. Forced Triggers (regelbasiert, kein LLM)
  2. LLM-Scan (Tier 1, ~130 Tokens)

Biologische Analogie:
  Der biologische Thalamus filtert ~90% des sensorischen Inputs.
  Nur ~10% erreicht das Bewusstsein. Ohne Filter: Ueberflutung.
  (Sherman & Guillery, 2006; Saalmann & Kastner, 2011)
"""

import json
import re
from datetime import date, datetime

from engine.organ_reader import read_yaml_organ, write_yaml_organ
from llm.router import llm_chat


# ================================================================
# DNA-abhaengige Burst-Schwellen
# ================================================================

DNA_BURST_SCHWELLEN = {
    'SEEKING/PLAY': {'burst_threshold': 0.75, 'emotional_shift': 0.35},
    'CARE/PANIC':   {'burst_threshold': 0.65, 'emotional_shift': 0.20},
    'RAGE/FEAR':    {'burst_threshold': 0.70, 'emotional_shift': 0.25},
    'DEFAULT':      {'burst_threshold': 0.70, 'emotional_shift': 0.30},
}


# ================================================================
# Pfad → Post-Processing-Schritte
# ================================================================

PFAD_SCHRITTE = {
    'A_MINIMAL': {
        'summary', 'recent_memory', 'circadian',
    },
    'B_SOZIAL': {
        'summary', 'emotion', 'drives', 'recent_memory',
        'episode', 'social_mapping', 'circadian', 'formatting',
    },
    'C_EMOTIONAL': {
        'summary', 'emotion', 'drives', 'recent_memory',
        'episode', 'experience', 'somatic_gate', 'circadian', 'formatting',
    },
    'D_BURST': {
        'summary', 'emotion', 'drives', 'bond', 'episode', 'experience',
        'owner_portrait', 'contact_manager', 'somatic_gate', 'circadian',
        'recent_memory', 'social_mapping', 'formatting',
    },
}


# NeuroMap-Intensitaeten pro Pfad
PFAD_INTENSITAET = {
    'A_MINIMAL':   0.15,
    'B_SOZIAL':    0.35,
    'C_EMOTIONAL': 0.55,
    'D_BURST':     0.85,
}


# ================================================================
# Burst-Keywords (Case-Insensitive Regex)
# ================================================================

BURST_KEYWORDS = [
    r'\btod\b', r'\bsterben\b', r'\bgestorben\b', r'\btot\b',
    r'\bverlust\b', r'\bnie\s+wieder\b',
    r'\bliebe\b', r'\bhasse\b', r'\blieb', r'\bhass',
    r'\bf[uü]r\s+immer\b', r'\bversprechen\b', r'\bversprochen\b',
    r'\bwer\s+bin\s+ich\b', r'\bmein\s+sinn\b', r'\bmein\s+zweck\b',
    r'\bsuizid\b', r'\bselbstmord\b', r'\bumbringen\b',
    r'\bscheidung\b', r'\btrennung\b',
    r'\bgeboren\b', r'\bschwanger\b',
]
BURST_PATTERN = re.compile('|'.join(BURST_KEYWORDS), re.IGNORECASE)


# ================================================================
# Thalamus System-Prompt (Tier 1)
# ================================================================

THALAMUS_SYSTEM = (
    'Du bist der Thalamus — der Relevanzfilter eines EGONs. '
    'Bewerte die letzte Konversation in einem einzigen JSON-Block. '
    'Keine Erklaerung. Nur JSON.'
)


# ================================================================
# Forced Trigger Checks (regelbasiert, kein LLM)
# ================================================================

def check_forced_triggers(
    egon_id: str,
    messages: list[dict],
    conversation_type: str = 'owner_chat',
    partner_id: str | None = None,
) -> str | None:
    """Regelbasierte Forced-Trigger Checks — kein LLM noetig.

    Returns:
        'burst'   — Erzwungener Burst-Modus
        'minimal' — Erzwungener Minimal-Modus
        None      — Kein Forced-Trigger → LLM-Gate noetig
    """

    # ------ FORCED MINIMAL ------

    user_messages = [m for m in messages if m.get('role') == 'user']
    last_msg = user_messages[-1]['content'] if user_messages else ''

    # < 2 User-Nachrichten UND kein Burst-Keyword → minimal
    if len(user_messages) < 2:
        # Aber: Burst-Keywords override auch bei kurzen Gespraechen
        if last_msg and BURST_PATTERN.search(last_msg):
            return 'burst'
        # Kurze Begruessung ohne Inhalt (max 3 Woerter)
        if len(last_msg.split()) <= 3:
            return 'minimal'

    # ------ FORCED BURST ------

    # Keyword-Check in letzten Nachrichten (User + EGON)
    letzte_texte = ' '.join(
        m.get('content', '') for m in messages[-6:]
        if m.get('role') in ('user', 'assistant')
    )
    if BURST_PATTERN.search(letzte_texte):
        return 'burst'

    # Partner ist neu (erster Kontakt) → Burst
    if partner_id:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
        if bonds_data:
            bond = _find_bond_in_data(bonds_data, partner_id)
            if not bond:
                return 'burst'  # Kein Bond = erster Kontakt
            # Eltern-Kind Bond → immer Burst
            bond_typ = bond.get('bond_typ', bond.get('typ', ''))
            if bond_typ in ('eltern_kind', 'kind_eltern'):
                return 'burst'

    # Thalamus-Historie: >= 3 Burst heute → anhaltende Krise
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    thalamus = state.get('thalamus', {}) if state else {}
    forced_burst_count = thalamus.get('forced_burst_count_heute', 0)
    if forced_burst_count >= 3:
        return 'burst'

    return None  # → LLM-Gate wird benoetigt


# ================================================================
# LLM-basierter Thalamus-Scan (Tier 1)
# ================================================================

async def thalamus_scan(
    egon_id: str,
    messages: list[dict],
    partner_id: str | None = None,
) -> dict:
    """Tier 1 LLM-Call: Schnelle Relevanz-Bewertung.

    Input:  ~80 Tokens (Ego-Kurzprofil + Zustand + Partner + letzte 3 Msgs)
    Output: ~50 Tokens (JSON)
    Gesamt: ~130 Tokens

    Returns:
        dict mit relevanz, routing, prioritaet
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')

    # Ego-Einzeiler
    ego_kurz = _build_ego_einzeiler(egon_id, state)

    # Staerkstes emotionales System
    drives = state.get('drives', {}) if state else {}
    if drives:
        staerkstes = max(
            drives.items(),
            key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
        )
        zustand_str = f'{staerkstes[0]}={staerkstes[1]:.2f}'
    else:
        zustand_str = 'neutral=0.50'

    # Partner-Info
    partner_name = partner_id or 'owner'
    bond_staerke = 0.0
    if partner_id:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
        if bonds_data:
            bond = _find_bond_in_data(bonds_data, partner_id)
            if bond:
                bond_staerke = bond.get('score', bond.get('staerke', 0.0))
                # Normalisiere auf 0-1 wenn score 0-100 ist
                if isinstance(bond_staerke, (int, float)) and bond_staerke > 1:
                    bond_staerke = bond_staerke / 100.0

    # Letzte Nachrichten (gekuerzt, max 400 Zeichen)
    letzte = messages[-6:] if len(messages) > 6 else messages
    letzte_str = '\n'.join(
        f'{m["role"]}: {m["content"][:80]}'
        for m in letzte
        if m.get('role') in ('user', 'assistant')
    )[-400:]

    prompt = (
        f'EGO: {ego_kurz}\n'
        f'ZUSTAND: {zustand_str}\n'
        f'PARTNER: {partner_name} (Bond: {bond_staerke:.2f})\n'
        f'LETZTE NACHRICHTEN:\n{letzte_str}\n\n'
        f'Bewerte als JSON:\n'
        f'{{"relevanz":0.0-1.0,"routing":{{"emotional":bool,"sozial":bool,'
        f'"identitaet":bool,"erinnerung":bool,"krise":bool}},'
        f'"prioritaet":"niedrig"|"mittel"|"hoch"|"burst"}}'
    )

    try:
        response = await llm_chat(
            system_prompt=THALAMUS_SYSTEM,
            messages=[{'role': 'user', 'content': prompt}],
            tier='1',
            egon_id=egon_id,
        )
        text = response['content'].strip()

        # JSON extrahieren (manchmal wrapped in ```json...```)
        json_match = re.search(
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL,
        )
        if json_match:
            data = json.loads(json_match.group())
            return _normalize_gate_output(data)

        return _normalize_gate_output(json.loads(text))

    except (json.JSONDecodeError, Exception) as e:
        print(f'[thalamus] LLM-Scan Fehler: {e}')
        # Fallback: Im Zweifel HOCH (lieber zu viel als zu wenig)
        return {
            'relevanz': 0.8,
            'routing': {
                'emotional': True, 'sozial': True,
                'identitaet': False, 'erinnerung': False,
                'krise': False,
            },
            'prioritaet': 'hoch',
        }


# ================================================================
# Pfad-Bestimmung
# ================================================================

def bestimme_pfad(thalamus_output: dict, dna_profile: str = 'DEFAULT') -> str:
    """Aus dem Thalamus-Gate-Output den Verarbeitungspfad bestimmen.

    DNA-abhaengige Burst-Schwellen:
      SEEKING/PLAY: 0.75 (toleranter)
      CARE/PANIC:   0.65 (sensitiver)
      RAGE/FEAR:    0.70 (mittel)
      DEFAULT:      0.70 (Standard)
    """
    rel = thalamus_output.get('relevanz', 0.5)
    routing = thalamus_output.get('routing', {})
    prio = thalamus_output.get('prioritaet', 'mittel')

    schwellen = DNA_BURST_SCHWELLEN.get(
        dna_profile, DNA_BURST_SCHWELLEN['DEFAULT'],
    )
    burst_threshold = schwellen['burst_threshold']

    # BURST ueberschreibt alles
    if prio == 'burst' or rel > burst_threshold + 0.10 or routing.get('krise'):
        return 'D_BURST'

    # Ueber Burst-Schwelle → Burst
    if rel > burst_threshold:
        return 'D_BURST'

    # Niedrig: Minimal
    if rel < 0.3 and prio == 'niedrig':
        return 'A_MINIMAL'

    # Mittel: Welcher Pfad dominiert?
    aktive_routen = [k for k, v in routing.items() if v]

    # Identitaet → immer Burst
    if 'identitaet' in aktive_routen:
        return 'D_BURST'

    # Emotional UND sozial → Burst
    if 'emotional' in aktive_routen and 'sozial' in aktive_routen:
        return 'D_BURST'

    if 'emotional' in aktive_routen:
        return 'C_EMOTIONAL'

    if 'sozial' in aktive_routen:
        return 'B_SOZIAL'

    # Default: Standard (= SOZIAL)
    return 'B_SOZIAL'


# ================================================================
# Validierung des Thalamus-Outputs
# ================================================================

def validiere_thalamus_output(
    output: dict,
    conversation_type: str = 'owner_chat',
    partner_id: str | None = None,
    egon_id: str | None = None,
) -> dict:
    """Konsistenz-Checks: Korrigiert Widersprueche im Gate-Output.

    Regeln:
    - Krise erkannt aber niedrige Relevanz → hochsetzen
    - Hohe Relevanz aber kein Routing → emotional setzen
    - Owner → mindestens mittel
    - Erster Kontakt → Burst
    """
    routing = output.get('routing', {})

    # Krise erkannt aber niedrige Relevanz?
    if routing.get('krise') and output.get('relevanz', 0.5) < 0.7:
        output['relevanz'] = 0.85
        output['prioritaet'] = 'burst'

    # Hohe Relevanz aber kein Routing?
    if output.get('relevanz', 0.5) > 0.7 and not any(routing.values()):
        output['routing']['emotional'] = True

    # Partner ist Owner → mindestens mittel (aber Krise ueberschreibt nicht)
    if conversation_type == 'owner_chat' and output.get('relevanz', 0.5) < 0.4:
        output['relevanz'] = 0.4
        output['prioritaet'] = 'mittel'

    # Erster Kontakt → Burst
    if partner_id and egon_id:
        bonds_data = read_yaml_organ(egon_id, 'social', 'bonds.yaml')
        if bonds_data:
            bond = _find_bond_in_data(bonds_data, partner_id)
            if not bond:
                output['relevanz'] = 0.9
                output['prioritaet'] = 'burst'
                output['routing']['sozial'] = True

    return output


# ================================================================
# State Update — Thalamus-Block in state.yaml
# ================================================================

def update_thalamus_state(egon_id: str, pfad: str, relevanz: float) -> None:
    """Schreibt den Thalamus-Block in state.yaml.

    Trackt: letzter_pfad, letzte_relevanz, pfad_historie_heute,
    forced_burst_count_heute. Tages-Reset bei neuem Datum.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    thalamus = state.get('thalamus', {})

    # Tages-Reset
    heute = date.today().isoformat()
    letzter_tag = thalamus.get('letzter_tag', '')
    if letzter_tag != heute:
        thalamus['pfad_historie_heute'] = {
            'A_MINIMAL': 0, 'B_SOZIAL': 0,
            'C_EMOTIONAL': 0, 'D_BURST': 0,
        }
        thalamus['forced_burst_count_heute'] = 0
        thalamus['letzter_tag'] = heute

    # Update
    thalamus['letzter_pfad'] = pfad
    thalamus['letzte_relevanz'] = round(relevanz, 3)

    historie = thalamus.get('pfad_historie_heute', {
        'A_MINIMAL': 0, 'B_SOZIAL': 0,
        'C_EMOTIONAL': 0, 'D_BURST': 0,
    })
    historie[pfad] = historie.get(pfad, 0) + 1
    thalamus['pfad_historie_heute'] = historie

    if pfad == 'D_BURST':
        thalamus['forced_burst_count_heute'] = (
            thalamus.get('forced_burst_count_heute', 0) + 1
        )

    state['thalamus'] = thalamus
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


# ================================================================
# Haupt-Entry-Point
# ================================================================

async def thalamus_gate(
    egon_id: str,
    messages: list[dict],
    conversation_type: str = 'owner_chat',
    partner_id: str | None = None,
) -> dict:
    """Haupt-Entry-Point: Bestimmt den Verarbeitungspfad.

    Aufgerufen am Ende jeder Konversation VOR dem Post-Processing.
    Bestimmt welche Post-Processing-Schritte ausgefuehrt werden.

    Ablauf:
    1. Forced-Trigger-Check (regelbasiert, kein LLM)
    2. LLM-Scan (Tier 1, ~130 Tokens)
    3. Validierung
    4. Pfad-Bestimmung (DNA-abhaengig)
    5. State-Update

    Returns:
        dict: {
            'pfad': 'A_MINIMAL' | 'B_SOZIAL' | 'C_EMOTIONAL' | 'D_BURST',
            'schritte': set of step names,
            'relevanz': float (0.0-1.0),
            'gate_output': dict | None (raw thalamus output),
            'intensitaet': float (fuer NeuroMap),
        }
    """
    # Pulse / Nachtverarbeitung: Kein Gate — immer volle Verarbeitung
    if conversation_type == 'pulse':
        return {
            'pfad': 'D_BURST',
            'schritte': PFAD_SCHRITTE['D_BURST'],
            'relevanz': 1.0,
            'gate_output': None,
            'intensitaet': 0.85,
        }

    # 1. Forced-Trigger Check (kein LLM)
    forced = check_forced_triggers(
        egon_id, messages, conversation_type, partner_id,
    )

    if forced == 'burst':
        update_thalamus_state(egon_id, 'D_BURST', 0.9)
        return {
            'pfad': 'D_BURST',
            'schritte': PFAD_SCHRITTE['D_BURST'],
            'relevanz': 0.9,
            'gate_output': {'forced': True, 'trigger': 'burst'},
            'intensitaet': 0.85,
        }

    if forced == 'minimal':
        update_thalamus_state(egon_id, 'A_MINIMAL', 0.1)
        return {
            'pfad': 'A_MINIMAL',
            'schritte': PFAD_SCHRITTE['A_MINIMAL'],
            'relevanz': 0.1,
            'gate_output': {'forced': True, 'trigger': 'minimal'},
            'intensitaet': 0.15,
        }

    # 2. LLM-basiertes Gate (Tier 1)
    gate_output = await thalamus_scan(egon_id, messages, partner_id)

    # 3. Validierung
    gate_output = validiere_thalamus_output(
        gate_output, conversation_type, partner_id, egon_id,
    )

    # 4. DNA-Profil laden
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    dna_profile = state.get('dna_profile', 'DEFAULT') if state else 'DEFAULT'

    # 5. Pfad bestimmen
    pfad = bestimme_pfad(gate_output, dna_profile)
    relevanz = gate_output.get('relevanz', 0.5)

    # 6. State updaten
    update_thalamus_state(egon_id, pfad, relevanz)

    print(
        f'[thalamus] {egon_id}: Pfad={pfad} Relevanz={relevanz:.2f} '
        f'Routing={gate_output.get("routing", {})}'
    )

    return {
        'pfad': pfad,
        'schritte': PFAD_SCHRITTE[pfad],
        'relevanz': relevanz,
        'gate_output': gate_output,
        'intensitaet': PFAD_INTENSITAET.get(pfad, 0.35),
    }


# ================================================================
# Convenience: Pruefen ob ein Schritt laufen soll
# ================================================================

def soll_schritt_laufen(thalamus_result: dict | None, schritt_name: str) -> bool:
    """Prueft ob ein bestimmter Post-Processing-Schritt laufen soll.

    Usage in chat.py:
        gate = await thalamus_gate(egon_id, history, ...)
        if soll_schritt_laufen(gate, 'emotion'):
            await update_emotion_after_chat(...)
    """
    if thalamus_result is None:
        return True  # Kein Gate → alles laufen lassen (Fallback)
    return schritt_name in thalamus_result.get('schritte', set())


# ================================================================
# Helper
# ================================================================

def _find_bond_in_data(bonds_data: dict, partner_id: str) -> dict | None:
    """Sucht einen Bond in bonds.yaml Daten."""
    for bond in bonds_data.get('bonds', []):
        if bond.get('id') == partner_id:
            return bond
    return None


def _build_ego_einzeiler(egon_id: str, state: dict | None) -> str:
    """Baut ein Ego-Kurzprofil (~15 Tokens) fuer den Thalamus-Scan."""
    if not state:
        return egon_id

    identitaet = state.get('identitaet', {})
    name = identitaet.get(
        'anzeigename', identitaet.get('vorname', egon_id),
    )

    # Top-2-Drives als Persoenlichkeits-Hint
    drives = state.get('drives', {})
    if drives:
        numeric_drives = {
            k: v for k, v in drives.items()
            if isinstance(v, (int, float))
        }
        if numeric_drives:
            top = sorted(
                numeric_drives.items(), key=lambda x: x[1], reverse=True,
            )[:2]
            drive_hint = '/'.join(d[0] for d in top)
            return f'{name} ({drive_hint})'

    return name


def _normalize_gate_output(data: dict) -> dict:
    """Normalisiert den LLM-Output auf konsistentes Format.

    Stellt sicher: relevanz ist float, routing ist dict of bool,
    prioritaet ist einer der 4 erlaubten Werte.
    """
    # Relevanz
    rel = data.get('relevanz', 0.5)
    if isinstance(rel, str):
        try:
            rel = float(rel)
        except ValueError:
            rel = 0.5
    data['relevanz'] = max(0.0, min(1.0, float(rel)))

    # Routing — sicherstellen dass alle Keys existieren
    routing = data.get('routing', {})
    if not isinstance(routing, dict):
        routing = {}
    for key in ('emotional', 'sozial', 'identitaet', 'erinnerung', 'krise'):
        if key not in routing:
            routing[key] = False
        elif not isinstance(routing[key], bool):
            routing[key] = bool(routing[key])
    data['routing'] = routing

    # Prioritaet
    prio = data.get('prioritaet', data.get('priorität', 'mittel'))
    if prio not in ('niedrig', 'mittel', 'hoch', 'burst'):
        prio = 'mittel'
    data['prioritaet'] = prio

    return data
