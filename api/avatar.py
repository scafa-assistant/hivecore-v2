"""Avatar-State Endpoint — Gibt den aktuellen Zustand eines EGONs fuer die 3D-Avatar-Animation zurueck.

Der Avatar im Dashboard zeigt den emotionalen Zustand visuell:
- Stimmung beeinflusst die Grundanimation (idle, walking, confused)
- Emotionen triggern spezielle Animationen (celebrating, angry, sleeping)
- Energie beeinflusst die Geschwindigkeit
"""

from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import EGON_DATA_DIR
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from engine.body_state_engine import compute_body_state

router = APIRouter()


# ================================================================
# FUSION Phase 4: Body Feedback (POST Request Model)
# ================================================================

class BodyFeedbackModel(BaseModel):
    position: Optional[dict] = None
    facing: Optional[float] = None
    is_walking: Optional[bool] = None
    last_motor_word: Optional[str] = None
    seconds_since_last_gesture: Optional[int] = None
    seconds_since_last_chat: Optional[int] = None

class AvatarStateRequest(BaseModel):
    body_feedback: Optional[BodyFeedbackModel] = None


# ================================================================
# Emotion → Animation Mapping
# ================================================================

EMOTION_TO_ANIMATION = {
    'curiosity': 'idle',
    'excitement': 'celebrating',
    'joy': 'very_happy',
    'love': 'very_happy',
    'anger': 'angry',
    'rage': 'angry',
    'fear': 'confused',
    'anxiety': 'confused',
    'caution': 'idle',
    'sadness': 'pain',
    'grief': 'pain',
    'loneliness': 'pain',
}

MOOD_TO_ANIMATION = {
    # mood_value ranges
    'very_low': 'pain',        # 0.0 - 0.2
    'low': 'confused',         # 0.2 - 0.4
    'neutral': 'idle',         # 0.4 - 0.6
    'good': 'idle',            # 0.6 - 0.8
    'great': 'celebrating',    # 0.8 - 1.0
}


def _mood_to_animation(mood_value: float) -> str:
    """Mappt einen Mood-Wert (0-1) auf eine Animation."""
    if mood_value < 0.2:
        return 'pain'
    elif mood_value < 0.4:
        return 'confused'
    elif mood_value < 0.6:
        return 'idle'
    elif mood_value < 0.8:
        return 'idle'
    else:
        return 'celebrating'


def _resolve_animation(state: dict) -> str:
    """Bestimmt die beste Animation basierend auf dem EGON-State.

    Prioritaet: special_event > activity > emotional > mood_baseline
    """
    # 1. Express: Staerkste Emotion
    express = state.get('express', {})
    emotions = express.get('active_emotions', [])

    if emotions:
        # Sortiere nach Intensitaet
        sorted_emo = sorted(emotions, key=lambda e: e.get('intensity', 0), reverse=True)
        top = sorted_emo[0]
        emo_type = top.get('type', '')
        intensity = top.get('intensity', 0)

        if intensity > 0.7:
            # Starke Emotion → spezielle Animation
            anim = EMOTION_TO_ANIMATION.get(emo_type)
            if anim:
                return anim

    # 2. Mood-basierte Fallback-Animation
    thrive = state.get('thrive', {})
    mood = thrive.get('mood', {})
    mood_value = mood.get('value', 0.5) if isinstance(mood, dict) else 0.5

    return _mood_to_animation(mood_value)


@router.get('/egon/{egon_id}/avatar-state')
async def get_avatar_state(egon_id: str):
    """Gibt den aktuellen Avatar-State fuer die 3D-Animation zurueck.

    Response:
        activity: Was der EGON gerade tut (idle, working, sleeping)
        primary_emotion: Staerkste aktuelle Emotion
        emotion_intensity: Staerke der Emotion (0-1)
        mood: Allgemeine Stimmung (0-1)
        energy: Energie-Level (0-1)
        animation: Empfohlene Animation (gemappt aus State)
        special_event: Spezialevent (z.B. Geburtstag)
    """
    egon_path = Path(EGON_DATA_DIR) / egon_id
    if not egon_path.exists():
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden.')

    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        # Fallback: Neutral state
        return {
            'activity': 'idle',
            'primary_emotion': 'neutral',
            'emotion_intensity': 0.0,
            'mood': 0.5,
            'energy': 0.5,
            'animation': 'idle',
            'special_event': None,
        }

    # Avatar-Animations Config laden (falls vorhanden)
    anim_config = _load_animation_config(egon_id)

    # Express-Layer auslesen
    express = state.get('express', {})
    emotions = express.get('active_emotions', [])
    top_emotion = 'neutral'
    top_intensity = 0.0

    if emotions:
        sorted_emo = sorted(emotions, key=lambda e: e.get('intensity', 0), reverse=True)
        top_emotion = sorted_emo[0].get('type', 'neutral')
        top_intensity = sorted_emo[0].get('intensity', 0.0)

    # Thrive-Layer
    thrive = state.get('thrive', {})
    mood_data = thrive.get('mood', {})
    mood_value = mood_data.get('value', 0.5) if isinstance(mood_data, dict) else 0.5

    # Survive-Layer
    survive = state.get('survive', {})
    energy_data = survive.get('energy', {})
    energy_value = energy_data.get('value', 0.5) if isinstance(energy_data, dict) else 0.5

    # Animation bestimmen
    animation = _resolve_animation(state)

    # FUSION Phase 3: Body State + Behavior Params
    body = compute_body_state(egon_id)

    # Autonome Motor-Aktion (falls vom Somatic Gate geschrieben)
    autonomous_bone_update = _pop_pending_motor_action(egon_id)

    # Circadian Phase
    zirkadian = state.get('zirkadian', {})
    circadian_phase = zirkadian.get('aktuelle_phase', 'aktivitaet')

    return {
        'activity': 'idle',
        'primary_emotion': top_emotion,
        'emotion_intensity': round(top_intensity, 2),
        'mood': round(mood_value, 2),
        'energy': round(energy_value, 2),
        'animation': animation,
        'special_event': None,
        # FUSION Phase 3
        'body_state': body['body_state'],
        'behavior_params': body['behavior_params'],
        'autonomous_bone_update': autonomous_bone_update,
        'circadian_phase': circadian_phase,
    }


@router.post('/egon/{egon_id}/avatar-state')
async def post_avatar_state(egon_id: str, request: AvatarStateRequest = None):
    """POST version — empfaengt body_feedback, gibt gleichen avatar-state zurueck.

    FUSION Phase 4: Die App sendet alle 15s body_feedback mit Position,
    Facing, Walking-Status, letzter Geste und Idle-Zeiten.
    Rueckwaerts-kompatibel: GET ohne body_feedback funktioniert weiterhin.
    """
    if request and request.body_feedback:
        try:
            from engine.proprioception import process_body_feedback
            process_body_feedback(egon_id, request.body_feedback.dict())
        except Exception as e:
            print(f'[avatar] body_feedback error: {e}')

    return await get_avatar_state(egon_id)


def _pop_pending_motor_action(egon_id: str) -> dict | None:
    """Liest und loescht eine ausstehende autonome Motor-Aktion.

    Wird vom Somatic Gate geschrieben, vom avatar-state Endpoint abgeholt.
    Einmal gelesen = geloescht (Consume-Semantik).
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return None
    pending = state.get('pending_motor_action')
    if not pending:
        return None
    # Consume: Entfernen nach Lesen
    del state['pending_motor_action']
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)
    return pending


def _load_animation_config(egon_id: str) -> dict:
    """Laedt die Avatar-Animations-Config fuer einen EGON."""
    config_path = Path(EGON_DATA_DIR) / egon_id / 'config' / 'avatar_animations.yaml'
    if not config_path.is_file():
        return {}
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return {}
