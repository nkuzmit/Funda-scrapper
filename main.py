import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import yaml
import logging

from funda_bot.scraper import get_new_listings
from funda_bot.notifier import notify_listing
from funda_bot.scheduler import schedule_scrapes
from funda_bot.filters import matches_filters

logging.basicConfig(filename='main.log', level=logging.INFO)

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise


def scrape_and_notify(config):
    """Scrape and notify for new matching listings"""
    try:
        filters = config['filters']
        listings = get_new_listings(filters)
        logging.info(f"Found {len(listings)} new listings")
        for listing in listings:
            if matches_filters(listing, filters):
                notify_listing(
                    config['telegram']['bot_token'],
                    config['telegram']['chat_id'],
                    listing,
                )
                logging.info(f"Notified about {listing['title']}")
    except Exception as e:
        logging.error(f"Error in scrape_and_notify: {e}")

def main():
    config = load_config()
    logging.info("Starting Funda Scraper Bot")
    schedule_scrapes(config['schedule']['hours'], lambda: scrape_and_notify(config))

if __name__ == "__main__":
    main()