"""APScheduler fuer den taeglichen Pulse-Cronjob.

Multi-EGON: Pulsed ALLE aktiven EGONs, nicht nur einen.
"""

from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import PULSE_HOUR, PULSE_MINUTE, EGON_DATA_DIR
from engine.pulse_v2 import run_pulse

scheduler = AsyncIOScheduler()


def _discover_egon_ids() -> list[str]:
    """Findet alle EGON-IDs im egons/ Verzeichnis."""
    base = Path(EGON_DATA_DIR)
    if not base.exists():
        return []
    return sorted([
        d.name for d in base.iterdir()
        if d.is_dir() and (d / 'core').exists()
    ])


@scheduler.scheduled_job('cron', hour=PULSE_HOUR, minute=PULSE_MINUTE)
async def daily_pulse():
    """Taeglicher Pulse um 08:00 — fuer ALLE EGONs."""
    egon_ids = _discover_egon_ids()
    if not egon_ids:
        print('[PULSE] Keine EGONs gefunden.')
        return

    for eid in egon_ids:
        try:
            result = await run_pulse(eid)
            thought = result.get('idle_thought', '...')
            print(f'[PULSE] {eid}: {thought}')
        except Exception as e:
            print(f'[PULSE] {eid}: FEHLER — {e}')

    # TODO: Push-Notification an App (Expo Push API)
    print(f'[PULSE] Fertig. {len(egon_ids)} EGONs gepulst.')
