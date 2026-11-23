import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_TIMEZONE = 'Europe/Amsterdam'


def schedule_scrapes(hours: list, callback):
    """Arrange for *callback* to run at each of the specified times daily.

    The ``hours`` list may contain integers (hour of day) or strings of the
    form ``HH`` or ``HH:MM`` (24‑hour clock).  Entries without minutes default
    to minute 0.  All times are interpreted in Europe/Amsterdam timezone.
    """
    scheduler = BackgroundScheduler(timezone=_TIMEZONE)
    times: list[str] = []
    for entry in hours:
        try:
            if isinstance(entry, str) and ':' in entry:
                parts = entry.split(':')
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
            else:
                h = int(entry)
                m = 0
            # Inside the try: '25:00' parses but APScheduler raises ValueError
            # here, which used to crash startup (review C12).
            scheduler.add_job(callback, 'cron', hour=h, minute=m)
        except (ValueError, IndexError):
            logger.warning(f"Skipping invalid schedule entry: {entry!r}")
            continue
        times.append(f'{h:02d}:{m:02d}')
    try:
        scheduler.start()
    except Exception as e:
        logger.error(f"Scheduler failed to start: {e}")
        raise
    logger.info(f"Scheduler started: {len(times)} runs a day ({_TIMEZONE}) at {', '.join(times)}")
