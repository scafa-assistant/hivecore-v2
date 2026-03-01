"""Admin-Endpoints — Kill Switch + Status fuer alle EGONs.

POST /admin/egon/{id}/disable  → EGON deaktivieren
POST /admin/egon/{id}/enable   → EGON reaktivieren
GET  /admin/egons/status       → Status aller EGONs
GET  /admin/rate-limits        → Aktuelle Rate-Limit-Zaehler
"""

from fastapi import APIRouter, HTTPException
from engine.organ_reader import read_yaml_organ, write_yaml_organ
from engine.rate_limiter import get_all_counters, reset_counters

router = APIRouter(tags=['admin'])


@router.post('/admin/egon/{egon_id}/disable')
async def disable_egon(egon_id: str):
    """Deaktiviert einen EGON — Kill Switch."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden')
    state['deaktiviert'] = True
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)
    return {'status': 'disabled', 'egon_id': egon_id}


@router.post('/admin/egon/{egon_id}/enable')
async def enable_egon(egon_id: str):
    """Reaktiviert einen EGON."""
    state = read_yaml_organ(egon_id, 'core', 'state.yaml')
    if not state:
        raise HTTPException(status_code=404, detail=f'EGON {egon_id} nicht gefunden')
    state['deaktiviert'] = False
    write_yaml_organ(egon_id, 'core', 'state.yaml', state)
    return {'status': 'enabled', 'egon_id': egon_id}


@router.get('/admin/egons/status')
async def egons_status():
    """Status aller EGONs: aktiv/deaktiviert, Drives, letzte Aktivitaet."""
    from pathlib import Path
    from config import EGON_DATA_DIR
    from engine.naming import get_display_name

    base = Path(EGON_DATA_DIR)
    egons = []

    for d in sorted(base.iterdir()):
        if not d.is_dir() or d.name in ('shared',):
            continue
        if not ((d / 'kern').exists() or (d / 'core').exists() or (d / 'soul.md').exists()):
            continue

        eid = d.name
        state = read_yaml_organ(eid, 'core', 'state.yaml')
        if not state:
            continue

        drives = state.get('drives', {})
        top_drives = sorted(
            [(k, v) for k, v in drives.items() if isinstance(v, (int, float))],
            key=lambda x: x[1], reverse=True,
        )[:3]

        egons.append({
            'egon_id': eid,
            'name': get_display_name(eid, 'vorname'),
            'deaktiviert': state.get('deaktiviert', False),
            'top_drives': {k: round(v, 3) for k, v in top_drives},
            'phase': state.get('zirkadian', {}).get('aktuelle_phase', '?'),
        })

    return {'egons': egons, 'total': len(egons)}


@router.get('/admin/rate-limits')
async def rate_limits():
    """Aktuelle Rate-Limit-Zaehler aller EGONs."""
    return get_all_counters()


@router.post('/admin/rate-limits/reset/{egon_id}')
async def reset_rate_limit(egon_id: str):
    """Setzt Rate-Limits fuer einen EGON zurueck."""
    reset_counters(egon_id)
    return {'status': 'reset', 'egon_id': egon_id}
