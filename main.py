import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import logging
import yaml
from dotenv import load_dotenv

from funda_bot.scraper import get_new_listings, mark_seen
from funda_bot.notifier import build_notifiers
from funda_bot.scheduler import schedule_scrapes
from funda_bot.filters import matches_filters

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('main.log'),
        logging.StreamHandler(),
    ],
)


def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise


def scrape_and_notify(config: dict, notifiers: list):
    """Scrape for new listings and dispatch to all active notification channels."""
    try:
        filters = config['filters']
        listings = get_new_listings(filters)
        logging.info(f"Found {len(listings)} new listings")

        for listing in listings:
            if not matches_filters(listing, filters):
                continue

            delivered = False
            for notifier in notifiers:
                success = notifier.notify(listing)
                if success:
                    delivered = True
                else:
                    logging.warning(f"{notifier.__class__.__name__} failed for {listing['url']}")

            if delivered:
                mark_seen(listing['url'])
                logging.info(f"Delivered and marked seen: {listing.get('title')}")
            else:
                logging.error(f"All channels failed for {listing['url']} — will retry next run")

    except Exception as e:
        logging.error(f"Error in scrape_and_notify: {e}")


def main():
    config = load_config()
    notifiers = build_notifiers(config)

    if not notifiers:
        logging.error("No notification channels configured — check .env and config.yaml")
        return

    logging.info(f"Starting Funda Scraper Bot ({len(notifiers)} channel(s) active)")
    schedule_scrapes(
        config['schedule']['hours'],
        lambda: scrape_and_notify(config, notifiers),
    )


if __name__ == "__main__":
    main()
