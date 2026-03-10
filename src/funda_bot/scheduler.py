import logging
from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)


def schedule_scrapes(hours: list, callback):
    """Arrange for *callback* to run at each of the specified integer hours daily."""
    try:
        scheduler = BlockingScheduler()
        for hour in hours:
            scheduler.add_job(callback, 'cron', hour=hour, minute=0)
        scheduler.start()
    except Exception as e:
        logger.error(f"Error in scheduler: {e}")
