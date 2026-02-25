"""APScheduler fuer den taeglichen Pulse-Cronjob.

Multi-EGON: Pulsed ALLE aktiven EGONs, nicht nur einen.
Nach jedem Pulse wird ein automatischer Snapshot erstellt.
"""

from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import PULSE_HOUR, PULSE_MINUTE, EGON_DATA_DIR
from engine.prompt_builder import _detect_brain_version
from engine.snapshot import create_snapshot

scheduler = AsyncIOScheduler()


def _discover_egon_ids() -> list[str]:
    """Findet alle EGON-IDs im egons/ Verzeichnis.

    v2: core/ vorhanden, v1: soul.md vorhanden.
    Symlinks werden bevorzugt (adam_001 -> adam → nur adam_001).
    """
    base = Path(EGON_DATA_DIR)
    if not base.exists():
        return []

    symlink_targets = set()
    for d in base.iterdir():
        if d.is_symlink() and d.is_dir():
            try:
                symlink_targets.add(d.resolve().name)
            except OSError:
                pass

    found = set()
    for d in base.iterdir():
        if not d.is_dir() or d.name in ('shared',):
            continue
        if not d.is_symlink() and d.name in symlink_targets:
            continue
        if (d / 'core').exists() or (d / 'soul.md').exists():
            found.add(d.name)

    return sorted(found)


@scheduler.scheduled_job('cron', hour=PULSE_HOUR, minute=PULSE_MINUTE)
async def daily_pulse():
    """Taeglicher Pulse um 08:00 — fuer ALLE EGONs."""
    egon_ids = _discover_egon_ids()
    if not egon_ids:
        print('[PULSE] Keine EGONs gefunden.')
        return

    pulse_results = {}
    for eid in egon_ids:
        try:
            brain = _detect_brain_version(eid)
            if brain == 'v2':
                from engine.pulse_v2 import run_pulse as run_pulse_fn
            else:
                from engine.pulse import run_pulse as run_pulse_fn
            result = await run_pulse_fn(eid)
            pulse_results[eid] = (brain, result)
            thought = result.get('idle_thought', result.get('discovery', '...'))
            print(f'[PULSE] {eid} ({brain}): {thought}')
        except Exception as e:
            print(f'[PULSE] {eid}: FEHLER — {e}')

    # Post-Pulse Snapshots — automatische Archivierung
    for eid, (brain, result) in pulse_results.items():
        try:
            create_snapshot(eid, brain, pulse_result=result)
        except Exception as e:
            print(f'[snapshot] {eid}: FEHLER — {e}')

    # TODO: Push-Notification an App (Expo Push API)
    print(f'[PULSE] Fertig. {len(egon_ids)} EGONs gepulst + archiviert.')
