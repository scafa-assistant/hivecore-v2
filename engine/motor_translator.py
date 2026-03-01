"""Motor Translator — uebersetzt Motor-Woerter in Bone-Rotationen.

Nimmt die geparsete ###BODY### Daten (words + intensity) und
schlaegt die Bone-Rotationen in motor_vocabulary.json nach.

Output: bone_update dict — bereit fuer die App (skeletalRenderer.ts).
"""

import json
import os
from typing import Optional


def _normalize_umlauts(word: str) -> str:
    """Normalisiert deutsche Umlaute zu ASCII-Ersetzungen.

    Das LLM generiert manchmal Umlaute (kopf_schütteln) obwohl
    motor_vocabulary.json ASCII nutzt (kopf_schuetteln).
    Fix fuer BUG-010: Umlaut-Mismatch body.md vs vocabulary.
    """
    return (word
            .replace('ü', 'ue').replace('ö', 'oe')
            .replace('ä', 'ae').replace('ß', 'ss')
            .replace('Ü', 'Ue').replace('Ö', 'Oe').replace('Ä', 'Ae'))

# Motor-Vocabulary einmalig laden (Singleton)
_vocab_cache: Optional[dict] = None
_VOCAB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config', 'motor_vocabulary.json',
)


def _load_vocab() -> dict:
    """Laedt motor_vocabulary.json (cached)."""
    global _vocab_cache
    if _vocab_cache is None:
        try:
            with open(_VOCAB_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _vocab_cache = data.get('motor_vocabulary', {}).get('words', {})
        except Exception:
            _vocab_cache = {}
    return _vocab_cache


def reload_vocab() -> None:
    """Erzwingt Neuladen des Vocabularys (z.B. nach Hot-Reload)."""
    global _vocab_cache
    _vocab_cache = None


def translate(body_data: dict) -> Optional[dict]:
    """Uebersetzt geparsete Body-Daten in ein bone_update dict.

    Zwei Modi:
    1. WORD-MODUS (gelernt): {"words": ["nicken"], "intensity": 0.7}
       → Vocabulary-Lookup → vordefinierte Bone-Rotationen
    2. FREIER MODUS (direkt): {"bones": {"head": {"rx": -15}}, "intensity": 0.7}
       → EGON steuert Gelenke direkt, kein Vocabulary noetig
    3. HYBRID: {"words": ["stehen"], "bones": {"head": {"ry": -25}}, "intensity": 0.7}
       → Words werden uebersetzt, dann bones draufgelegt

    Args:
        body_data: Body-Dict mit "words" und/oder "bones"

    Returns:
        bone_update dict oder None bei Fehler.
    """
    if not body_data:
        return None

    has_words = isinstance(body_data.get('words'), list)
    has_bones = isinstance(body_data.get('bones'), dict)

    if not has_words and not has_bones:
        return None

    intensity = body_data.get('intensity', 0.5)
    reason = body_data.get('reason', '')
    # Wort-Aliase: LLM sagt "schlafen" → Motor spielt "hinlegen_schlafen"
    WORD_ALIASES = {
        'schlafen': 'hinlegen_schlafen',
        'aufwachen': 'aufstehen',
    }

    animations = []

    # 1. Word-Modus: Vocabulary-Lookup (wie bisher)
    if has_words:
        vocab = _load_vocab()
        for word in body_data['words']:
            normalized = _normalize_umlauts(word)
            normalized = WORD_ALIASES.get(normalized, normalized)
            spec = vocab.get(normalized)
            if not spec:
                print(f'[motor] WARNUNG: Unbekanntes Wort "{word}" (normalisiert: "{normalized}")')
                continue

            anim = {
                'word': word,
                'id': spec.get('id', ''),
                'category': spec.get('category', ''),
                'type': spec.get('type', 'static'),
                'duration_ms': spec.get('duration_ms', 500),
                'easing': spec.get('easing', 'ease_out'),
                'loopable': spec.get('loopable', False),
                'blendable': spec.get('blendable', True),
                'glb_fallback': spec.get('glb_fallback'),
            }

            if spec.get('type') == 'sequence':
                anim['keyframes'] = _scale_keyframes(
                    spec.get('keyframes', []), intensity,
                )
            else:
                anim['bones'] = _scale_bones(
                    spec.get('bones', {}), intensity,
                )

            animations.append(anim)

    # 2. Freier Modus: EGON steuert Gelenke direkt
    if has_bones:
        raw_bones = body_data['bones']
        # Validierung: nur erlaubte Bones durchlassen
        valid_bones = _validate_free_bones(raw_bones)
        if valid_bones:
            scaled = _scale_bones(valid_bones, intensity)
            anim = {
                'word': '_frei',
                'id': 'MOT_FREE',
                'category': 'free',
                'type': 'static',
                'duration_ms': body_data.get('duration_ms', 600),
                'easing': body_data.get('easing', 'ease_out'),
                'loopable': False,
                'blendable': True,
                'glb_fallback': None,
                'bones': scaled,
            }
            animations.append(anim)
            print(f'[motor] FREI: {list(valid_bones.keys())} intensity={intensity}')

    if not animations:
        return None

    return {
        'words': [a['word'] for a in animations],
        'intensity': intensity,
        'reason': reason,
        'animations': animations,
    }


# Erlaubte Bones fuer freien Modus (Sicherheit: keine ungueltigen Bones)
VALID_BONES = {
    'head', 'neck',
    'spine_0', 'spine_1', 'spine_2', 'hips',
    'shoulder_L', 'shoulder_R',
    'upper_arm_L', 'upper_arm_R',
    'lower_arm_L', 'lower_arm_R',
    'hand_L', 'hand_R',
    'upper_leg_L', 'upper_leg_R',
    'lower_leg_L', 'lower_leg_R',
}

# Erlaubte Achsen
VALID_AXES = {'rx', 'ry', 'rz', 'tx', 'ty', 'tz'}

# Sicherheits-Limits (Grad) pro Achse — verhindert kaputte Posen
MAX_ROTATION = 180


def _validate_free_bones(raw_bones: dict) -> dict:
    """Validiert und bereinigt frei gesteuerte Bone-Daten.

    Filtert unbekannte Bones, unbekannte Achsen,
    und clampt Werte auf sichere Bereiche.
    """
    validated = {}
    for bone_name, rotations in raw_bones.items():
        if bone_name not in VALID_BONES:
            print(f'[motor] FREI: Unbekannter Bone "{bone_name}" ignoriert')
            continue
        if not isinstance(rotations, dict):
            continue
        clean_rots = {}
        for axis, value in rotations.items():
            if axis not in VALID_AXES:
                continue
            try:
                val = float(value)
                val = max(-MAX_ROTATION, min(MAX_ROTATION, val))
                clean_rots[axis] = round(val, 1)
            except (ValueError, TypeError):
                continue
        if clean_rots:
            validated[bone_name] = clean_rots
    return validated


def check_pose_naturalness(bone_update: dict) -> dict:
    """Prueft ob eine Pose physikalisch natuerlich aussieht.

    FUSION Phase 5: Constraint-Check fuer gelernte Motor-Skills.
    Wird nach Translation aufgerufen um unnatuerliche Kombinationen zu erkennen.

    Returns: {'natural': bool, 'warnings': [...]}
    """
    warnings = []

    if not bone_update or not isinstance(bone_update, dict):
        return {'natural': True, 'warnings': []}

    animations = bone_update.get('animations', [])

    for anim in animations:
        bones = anim.get('bones', {})
        if not bones:
            # Keyframe-Animation — Keyframes einzeln pruefen
            for kf in anim.get('keyframes', []):
                bones = kf.get('bones', {})
                _check_bones(bones, warnings)
            continue
        _check_bones(bones, warnings)

    return {
        'natural': len(warnings) == 0,
        'warnings': warnings,
    }


def _check_bones(bones: dict, warnings: list) -> None:
    """Prueft einzelne Bone-Rotationen auf natuerliche Grenzen."""
    # Kopf: Rotation > 45° in jede Richtung ist unnatuerlich
    head = bones.get('head', {})
    if abs(head.get('ry', 0)) > 45:
        warnings.append('head_overrotation_y')
    if abs(head.get('rx', 0)) > 50:
        warnings.append('head_overrotation_x')
    if abs(head.get('rz', 0)) > 30:
        warnings.append('head_tilt_extreme')

    # Spine: Verdrehung > 30° ist unnatuerlich
    for spine_name in ('spine_0', 'spine_1', 'spine_2'):
        spine = bones.get(spine_name, {})
        if abs(spine.get('ry', 0)) > 30:
            warnings.append(f'{spine_name}_twist_extreme')
        if abs(spine.get('rz', 0)) > 25:
            warnings.append(f'{spine_name}_lateral_extreme')

    # Schultern: Asymmetrie > 20° ist auffaellig
    left_shoulder = bones.get('upper_arm_L', {})
    right_shoulder = bones.get('upper_arm_R', {})
    if left_shoulder and right_shoulder:
        asym = abs(left_shoulder.get('rz', 0) - right_shoulder.get('rz', 0))
        if asym > 40:
            warnings.append('shoulder_asymmetry_extreme')


def _scale_bones(bones: dict, intensity: float) -> dict:
    """Skaliert statische Bone-Rotationen mit Intensitaet.

    intensity=1.0 → volle Werte aus dem Vocabulary
    intensity=0.5 → halbe Werte
    intensity=0.1 → subtile Andeutung

    Translation-Werte (tx, ty, tz) werden auch skaliert.
    """
    scaled = {}
    for bone_name, rotations in bones.items():
        scaled[bone_name] = {}
        for axis, value in rotations.items():
            scaled[bone_name][axis] = round(value * intensity, 2)
    return scaled


def _scale_keyframes(keyframes: list, intensity: float) -> list:
    """Skaliert Keyframe-Bone-Rotationen mit Intensitaet."""
    scaled = []
    for kf in keyframes:
        new_kf = {'t': kf.get('t', 0)}
        bones = kf.get('bones', {})
        new_kf['bones'] = _scale_bones(bones, intensity)
        scaled.append(new_kf)
    return scaled
