import logging
from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)

_TIMEZONE = 'Europe/Amsterdam'


def schedule_scrapes(hours: list, callback):
    """Arrange for *callback* to run at each of the specified times daily.

    The ``hours`` list may contain integers (hour of day) or strings of the
    form ``HH`` or ``HH:MM`` (24‑hour clock).  Entries without minutes default
    to minute 0.  All times are interpreted in Europe/Amsterdam timezone.
    """
    try:
        scheduler = BlockingScheduler(timezone=_TIMEZONE)
        for entry in hours:
            # interpret entry
            if isinstance(entry, str) and ':' in entry:
                parts = entry.split(':')  # could be HH:MM or HH:MM:SS
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                # ignore seconds if provided
            else:
                h = int(entry)
                m = 0
            scheduler.add_job(callback, 'cron', hour=h, minute=m)
        scheduler.start()
    except Exception as e:
        logger.error(f"Error in scheduler: {e}")
