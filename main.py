import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

import copy
import logging
import logging.handlers
import os
import shutil
import threading
import time
from typing import NamedTuple

import yaml
from dotenv import load_dotenv

from funda_bot.scraper import ScrapeError, get_new_listings, mark_seen
from funda_bot.notifier import build_notifiers
from funda_bot.scheduler import schedule_scrapes
from funda_bot.filters import matches_filters
from funda_bot.commands import poll_commands, _send, HELP_TEXT, _CONFIG_LOCK, _CONFIG_PATH

load_dotenv()

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler(
            'main.log', maxBytes=5 * 1024 * 1024, backupCount=3
        ),
        logging.StreamHandler(),
    ],
)
# APScheduler's INFO lines ("Running job", "Job executed", "Added job") were
# 29% of main.log by 2026-11. Its warnings and errors (a missed run, a job
# that raised) still get through; funda_bot.scheduler logs the schedule itself.
logging.getLogger('apscheduler').setLevel(logging.WARNING)


_CONFIG_EXAMPLE_PATH = Path(__file__).resolve().parent / 'config.example.yaml'


def load_config():
    """Load configuration from config.yaml, bootstrapping from the template on first run."""
    if not _CONFIG_PATH.exists():
        if not _CONFIG_EXAMPLE_PATH.exists():
            logger.error("Neither config.yaml nor config.example.yaml found")
            raise FileNotFoundError("config.example.yaml is missing")
        shutil.copyfile(_CONFIG_EXAMPLE_PATH, _CONFIG_PATH)
        logger.info("config.yaml not found — created from config.example.yaml")
    try:
        with open(_CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise


class RunResult(NamedTuple):
    """Outcome of one scrape_and_notify run."""
    delivered: int              # listings delivered to at least one channel
    failed: int                 # listings every channel failed on (retried next run)
    error: str | None = None    # why the run failed; None if it completed
    skipped: str | None = None  # why no scrape ran; None if one did


# Alert after this many failed runs in a row. A single failure is retried
# quietly: 8 months of logs (to 2026-11-20) show 2 failures, both one-off
# read timeouts followed by a normal run.
_ALERT_AFTER = 2
_HEALTH_LOCK = threading.Lock()   # /run and the scheduler can run concurrently
_failed_runs = 0                  # consecutive failed runs; a restart resets it


def _track_health(error: str | None) -> str | None:
    """Count consecutive failed runs; return an alert or recovery message to send."""
    global _failed_runs
    with _HEALTH_LOCK:
        if error is None:
            n, _failed_runs = _failed_runs, 0
            if n >= _ALERT_AFTER:
                return f"✅ Scraping recovered after {n} failed runs."
            return None
        _failed_runs += 1
        if _failed_runs == _ALERT_AFTER:
            return (
                f"🚨 Scraping has failed {_failed_runs} runs in a row — "
                f"new listings are not being checked.\n\nLast error: {error}\n\n"
                "See main.log. You'll get a message when it recovers."
            )
        return None


def scrape_and_notify(config: dict, notifiers: list, alert=None) -> RunResult:
    """Scrape for new listings and dispatch to all active notification channels.

    A failed run is reported in RunResult.error and a skipped one in
    RunResult.skipped, never as "nothing new".
    After _ALERT_AFTER failed runs in a row, *alert* (a callable taking the
    message text) is called once, and again when a run next succeeds.
    """
    delivered_count = 0
    failed_count = 0
    error = None
    try:
        with _CONFIG_LOCK:
            filters = copy.deepcopy(config['filters'])
        if not filters.get('areas'):
            logger.info("No areas configured — skipping scrape until setup is complete.")
            # Neither a failure nor a success, so the health counter is untouched.
            return RunResult(0, 0, skipped='no areas configured')
        listings = get_new_listings(filters)
        logger.info(f"Found {len(listings)} new listings")

        for listing in listings:
            if not matches_filters(listing, filters):
                continue

            delivered = False
            for notifier in notifiers:
                success = notifier.notify(listing)
                if success:
                    delivered = True
                else:
                    logger.warning(f"{notifier.__class__.__name__} failed for {listing['url']}")

            if delivered:
                mark_seen(listing['url'])
                logger.info(f"Delivered and marked seen: {listing.get('title')}")
                delivered_count += 1
            else:
                logger.error(f"All channels failed for {listing['url']} — will retry next run")
                failed_count += 1

    except ScrapeError as e:
        error = str(e)
        logger.error(f"Scrape failed: {error}")
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        logger.exception(f"Error in scrape_and_notify: {error}")

    message = _track_health(error)
    if message:
        logger.warning(message)
        if alert:
            alert(message)
    return RunResult(delivered_count, failed_count, error)


def main():
    config = load_config()
    notifiers = build_notifiers(config)

    if not notifiers:
        logger.error("No notification channels configured — check .env and config.yaml")
        return

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    # Scrape-failure alerts go to Telegram; without it they're only logged.
    alert = (lambda text: _send(bot_token, chat_id, text)) if bot_token and chat_id else None

    def run() -> RunResult:
        return scrape_and_notify(config, notifiers, alert)

    logger.info(f"Starting Funda Scraper Bot ({len(notifiers)} channel(s) active)")
    if config['filters'].get('areas'):
        logger.info("Running initial scrape on startup...")
        run()
    else:
        logger.info("No areas configured yet — skipping startup scrape until filters are set up.")
    schedule_scrapes(config['schedule']['hours'], run)

    if not config['filters'].get('areas'):
        if bot_token and chat_id:
            _send(bot_token, chat_id, "No areas configured.\n\n" + HELP_TEXT)

    if bot_token and chat_id:
        poll_commands(bot_token, chat_id, config, run)
    else:
        logger.warning("Telegram credentials not set — command interface unavailable")
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
