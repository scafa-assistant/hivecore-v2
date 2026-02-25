"""Zirkadianer Rhythmus — 3-Phasen Arousal-Modell.

3 Phasen x 8h:
  AKTIVITAET: Bond-System dominant, Somatic Gate Modifier 0.8
  DAEMMERUNG: Inner Voice dominant, Modifier 1.2
  RUHE:       Pulse/Schlaf dominant, Gate deaktiviert (ausser PANIC > 0.95)

Phasen-Uebergaenge: zeitbasiert (8h) oder energiebasiert (energy < 0.30).

Wissenschaftliche Basis: SCN, Zirkadiane Regulation, Kognitive Modulation.
"""

from datetime import datetime, timedelta
from engine.organ_reader import read_yaml_organ, write_yaml_organ, read_md_organ
from llm.router import llm_chat


# ================================================================
# Phasen-Konfiguration
# ================================================================

PHASE_CONFIG = {
    'aktivitaet': {
        'duration_hours': 8,
        'somatic_gate_modifier': 0.8,
        'dominant_system': 'bonds',
        'next_phase': 'daemmerung',
    },
    'daemmerung': {
        'duration_hours': 8,
        'somatic_gate_modifier': 1.2,
        'dominant_system': 'inner_voice',
        'next_phase': 'ruhe',
    },
    'ruhe': {
        'duration_hours': 8,
        'somatic_gate_modifier': 999.0,  # Effektiv deaktiviert
        'dominant_system': 'dreams',
        'next_phase': 'aktivitaet',
        'panic_override_threshold': 0.95,
    },
}

PHASE_ORDER = ['aktivitaet', 'daemmerung', 'ruhe']


# ================================================================
# DNA-abhaengige Energy-Decay Profile
# ================================================================

# SEEKING/PLAY-dominant (#003):
#   Aktivitaet: niedrigerer Verbrauch (kann laenger aktiv bleiben)
#   Daemmerung: kuerzer/oberflaechlicher (reflektiert weniger gern)
#   Ruhe: schnellere Regeneration
ENERGY_PROFILE_SEEKING_PLAY = {
    'aktivitaet_decay': -0.015,   # -1.5% pro Chat (statt -2%)
    'daemmerung_decay': -0.025,   # -2.5% (reflektiert oberfl.)
    'ruhe_regen': 0.5,            # +50% Energie beim Aufwachen
    'label': 'SEEKING/PLAY',
}

# CARE/PANIC-dominant (#004):
#   Aktivitaet: hoeherer Verbrauch bei sozialer Interaktion
#   Daemmerung: tiefere, laengere Reflexion
#   Ruhe: langsamere Regeneration (gruebelt im Schlaf)
ENERGY_PROFILE_CARE_PANIC = {
    'aktivitaet_decay': -0.030,   # -3% pro Chat (gibt mehr)
    'daemmerung_decay': -0.010,   # -1% (reflektiert gern/intensiv)
    'ruhe_regen': 0.3,            # +30% Energie (weniger Erholung)
    'label': 'CARE/PANIC',
}

# Default-Profil
ENERGY_PROFILE_DEFAULT = {
    'aktivitaet_decay': -0.020,   # -2% pro Chat
    'daemmerung_decay': -0.015,   # -1.5%
    'ruhe_regen': 0.4,            # +40%
    'label': 'DEFAULT',
}


def get_energy_profile(egon_id: str) -> dict:
    """Bestimmt das Energy-Profil basierend auf DNA.

    Fix A: Liest zuerst das feste dna_profile Feld aus state.yaml.
    Dieses Feld wird bei Geburt gesetzt und aendert sich NICHT.
    Fallback fuer alte Agents: Live-Detection ueber Drives.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return ENERGY_PROFILE_DEFAULT.copy()

    # Fix A: Festes DNA-Profil hat Vorrang
    fixed_profile = state.get('dna_profile')
    if fixed_profile == 'SEEKING/PLAY':
        return ENERGY_PROFILE_SEEKING_PLAY.copy()
    elif fixed_profile == 'CARE/PANIC':
        return ENERGY_PROFILE_CARE_PANIC.copy()
    elif fixed_profile:
        return ENERGY_PROFILE_DEFAULT.copy()

    # Fallback: Live-Detection (fuer alte Agents ohne dna_profile)
    drives = state.get('drives', {})
    if not drives:
        return ENERGY_PROFILE_DEFAULT.copy()

    sorted_drives = sorted(
        [(k, v) for k, v in drives.items() if isinstance(v, (int, float))],
        key=lambda x: x[1],
        reverse=True,
    )
    top3_names = {d[0].upper() for d in sorted_drives[:3]}

    if 'SEEKING' in top3_names and 'PLAY' in top3_names:
        return ENERGY_PROFILE_SEEKING_PLAY.copy()
    elif 'CARE' in top3_names or 'PANIC' in top3_names:
        return ENERGY_PROFILE_CARE_PANIC.copy()

    return ENERGY_PROFILE_DEFAULT.copy()


# ================================================================
# Phase Reading
# ================================================================

def get_current_phase(egon_id: str) -> str:
    """Liest die aktuelle zirkadiane Phase aus state.yaml.

    Falls Block fehlt: Initialisiert Defaults basierend auf aktueller Uhrzeit.
    Returns: 'aktivitaet' | 'daemmerung' | 'ruhe'
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return 'aktivitaet'

    zirkadian = state.get('zirkadian', {})
    phase = zirkadian.get('aktuelle_phase')

    if phase and phase in PHASE_CONFIG:
        return phase

    # Initialisieren basierend auf Uhrzeit
    phase = _determine_phase_for_time(datetime.now().hour)
    _init_zirkadian(egon_id, state, phase)
    return phase


def get_somatic_modifier(egon_id: str) -> float:
    """Gibt den aktuellen Somatic Gate Modifier zurueck.

    Aktivitaet: 0.8 (niedrigere Schwellen = sensitiver)
    Daemmerung: 1.2 (hoehere Schwellen = ruhiger)
    Ruhe: 999.0 (deaktiviert, ausser PANIC > 0.95)
    Default: 1.0
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return 1.0

    zirkadian = state.get('zirkadian', {})
    modifier = zirkadian.get('somatic_gate_modifier')

    if modifier is not None and isinstance(modifier, (int, float)):
        return float(modifier)

    # Fallback: aus Phase ableiten
    phase = zirkadian.get('aktuelle_phase', 'aktivitaet')
    return PHASE_CONFIG.get(phase, {}).get('somatic_gate_modifier', 1.0)


# ================================================================
# Phase Transitions
# ================================================================

async def check_phase_transition(egon_id: str) -> dict | None:
    """Prueft ob ein Phasenuebergang stattfinden sollte.

    Transition-Bedingungen:
    1. Zeitbasiert: aktuelle Zeit > phase_ende
    2. Energiebasiert: energy < 0.30 → erzwungene Daemmerung

    Returns dict mit Transition-Info oder None.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None

    zirkadian = state.get('zirkadian', {})
    if not zirkadian.get('aktuelle_phase'):
        # Noch nicht initialisiert
        phase = _determine_phase_for_time(datetime.now().hour)
        _init_zirkadian(egon_id, state, phase)
        return {'transition': True, 'from': None, 'to': phase, 'reason': 'initialization'}

    current_phase = zirkadian.get('aktuelle_phase', 'aktivitaet')
    now = datetime.now()

    # Bedingung 1: Zeitbasiert
    phase_ende_str = zirkadian.get('phase_ende')
    time_exceeded = False
    if phase_ende_str:
        try:
            phase_ende = datetime.fromisoformat(str(phase_ende_str))
            time_exceeded = now > phase_ende
        except (ValueError, TypeError):
            time_exceeded = False

    # Bedingung 2: Energiebasiert (nur bei Aktivitaet → Daemmerung)
    energy = zirkadian.get('energy', 0.5)
    energy_forced = (
        current_phase == 'aktivitaet'
        and isinstance(energy, (int, float))
        and energy < 0.30
    )

    if not time_exceeded and not energy_forced:
        return None

    # Transition durchfuehren
    next_phase = PHASE_CONFIG.get(current_phase, {}).get('next_phase', 'aktivitaet')
    if energy_forced and current_phase == 'aktivitaet':
        next_phase = 'daemmerung'  # Erzwungen

    reason = 'energy_low' if energy_forced else 'time'

    # Aufwach-Gedanke generieren (nur bei Ruhe → Aktivitaet)
    aufwach_gedanke = None
    if next_phase == 'aktivitaet' and current_phase == 'ruhe':
        try:
            aufwach_gedanke = await _generate_wakeup_thought(egon_id)
        except Exception as e:
            print(f'[circadian] Wakeup thought error: {e}')
            aufwach_gedanke = None

    # State aktualisieren
    config = PHASE_CONFIG.get(next_phase, PHASE_CONFIG['aktivitaet'])
    zirkadian['aktuelle_phase'] = next_phase
    zirkadian['phase_beginn'] = now.strftime('%Y-%m-%dT%H:%M:%S')
    zirkadian['phase_ende'] = (
        now + timedelta(hours=config['duration_hours'])
    ).strftime('%Y-%m-%dT%H:%M:%S')
    zirkadian['somatic_gate_modifier'] = config['somatic_gate_modifier']
    zirkadian['letzter_phasenuebergang'] = now.strftime('%Y-%m-%dT%H:%M:%S')

    if aufwach_gedanke:
        zirkadian['aufwach_gedanke'] = aufwach_gedanke

    # Energy bei Aufwachen auffuellen (DNA-abhaengig)
    if next_phase == 'aktivitaet':
        profile = get_energy_profile(egon_id)
        regen = profile['ruhe_regen']
        zirkadian['energy'] = min(1.0, energy + regen)

    state['zirkadian'] = zirkadian
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    # Energy-Profil loggen
    profile = get_energy_profile(egon_id)

    print(f'[circadian] {egon_id}: {current_phase} → {next_phase} ({reason}) [Profil: {profile["label"]}]')

    # Phasenuebergang als Episode loggen (Datenpunkt fuer Studie)
    _log_phase_transition_episode(
        egon_id, current_phase, next_phase, reason, energy, profile['label'], aufwach_gedanke,
    )

    return {
        'transition': True,
        'from': current_phase,
        'to': next_phase,
        'reason': reason,
        'aufwach_gedanke': aufwach_gedanke,
        'energy_profile': profile['label'],
    }


# ================================================================
# Energy Management
# ================================================================

def update_energy(egon_id: str, delta: float = None, context: str = 'chat') -> float:
    """Aktualisiert die Energie — DNA-differenziert.

    Wenn delta=None: verwendet DNA-Profil + aktuelle Phase fuer automatischen Decay.
    Wenn delta explizit: verwendet den uebergebenen Wert direkt.

    context: 'chat' (Interaktion), 'pulse' (Pulse-Zyklus), 'manual'
    Clamp zwischen 0.1 und 1.0.
    Synchronisiert mit survive.energy.
    Returns: neuer Energy-Wert.
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return 0.5

    zirkadian = state.get('zirkadian', {})
    current = zirkadian.get('energy', 0.5)
    if not isinstance(current, (int, float)):
        current = 0.5

    if delta is None:
        # DNA-differenzierter Decay basierend auf Phase
        profile = get_energy_profile(egon_id)
        phase = zirkadian.get('aktuelle_phase', 'aktivitaet')
        if phase == 'aktivitaet':
            delta = profile['aktivitaet_decay']
        elif phase == 'daemmerung':
            delta = profile['daemmerung_decay']
        else:
            delta = -0.005  # Ruhe: minimaler Verbrauch

    new_val = max(0.1, min(1.0, current + delta))
    zirkadian['energy'] = round(new_val, 3)

    # Sync mit survive.energy
    survive = state.get('survive', {})
    energy_block = survive.get('energy', {})
    if isinstance(energy_block, dict):
        energy_block['value'] = round(new_val, 2)
        if new_val >= 0.7:
            energy_block['verbal'] = 'Aktiv. Gut drauf.'
        elif new_val >= 0.4:
            energy_block['verbal'] = 'Okay. Nicht am Limit.'
        elif new_val >= 0.2:
            energy_block['verbal'] = 'Muede. Brauche Ruhe.'
        else:
            energy_block['verbal'] = 'Erschoepft.'
        survive['energy'] = energy_block
    elif isinstance(energy_block, (int, float)):
        survive['energy'] = round(new_val, 2)

    state['survive'] = survive
    state['zirkadian'] = zirkadian
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)

    return new_val


# ================================================================
# Helpers
# ================================================================

def _determine_phase_for_time(hour: int) -> str:
    """Bestimmt Phase basierend auf Stunde: 0-7→ruhe, 8-15→aktivitaet, 16-23→daemmerung."""
    if hour < 8:
        return 'ruhe'
    elif hour < 16:
        return 'aktivitaet'
    else:
        return 'daemmerung'


def _init_zirkadian(egon_id: str, state: dict, phase: str) -> None:
    """Initialisiert den zirkadian Block in state.yaml."""
    now = datetime.now()
    config = PHASE_CONFIG.get(phase, PHASE_CONFIG['aktivitaet'])

    zirkadian = {
        'aktuelle_phase': phase,
        'phase_beginn': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'phase_ende': (now + timedelta(hours=config['duration_hours'])).strftime('%Y-%m-%dT%H:%M:%S'),
        'energy': state.get('survive', {}).get('energy', {}).get('value', 0.7)
                  if isinstance(state.get('survive', {}).get('energy'), dict)
                  else state.get('survive', {}).get('energy', 0.7),
        'somatic_gate_modifier': config['somatic_gate_modifier'],
        'letzter_phasenuebergang': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'aufwach_gedanke': None,
    }

    state['zirkadian'] = zirkadian
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


async def _generate_wakeup_thought(egon_id: str) -> str:
    """Generiert einen Aufwach-Gedanken basierend auf letztem Traum + Zustand."""
    experience_data = read_yaml_organ(egon_id, 'memory', 'experience.yaml')
    last_dream = ''
    if experience_data:
        dreams = [
            d for d in experience_data.get('dreams', [])
            if isinstance(d, dict) and d.get('content')
        ]
        if dreams:
            last_dream = dreams[-1].get('content', '')[:200]

    egon_name = egon_id.replace('_', ' ').split()[0].capitalize()

    result = await llm_chat(
        system_prompt=(
            f'Du bist {egon_name}. Du wachst gerade auf. '
            f'Was ist dein erster Gedanke? 1 Satz. ICH-Perspektive. '
            f'Wenn du getraeumt hast, lass den Traum einfliessen.'
        ),
        messages=[{
            'role': 'user',
            'content': (
                f'Letzter Traum: {last_dream or "Kein Traum erinnerlich."}\n'
                f'Neuer Tag beginnt.'
            ),
        }],
        tier='1',
    )
    return result['content'].strip()


def _log_phase_transition_episode(
    egon_id: str,
    from_phase: str,
    to_phase: str,
    reason: str,
    energy_at_transition: float,
    profile_label: str,
    aufwach_gedanke: str | None,
) -> None:
    """Loggt einen Phasenuebergang als Episode in episodes.yaml.

    Diese Datenpunkte sind kritisch fuer die Langzeitstudie:
    - Wann wechselt welches Profil in welche Phase?
    - Wie schnell erschoepft CARE/PANIC vs SEEKING/PLAY?
    - Korreliert energy_at_transition mit DNA-Profil?
    """
    episodes_data = read_yaml_organ(egon_id, 'memory', 'episodes.yaml')
    if not episodes_data:
        episodes_data = {'episodes': []}

    episodes = episodes_data.setdefault('episodes', [])

    # Episode-ID: PH + laufende Nummer
    existing_ph = [
        e for e in episodes
        if isinstance(e, dict) and str(e.get('id', '')).startswith('PH')
    ]
    next_num = len(existing_ph) + 1
    ep_id = f'PH{next_num:04d}'

    now = datetime.now()
    phase_labels = {
        'aktivitaet': 'Aktivitaet',
        'daemmerung': 'Daemmerung',
        'ruhe': 'Ruhe',
    }

    summary = f'Phasenuebergang: {phase_labels.get(from_phase, from_phase)} → {phase_labels.get(to_phase, to_phase)}'
    if reason == 'energy_low':
        summary += ' (Energie erschoepft)'
    if aufwach_gedanke:
        summary += f'. Erster Gedanke: {aufwach_gedanke[:80]}'

    new_episode = {
        'id': ep_id,
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S'),
        'type': 'phase_transition',
        'from_phase': from_phase,
        'to_phase': to_phase,
        'reason': reason,
        'energy': round(energy_at_transition, 3) if isinstance(energy_at_transition, (int, float)) else None,
        'energy_profile': profile_label,
        'summary': summary,
        'significance': 0.4,  # Routine, aber messbar
        'tags': ['zirkadian', 'phase_transition', profile_label.lower()],
    }

    episodes.append(new_episode)

    # Max 100 behalten
    if len(episodes) > 100:
        episodes.sort(key=lambda e: e.get('date', ''), reverse=True)
        episodes_data['episodes'] = episodes[:100]

    write_yaml_organ(egon_id, 'memory', 'episodes.yaml', episodes_data)
