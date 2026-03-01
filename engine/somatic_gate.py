"""Somatic Decision Gate — Intuitions-Schleife.

Uebersetzt emotionale Zustaende in Handlungsimpulse via Schwellenwert-System.
Nach jedem Chat oder Pulse: Pruefen ob Emotion/Drive ueber Schwelle liegt.
Wenn ja → ECR-Kette (WEIL/DESHALB/ALSO) → Decision Gate → handeln/warten/schweigen.
Max 3 autonome Nachrichten pro Stunde.

Wissenschaftliche Basis: Damasio (Somatische Marker), vmPFC, Panksepp.
"""

import json
import re
from datetime import datetime, timedelta
from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ, write_organ
from llm.router import llm_chat


# ================================================================
# Schwellenwert-Profile (DNA-abhaengig)
# ================================================================

DEFAULT_THRESHOLDS = {
    'fear': 0.75,
    'rage': 0.80,
    'care': 0.70,
    'seeking': 0.85,
    'panic': 0.70,
    'grief': 0.60,
    'play': 0.80,
}

# SEEKING/PLAY-dominant — teilt oefter, reagiert gelassener auf Bedrohung
SEEKING_PLAY_THRESHOLDS = {
    'fear': 0.85,
    'rage': 0.80,
    'care': 0.70,
    'seeking': 0.70,
    'panic': 0.80,
    'grief': 0.60,
    'play': 0.70,
}

# CARE/PANIC-dominant — kuemmert sich schneller, reagiert frueher auf Schweigen
CARE_PANIC_THRESHOLDS = {
    'fear': 0.60,
    'rage': 0.80,
    'care': 0.55,
    'seeking': 0.85,
    'panic': 0.50,
    'grief': 0.60,
    'play': 0.80,
}

# Impuls-Typ Mapping
IMPULSE_MAP = {
    'fear': 'SCHUTZ',
    'panic': 'SCHUTZ',
    'rage': 'WIDERSTAND',
    'care': 'FUERSORGE',
    'seeking': 'MITTEILUNG',
    'grief': 'RUECKZUG',
    'play': 'INTERAKTION',
}

MAX_AUTONOMOUS_PER_HOUR = 3


# ================================================================
# Threshold Detection
# ================================================================

def get_thresholds_for_egon(egon_id: str) -> dict:
    """Bestimmt DNA-Profil und gibt angepasste Schwellen zurueck.

    Fix A: Liest zuerst das feste dna_profile Feld aus state.yaml.
    Dieses Feld wird bei Geburt gesetzt und aendert sich NICHT —
    wie echte DNA. Damit kann Drive-Decay das Profil nicht kippen.

    Fallback fuer alte Agents (Adam/Eva): Live-Detection ueber Drives.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return DEFAULT_THRESHOLDS.copy()

    # Fix A: Festes DNA-Profil hat Vorrang (unveraenderlich wie DNA)
    fixed_profile = state.get('dna_profile')
    if fixed_profile == 'SEEKING/PLAY':
        return SEEKING_PLAY_THRESHOLDS.copy()
    elif fixed_profile == 'CARE/PANIC':
        return CARE_PANIC_THRESHOLDS.copy()
    elif fixed_profile:
        return DEFAULT_THRESHOLDS.copy()

    # Fallback: Live-Detection ueber aktuelle Drives (fuer alte Agents)
    drives = state.get('drives', {})
    if not drives:
        return DEFAULT_THRESHOLDS.copy()

    sorted_drives = sorted(
        [(k, v) for k, v in drives.items() if isinstance(v, (int, float))],
        key=lambda x: x[1],
        reverse=True,
    )
    top3_names = {d[0].upper() for d in sorted_drives[:3]}

    if 'SEEKING' in top3_names and 'PLAY' in top3_names:
        return SEEKING_PLAY_THRESHOLDS.copy()
    elif 'CARE' in top3_names or 'PANIC' in top3_names:
        return CARE_PANIC_THRESHOLDS.copy()

    return DEFAULT_THRESHOLDS.copy()


def check_somatic_gate(egon_id: str) -> dict | None:
    """Prueft ob ein Drive oder eine Emotion die Schwelle ueberschreitet.

    Returns:
        dict mit marker, value, threshold, impulse_type wenn Schwelle ueberschritten.
        None wenn keine Schwelle ueberschritten.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None

    # Circadian Phase Check — waehrend RUHE ist das Gate deaktiviert
    # (ausser PANIC > 0.95)
    try:
        from engine.circadian import get_current_phase
        phase = get_current_phase(egon_id)
        if phase == 'ruhe':
            panic_val = state.get('drives', {}).get('PANIC', 0)
            if isinstance(panic_val, (int, float)) and panic_val > 0.95:
                return {
                    'marker': 'panic',
                    'value': panic_val,
                    'threshold': 0.95,
                    'impulse_type': 'SCHUTZ',
                }
            return None
    except ImportError:
        pass  # Circadian nicht installiert — Gate normal ausfuehren

    # Hourly Counter Reset
    _reset_hourly_counter(egon_id, state)

    # Schwellen holen (DNA-abhaengig)
    thresholds = get_thresholds_for_egon(egon_id)

    # Circadian Modifier anwenden (Patch 2)
    try:
        from engine.circadian import get_somatic_modifier
        modifier = get_somatic_modifier(egon_id)
    except ImportError:
        modifier = 1.0

    adjusted = {k: min(1.0, v * modifier) for k, v in thresholds.items()}

    # Drives pruefen
    drives = state.get('drives', {})
    highest_marker = None
    highest_value = 0
    highest_threshold = 0

    drive_to_gate = {
        'FEAR': 'fear',
        'RAGE': 'rage',
        'CARE': 'care',
        'SEEKING': 'seeking',
        'PANIC': 'panic',
        'GRIEF': 'grief',
        'PLAY': 'play',
    }

    for drive_key, gate_key in drive_to_gate.items():
        val = drives.get(drive_key, 0)
        if not isinstance(val, (int, float)):
            continue
        thresh = adjusted.get(gate_key, 1.0)
        if val > thresh and val > highest_value:
            highest_marker = gate_key
            highest_value = val
            highest_threshold = thresh

    # Auch aktive Emotionen pruefen
    express = state.get('express', {})
    emotions = express.get('active_emotions', [])
    for em in emotions:
        etype = em.get('type', '')
        intensity = em.get('intensity', 0)
        if not isinstance(intensity, (int, float)):
            continue
        # Emotionstyp auf Gate-Key mappen
        gate_key = etype if etype in adjusted else None
        if gate_key and intensity > adjusted.get(gate_key, 1.0) and intensity > highest_value:
            highest_marker = gate_key
            highest_value = intensity
            highest_threshold = adjusted.get(gate_key, 1.0)

    if highest_marker:
        impulse = {
            'marker': highest_marker,
            'value': round(highest_value, 3),
            'threshold': round(highest_threshold, 3),
            'impulse_type': IMPULSE_MAP.get(highest_marker, 'MITTEILUNG'),
        }
        _update_somatic_state(egon_id, state, impulse, None)

        try:
            from engine.neuroplastizitaet import ne_emit
            ne_emit(egon_id, 'IMPULS', 'amygdala', 'hypothalamus', label=f'Somatischer Marker: {impulse.get("marker", "?")}', intensitaet=0.6, animation='flash')
        except Exception:
            pass

        return impulse

    # Keine Schwelle ueberschritten
    _update_somatic_state(egon_id, state, None, None)
    return None


# ================================================================
# Decision Gate — LLM-basierte Entscheidung
# ================================================================

GATE_PROMPT = '''Du bist das somatische Entscheidungstor von {egon_name}.
Ein Impuls hat die Schwelle ueberschritten.

Marker: {marker} = {value} (Schwelle: {threshold})
Impuls-Typ: {impulse_type}

Durchlaufe die ECR-Kette:
1. WEIL: Warum ist dieser Impuls so stark? (basierend auf deinem Zustand)
2. DESHALB: Was bedeutet das fuer dich?
3. ALSO: Was solltest du tun?

Entscheide: handeln | warten | schweigen

Antworte NUR mit JSON:
{{
  "weil": "Grund (1 Satz, ICH-Perspektive)",
  "deshalb": "Schlussfolgerung (1 Satz)",
  "also": "Konsequenz (1 Satz)",
  "entscheidung": "handeln|warten|schweigen",
  "nachricht": "Was du sagen wuerdest (nur bei handeln, sonst leer)"
}}'''


async def run_decision_gate(egon_id: str, impulse: dict) -> dict:
    """LLM-Call fuer die ECR-Kette und Entscheidung.

    Spam-Schutz: Max 3 autonome Nachrichten pro Stunde.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    gate = (state or {}).get('somatic_gate', {})
    msg_count = gate.get('autonome_nachrichten_diese_stunde', 0)

    if msg_count >= MAX_AUTONOMOUS_PER_HOUR:
        decision = {
            'weil': f'{impulse["marker"]} ist bei {impulse["value"]}',
            'deshalb': 'Ich wuerde gerne reagieren',
            'also': 'Aber ich habe schon zu oft gesprochen',
            'entscheidung': 'warten',
            'nachricht': '',
        }
        _update_somatic_state(egon_id, state, impulse, decision)
        return decision

    from engine.naming import get_display_name
    egon_name = get_display_name(egon_id)

    # Kontext: aktueller Zustand + letzte Inner Voice
    from engine.yaml_to_prompt import state_to_prompt
    state_text = state_to_prompt(state) if state else 'Kein Zustand verfuegbar.'
    inner_voice = read_md_organ(egon_id, 'memory', 'inner_voice.md') or ''
    # Nur letzten Eintrag
    entries = inner_voice.split('\n## ')
    last_thought = entries[-1][:200] if entries else ''

    try:
        result = await llm_chat(
            system_prompt=GATE_PROMPT.format(
                egon_name=egon_name,
                marker=impulse['marker'],
                value=impulse['value'],
                threshold=impulse['threshold'],
                impulse_type=impulse['impulse_type'],
            ),
            messages=[{
                'role': 'user',
                'content': (
                    f'Dein Zustand:\n{state_text[:400]}\n\n'
                    f'Letzter Gedanke:\n{last_thought}'
                ),
            }],
        )

        content = result['content'].strip()
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group())
        else:
            decision = {
                'entscheidung': 'schweigen',
                'weil': 'Konnte nicht klar denken',
                'deshalb': '',
                'also': '',
                'nachricht': '',
            }
    except Exception as e:
        print(f'[somatic_gate] Decision gate error: {e}')
        decision = {
            'entscheidung': 'schweigen',
            'weil': f'Fehler: {e}',
            'deshalb': '',
            'also': '',
            'nachricht': '',
        }

    _update_somatic_state(egon_id, state, impulse, decision)
    return decision


# ================================================================
# Autonomous Action Execution
# ================================================================

async def execute_autonomous_action(egon_id: str, decision: dict) -> None:
    """Fuehrt eine autonome Aktion aus (schreibt Inner Voice, optional Nachricht).

    Wird NUR aufgerufen wenn decision['entscheidung'] == 'handeln'.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    # Inner Voice Eintrag schreiben
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    weil = decision.get('weil', '')
    deshalb = decision.get('deshalb', '')
    also_ = decision.get('also', '')
    nachricht = decision.get('nachricht', '')

    thought = (
        f'## Autonomer Impuls — {now}\n\n'
        f'WEIL {weil}\n'
        f'DESHALB {deshalb}\n'
        f'ALSO {also_}\n'
    )
    if nachricht:
        thought += f'\nIch sage: "{nachricht}"\n'

    # An inner_voice.md anhaengen
    inner_voice = read_md_organ(egon_id, 'memory', 'inner_voice.md') or ''
    if inner_voice and not inner_voice.endswith('\n'):
        inner_voice += '\n'
    inner_voice += f'\n{thought}\n'
    write_organ(egon_id, 'memory', 'inner_voice.md', inner_voice)

    # FUSION Phase 3: Motor-Impuls basierend auf Impuls-Typ
    motor_impulse = _compute_motor_impulse(decision)
    if motor_impulse:
        # Motor Translation: words → bone-Rotationen (gleiche Pipeline wie Chat)
        try:
            from engine.motor_translator import translate as motor_translate
            bone_update = motor_translate(motor_impulse)
            if bone_update:
                state['pending_motor_action'] = bone_update
                print(f'[somatic_gate] {egon_id}: Motor-Impuls: {bone_update.get("words", [])}')
        except Exception as e:
            print(f'[somatic_gate] Motor-Translation FEHLER: {e}')

    # Counter erhoehen
    gate = state.get('somatic_gate', {})
    gate['autonome_nachrichten_diese_stunde'] = gate.get('autonome_nachrichten_diese_stunde', 0) + 1
    state['somatic_gate'] = gate
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    print(f'[somatic_gate] {egon_id}: Autonomer Impuls ausgefuehrt — {decision.get("entscheidung")}')


# ================================================================
# FUSION Phase 3: Motor-Impulse aus Entscheidungen
# ================================================================

# Impuls-Typ → passende Motor-Woerter (aus motor_vocabulary.json)
IMPULSE_MOTOR_MAP = {
    'SCHUTZ': {'words': ['aengstlich'], 'intensity': 0.6},
    'WIDERSTAND': {'words': ['wuetend_stehen'], 'intensity': 0.7},
    'FUERSORGE': {'words': ['kopf_neigen'], 'intensity': 0.5},
    'MITTEILUNG': {'words': ['hand_heben'], 'intensity': 0.5},
    'RUECKZUG': {'words': ['traurig_stehen'], 'intensity': 0.6},
    'INTERAKTION': {'words': ['winken'], 'intensity': 0.6},
}


def _compute_motor_impulse(decision: dict) -> dict | None:
    """Berechnet einen Motor-Impuls aus der Somatic-Gate-Entscheidung.

    Nur bei 'handeln' — und nur wenn ein passender Motor-Typ existiert.
    Returns bone_update-kompatibles Dict oder None.
    """
    if decision.get('entscheidung') != 'handeln':
        return None

    # Impuls-Typ aus dem Gate-Kontext (wird von check_somatic_gate gesetzt)
    # Leider hat decision keinen impulse_type — wir leiten ihn ab
    weil = decision.get('weil', '').lower()
    also_ = decision.get('also', '').lower()

    # Heuristik: Aus Entscheidungstext den passenden Motor-Typ waehlen
    for impulse_type, motor in IMPULSE_MOTOR_MAP.items():
        key = impulse_type.lower()
        if key in weil or key in also_:
            return {
                'words': motor['words'],
                'intensity': motor['intensity'],
                'source': 'somatic_gate',
            }

    # Fallback: Subtile Geste (Kopfdrehen — "ich schaue mich um")
    return {
        'words': ['kopf_drehen_rechts'],
        'intensity': 0.4,
        'source': 'somatic_gate',
    }


# ================================================================
# State Management Helpers
# ================================================================

def _reset_hourly_counter(egon_id: str, state: dict) -> None:
    """Setzt den Stunden-Zaehler zurueck wenn > 1h seit letztem Check."""
    gate = state.get('somatic_gate', {})
    last_check_str = gate.get('letzter_check')

    if last_check_str:
        try:
            last_check = datetime.fromisoformat(str(last_check_str))
            if datetime.now() - last_check > timedelta(hours=1):
                gate['autonome_nachrichten_diese_stunde'] = 0
        except (ValueError, TypeError):
            gate['autonome_nachrichten_diese_stunde'] = 0
    else:
        gate['autonome_nachrichten_diese_stunde'] = 0

    state['somatic_gate'] = gate


def _update_somatic_state(
    egon_id: str,
    state: dict | None,
    impulse: dict | None,
    decision: dict | None,
) -> None:
    """Schreibt den somatic_gate Block in state.yaml zurueck."""
    if not state:
        state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    now = datetime.now()
    gate = state.get('somatic_gate', {})

    gate['letzter_check'] = now.strftime('%Y-%m-%dT%H:%M:%S')
    gate['naechster_check'] = (now + timedelta(minutes=15)).strftime('%Y-%m-%dT%H:%M:%S')

    if impulse:
        gate['hoechster_marker'] = impulse.get('marker')
        gate['hoechster_wert'] = impulse.get('value', 0)
        gate['schwelle_ueberschritten'] = True
        gate['impuls_typ'] = impulse.get('impulse_type')
    else:
        gate['hoechster_marker'] = None
        gate['hoechster_wert'] = 0
        gate['schwelle_ueberschritten'] = False
        gate['impuls_typ'] = None

    if decision:
        gate['entscheidung'] = decision.get('entscheidung')
        gate['grund'] = decision.get('weil', '')
    else:
        gate['entscheidung'] = None
        gate['grund'] = None

    state['somatic_gate'] = gate
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)
