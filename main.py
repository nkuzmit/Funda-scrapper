import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

import logging
import logging.handlers
import yaml
from dotenv import load_dotenv

from funda_bot.scraper import get_new_listings, mark_seen
from funda_bot.notifier import build_notifiers
from funda_bot.scheduler import schedule_scrapes
from funda_bot.filters import matches_filters

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


def scrape_and_notify(config: dict, notifiers: list):
    """Scrape for new listings and dispatch to all active notification channels."""
    try:
        filters = config['filters']
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
            else:
                logger.error(f"All channels failed for {listing['url']} — will retry next run")

    except Exception as e:
        logger.error(f"Error in scrape_and_notify: {e}")


def main():
    config = load_config()
    notifiers = build_notifiers(config)

    if not notifiers:
        logger.error("No notification channels configured — check .env and config.yaml")
        return

    logger.info(f"Starting Funda Scraper Bot ({len(notifiers)} channel(s) active)")
    schedule_scrapes(
        config['schedule']['hours'],
        lambda: scrape_and_notify(config, notifiers),
    )


if __name__ == "__main__":
    main()
