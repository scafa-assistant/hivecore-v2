"""Proprioception — Adam spuert sich selbst.

Verarbeitet body_feedback von der App und speichert body_awareness in state.yaml.
Das LLM kann dann auf Position, Gesten, Idle-Zeit reagieren.

FUSION Phase 4.
"""

from datetime import datetime
from engine.organ_reader import read_yaml_organ, write_yaml_organ


def process_body_feedback(egon_id: str, feedback: dict) -> None:
    """Verarbeitet body_feedback von der App und speichert in state.yaml.

    Args:
        feedback: {
            'position': {'x': 1.2, 'z': -0.8},
            'facing': 2.1,
            'is_walking': False,
            'last_motor_word': 'nicken',
            'seconds_since_last_gesture': 45,
            'seconds_since_last_chat': 180,
        }
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return

    pos = feedback.get('position', {})
    state['body_awareness'] = {
        'position': {
            'x': round(pos.get('x', 0), 1),
            'z': round(pos.get('z', 0), 1),
        },
        'facing': round(feedback.get('facing', 0), 2),
        'is_walking': bool(feedback.get('is_walking', False)),
        'last_gesture': feedback.get('last_motor_word', ''),
        'idle_since': int(feedback.get('seconds_since_last_gesture', 0)),
        'alone_since': int(feedback.get('seconds_since_last_chat', 0)),
        'updated_at': datetime.now().isoformat(),
    }

    write_yaml_organ(egon_id, 'core', 'state.yaml', state)


def body_awareness_to_prompt(egon_id: str) -> str:
    """Generiert einen natuerlichsprachigen Prompt aus body_awareness.

    Returns z.B.:
        "Ich stehe gerade rechts hinten im Raum. Ich laufe nicht.
         Seit 3 Minuten hat niemand mit mir gesprochen.
         Meine letzte Geste war ein Nicken vor 45 Sekunden."
    """
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        return ''

    ba = state.get('body_awareness')
    if not ba:
        return ''

    parts = []

    # Position beschreiben
    x = ba.get('position', {}).get('x', 0)
    z = ba.get('position', {}).get('z', 0)
    pos_desc = _describe_position(x, z)
    parts.append(f'Ich stehe gerade {pos_desc}.')

    # Bewegungszustand
    if ba.get('is_walking'):
        parts.append('Ich laufe gerade.')

    # Letzte Geste
    last_gesture = ba.get('last_gesture', '')
    idle_since = ba.get('idle_since', 0)
    if last_gesture and idle_since > 0:
        if idle_since < 60:
            parts.append(f'Meine letzte Geste war {last_gesture} vor {idle_since} Sekunden.')
        else:
            mins = idle_since // 60
            parts.append(f'Meine letzte Geste war {last_gesture} vor {mins} Minuten.')

    # Allein-Zeit
    alone_since = ba.get('alone_since', 0)
    if alone_since > 60:
        mins = alone_since // 60
        if mins >= 60:
            hours = mins // 60
            parts.append(f'Seit {hours} Stunde{"n" if hours > 1 else ""} hat niemand mit mir gesprochen.')
        else:
            parts.append(f'Seit {mins} Minuten hat niemand mit mir gesprochen.')

    return ' '.join(parts)


def _describe_position(x: float, z: float) -> str:
    """Beschreibt eine x/z Position in natuerlicher Sprache.

    Gehege: -1.5..+1.5 auf x, -4.0..+1.0 auf z.
    x > 0 = rechts, x < 0 = links
    z > 0 = vorne (nah an Kamera), z < 0 = hinten (weit weg)
    """
    # Horizontal
    if x > 0.8:
        h = 'rechts'
    elif x < -0.8:
        h = 'links'
    else:
        h = 'in der Mitte'

    # Tiefe
    if z < -2.0:
        d = 'hinten'
    elif z > 0.0:
        d = 'vorne'
    else:
        d = ''

    if h == 'in der Mitte' and not d:
        return 'in der Mitte des Raums'
    elif h == 'in der Mitte':
        return f'{d} in der Mitte'
    elif d:
        return f'{h} {d} im Raum'
    else:
        return f'{h} im Raum'
