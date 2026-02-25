"""Motor Translator — uebersetzt Motor-Woerter in Bone-Rotationen.

Nimmt die geparsete ###BODY### Daten (words + intensity) und
schlaegt die Bone-Rotationen in motor_vocabulary.json nach.

Output: bone_update dict — bereit fuer die App (skeletalRenderer.ts).
"""

import json
import os
from typing import Optional

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

    Args:
        body_data: {"words": ["nicken", "kopf_neigen"], "intensity": 0.7, "reason": "..."}

    Returns:
        bone_update dict oder None bei Fehler:
        {
            "words": ["nicken", "kopf_neigen"],
            "intensity": 0.7,
            "reason": "...",
            "animations": [
                {
                    "word": "nicken",
                    "type": "sequence",
                    "duration_ms": 600,
                    "easing": "ease_in_out",
                    "loopable": false,
                    "blendable": true,
                    "glb_fallback": null,
                    "keyframes": [...] oder "bones": {...}
                },
                ...
            ]
        }
    """
    if not body_data or not isinstance(body_data.get('words'), list):
        return None

    vocab = _load_vocab()
    words = body_data['words']
    intensity = body_data.get('intensity', 0.5)
    reason = body_data.get('reason', '')

    animations = []
    for word in words:
        spec = vocab.get(word)
        if not spec:
            # Unbekanntes Wort — skippen (LLM hat etwas halluziniert)
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

        # Bone-Daten je nach Typ
        if spec.get('type') == 'sequence':
            anim['keyframes'] = _scale_keyframes(
                spec.get('keyframes', []), intensity,
            )
        else:
            anim['bones'] = _scale_bones(
                spec.get('bones', {}), intensity,
            )

        animations.append(anim)

    if not animations:
        return None

    return {
        'words': [a['word'] for a in animations],
        'intensity': intensity,
        'reason': reason,
        'animations': animations,
    }


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
