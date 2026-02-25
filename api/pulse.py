"""Pulse API — manueller Trigger fuer den Daily Pulse + Snapshots.

Auto-detects brain version per EGON:
  v1 (Adam): engine/pulse.py (9 Steps, .md Files)
  v2 (Eva):  engine/pulse_v2.py (13 Steps, YAML Organe)
"""

from fastapi import APIRouter
from engine.prompt_builder import _detect_brain_version
from engine.snapshot import create_snapshot, list_snapshots, get_latest_snapshot

router = APIRouter()


@router.get('/pulse/trigger')
async def trigger_pulse(egon_id: str = 'adam_001'):
    """Manuell den Pulse fuer einen EGON ausloesen.

    Erkennt automatisch ob der EGON v1 oder v2 Gehirn hat.
    Erstellt automatisch einen Post-Pulse Snapshot.
    """
    brain = _detect_brain_version(egon_id)

    if brain == 'v2':
        from engine.pulse_v2 import run_pulse
    else:
        from engine.pulse import run_pulse

    result = await run_pulse(egon_id)

    # Post-Pulse Snapshot
    try:
        snapshot_meta = create_snapshot(egon_id, brain, pulse_result=result)
        snapshot_info = {
            'date': snapshot_meta.get('snapshot_date'),
            'files': snapshot_meta.get('files_count'),
            'size_bytes': snapshot_meta.get('total_size_bytes'),
        }
    except Exception as e:
        snapshot_info = {'error': str(e)}

    return {
        'egon_id': egon_id,
        'brain_version': brain,
        'pulse': result,
        'snapshot': snapshot_info,
    }


@router.get('/snapshots')
async def get_snapshots(egon_id: str | None = None):
    """Alle Snapshots auflisten, optional gefiltert nach EGON."""
    snaps = list_snapshots(egon_id)
    return {
        'count': len(snaps),
        'snapshots': [
            {
                'date': s.get('snapshot_date'),
                'egon_id': s.get('egon_id'),
                'brain_version': s.get('brain_version'),
                'files_count': s.get('files_count'),
                'total_size_bytes': s.get('total_size_bytes'),
                'pulse': s.get('pulse', {}),
            }
            for s in snaps
        ],
    }


@router.get('/snapshots/latest')
async def get_latest(egon_id: str = 'adam_001'):
    """Letzten Snapshot fuer einen EGON laden."""
    snap = get_latest_snapshot(egon_id)
    if not snap:
        return {'error': f'Kein Snapshot fuer {egon_id}'}
    return snap
