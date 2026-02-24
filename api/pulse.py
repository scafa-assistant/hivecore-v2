"""Pulse API — manueller Trigger fuer den Daily Pulse.

Auto-detects brain version per EGON:
  v1 (Adam): engine/pulse.py (9 Steps, .md Files)
  v2 (Eva):  engine/pulse_v2.py (13 Steps, YAML Organe)
"""

from fastapi import APIRouter
from engine.prompt_builder import _detect_brain_version

router = APIRouter()


@router.get('/pulse/trigger')
async def trigger_pulse(egon_id: str = 'adam_001'):
    """Manuell den Pulse fuer einen EGON ausloesen.

    Erkennt automatisch ob der EGON v1 oder v2 Gehirn hat.
    """
    brain = _detect_brain_version(egon_id)

    if brain == 'v2':
        from engine.pulse_v2 import run_pulse
    else:
        from engine.pulse import run_pulse

    result = await run_pulse(egon_id)
    return {
        'egon_id': egon_id,
        'brain_version': brain,
        'pulse': result,
    }
