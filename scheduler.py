"""APScheduler fuer den taeglichen Pulse-Cronjob."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import PULSE_HOUR, PULSE_MINUTE
from engine.pulse import run_pulse

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('cron', hour=PULSE_HOUR, minute=PULSE_MINUTE)
async def daily_pulse():
    """Taeglicher Pulse um 08:00."""
    result = await run_pulse('adam')
    # TODO: Push-Notification an App (Expo Push API)
    print(f'[PULSE] Adam: {result.get("idle_thought", "...")}')
