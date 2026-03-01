"""Body State Engine — Uebersetzt inneren Zustand in Koerper-Parameter.

Liest state.yaml (Emotionen, Drives, Energy, Mood, Circadian)
und berechnet:
  - body_state: Semantischer Zustand (schlafend, muede, traurig, etc.)
  - behavior_params: Konkrete Steuerparameter fuer die App (Locomotion + NaturalMotion)

FUSION Phase 3 — Server-seitig, wird vom avatar-state Endpoint aufgerufen.
"""

from engine.organ_reader import read_yaml_organ


# ================================================================
# Body State Bestimmung — Prioritaetsbasiert
# ================================================================

def compute_body_state(egon_id: str) -> dict:
    """Berechnet body_state + behavior_params aus state.yaml.

    Returns:
        {
            'body_state': str,
            'behavior_params': dict,
        }
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return _make_result('ruhig')

    # Werte extrahieren
    survive = state.get('survive', {})
    energy_data = survive.get('energy', {})
    energy = energy_data.get('value', 0.5) if isinstance(energy_data, dict) else 0.5

    thrive = state.get('thrive', {})
    mood_data = thrive.get('mood', {})
    mood = mood_data.get('value', 0.5) if isinstance(mood_data, dict) else 0.5

    drives = state.get('drives', {})
    seeking = _drive_val(drives, 'SEEKING')
    play = _drive_val(drives, 'PLAY')
    fear = _drive_val(drives, 'FEAR')
    panic = _drive_val(drives, 'PANIC')

    express = state.get('express', {})
    emotions = express.get('active_emotions', [])
    sadness = _emotion_intensity(emotions, 'sadness')
    grief = _emotion_intensity(emotions, 'grief')

    # Circadian Phase
    zirkadian = state.get('zirkadian', {})
    phase = zirkadian.get('aktuelle_phase', 'aktivitaet')

    # Interaktions-Inaktivitaet
    somatic = state.get('somatic_gate', {})
    letzter_check = somatic.get('letzter_check', '')

    # ── Prioritaets-Kette ──

    # 1. Schlafend: Ruhe-Phase + niedrige Energy
    if phase == 'ruhe' and energy < 0.15:
        return _make_result('schlafend')

    # 2. Muede: Niedrige Energy
    if energy < 0.3:
        return _make_result('muede')

    # 3. Unruhig: Hohe Angst/Panik
    if fear > 0.6 or panic > 0.6:
        return _make_result('unruhig')

    # 4. Traurig: Hohe Traurigkeit/Trauer
    if sadness > 0.5 or grief > 0.5:
        return _make_result('traurig')

    # 5. Freudig: Gute Stimmung + Energie
    if mood > 0.75 and energy > 0.5:
        return _make_result('freudig')

    # 6. Neugierig: Hoher SEEKING-Drive
    if seeking > 0.6:
        return _make_result('neugierig')

    # 7. Verspielt: Hoher PLAY-Drive
    if play > 0.6:
        return _make_result('freudig')

    # 8. Default
    return _make_result('ruhig')


# ================================================================
# Behavior Parameter Profiles
# ================================================================

BEHAVIOR_PROFILES = {
    'schlafend': {
        'walk_speed': 0.0,
        'walk_ratio': 0.0,
        'stand_duration_min': 999,
        'stand_duration_max': 999,
        'breathing_rate': 0.12,
        'posture_offset': 5.0,
        'head_range': 0.5,
        'sway_amplitude': 0.3,
    },
    'muede': {
        'walk_speed': 0.15,
        'walk_ratio': 0.15,
        'stand_duration_min': 15,
        'stand_duration_max': 30,
        'breathing_rate': 0.18,
        'posture_offset': 3.0,
        'head_range': 1.0,
        'sway_amplitude': 0.5,
    },
    'traurig': {
        'walk_speed': 0.2,
        'walk_ratio': 0.2,
        'stand_duration_min': 12,
        'stand_duration_max': 25,
        'breathing_rate': 0.2,
        'posture_offset': 3.0,
        'head_range': 1.0,
        'sway_amplitude': 0.6,
    },
    'unruhig': {
        'walk_speed': 0.5,
        'walk_ratio': 0.6,
        'stand_duration_min': 3,
        'stand_duration_max': 8,
        'breathing_rate': 0.35,
        'posture_offset': -1.0,
        'head_range': 4.0,
        'sway_amplitude': 1.5,
    },
    'neugierig': {
        'walk_speed': 0.35,
        'walk_ratio': 0.45,
        'stand_duration_min': 6,
        'stand_duration_max': 15,
        'breathing_rate': 0.28,
        'posture_offset': -0.5,
        'head_range': 3.5,
        'sway_amplitude': 1.0,
    },
    'freudig': {
        'walk_speed': 0.4,
        'walk_ratio': 0.5,
        'stand_duration_min': 5,
        'stand_duration_max': 12,
        'breathing_rate': 0.3,
        'posture_offset': -1.0,
        'head_range': 3.0,
        'sway_amplitude': 1.2,
    },
    'ruhig': {
        'walk_speed': 0.3,
        'walk_ratio': 0.35,
        'stand_duration_min': 8,
        'stand_duration_max': 20,
        'breathing_rate': 0.25,
        'posture_offset': 0.0,
        'head_range': 2.0,
        'sway_amplitude': 1.0,
    },
}


# ================================================================
# Helpers
# ================================================================

def _drive_val(drives: dict, key: str) -> float:
    """Sicheres Lesen eines Drive-Werts."""
    val = drives.get(key, 0)
    return float(val) if isinstance(val, (int, float)) else 0.0


def _emotion_intensity(emotions: list, etype: str) -> float:
    """Findet die Intensitaet einer bestimmten Emotion."""
    for em in emotions:
        if em.get('type') == etype:
            val = em.get('intensity', 0)
            return float(val) if isinstance(val, (int, float)) else 0.0
    return 0.0


def _make_result(body_state: str) -> dict:
    """Baut das Result-Dict mit body_state + behavior_params."""
    params = BEHAVIOR_PROFILES.get(body_state, BEHAVIOR_PROFILES['ruhig'])
    return {
        'body_state': body_state,
        'behavior_params': dict(params),
    }
