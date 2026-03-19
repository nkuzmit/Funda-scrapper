import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

import logging
import logging.handlers
import os
import time
import yaml
from dotenv import load_dotenv

from funda_bot.scraper import get_new_listings, mark_seen
from funda_bot.notifier import build_notifiers
from funda_bot.scheduler import schedule_scrapes
from funda_bot.filters import matches_filters
from funda_bot.commands import poll_commands, _send, HELP_TEXT

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


_CONFIG_PATH = Path(__file__).resolve().parent / 'config.yaml'


def load_config():
    """Load configuration from config.yaml."""
    try:
        with open(_CONFIG_PATH, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise


def scrape_and_notify(config: dict, notifiers: list) -> int:
    """Scrape for new listings and dispatch to all active notification channels.

    Returns the number of successfully delivered listings.
    """
    try:
        filters = config['filters']
        listings = get_new_listings(filters)
        logger.info(f"Found {len(listings)} new listings")

        delivered_count = 0
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

        return delivered_count

    except Exception as e:
        logger.error(f"Error in scrape_and_notify: {e}")
        return 0


def main():
    config = load_config()
    notifiers = build_notifiers(config)

    if not notifiers:
        logger.error("No notification channels configured — check .env and config.yaml")
        return

    logger.info(f"Starting Funda Scraper Bot ({len(notifiers)} channel(s) active)")
    logger.info("Running initial scrape on startup...")
    scrape_and_notify(config, notifiers)
    schedule_scrapes(
        config['schedule']['hours'],
        lambda: scrape_and_notify(config, notifiers),
    )

    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not config['filters'].get('areas'):
        if bot_token and chat_id:
            _send(bot_token, chat_id, "No areas configured.\n\n" + HELP_TEXT)

    if bot_token and chat_id:
        poll_commands(
            bot_token, chat_id, config,
            lambda: scrape_and_notify(config, notifiers),
        )
    else:
        logger.warning("Telegram credentials not set — command interface unavailable")
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
