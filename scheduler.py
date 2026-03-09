from apscheduler.schedulers.blocking import BlockingScheduler
import logging

logging.basicConfig(filename='scheduler.log', level=logging.ERROR)

def schedule_scrapes(hours, callback):
    """
    Schedule the callback to run at the specified hours every day.
    hours: list of int, e.g. [9, 12, 15, 18]
    """
    try:
        scheduler = BlockingScheduler()
        for hour in hours:
            scheduler.add_job(callback, 'cron', hour=hour, minute=0)
        scheduler.start()
    except Exception as e:
        logging.error(f"Error in scheduler: {e}")