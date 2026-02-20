"""Pulse API — manueller Trigger fuer den Daily Pulse."""

from fastapi import APIRouter
from engine.pulse import run_pulse

router = APIRouter()


@router.get('/pulse/trigger')
async def trigger_pulse(egon_id: str = 'adam'):
    """Manuell den Pulse fuer einen EGON ausloesen."""
    result = await run_pulse(egon_id)
    return {
        'egon_id': egon_id,
        'pulse': result,
    }
