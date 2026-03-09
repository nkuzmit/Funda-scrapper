import yaml
import re
import logging
from scraper import get_new_listings
from notifier import notify_listing
from scheduler import schedule_scrapes

logging.basicConfig(filename='main.log', level=logging.INFO)

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading config: {e}")
        raise

def parse_price(price_str):
    """Parse price string to int, e.g. '€ 529.000 k.k.' -> 529000"""
    try:
        # Remove €, spaces, k.k., and dots
        cleaned = re.sub(r'[€\s\.k\.]+', '', price_str)
        return int(cleaned)
    except:
        return 0

def parse_rooms(rooms_str):
    """Parse rooms string to int"""
    try:
        return int(re.search(r'\d+', rooms_str).group())
    except:
        return 0

def matches_filters(listing, filters):
    """Check if listing matches the filters"""
    try:
        price = parse_price(listing['price'])
        if price < filters['min_price'] or price > filters['max_price']:
            return False
        
        rooms = parse_rooms(listing['rooms'])
        if rooms < filters['min_bedrooms']:
            return False
        
        # Check keywords in title
        if filters['keywords']:
            title_lower = listing['title'].lower()
            if not any(kw.lower() in title_lower for kw in filters['keywords']):
                return False
        
        return True
    except Exception as e:
        logging.error(f"Error matching filters: {e}")
        return False

def scrape_and_notify(config):
    """Scrape and notify for new matching listings"""
    try:
        listings = get_new_listings(config['filters']['city'])
        logging.info(f"Found {len(listings)} new listings")
        for listing in listings:
            if matches_filters(listing, config['filters']):
                notify_listing(config['telegram']['bot_token'], config['telegram']['chat_id'], listing)
                logging.info(f"Notified about {listing['title']}")
    except Exception as e:
        logging.error(f"Error in scrape_and_notify: {e}")

def main():
    config = load_config()
    logging.info("Starting Funda Scraper Bot")
    schedule_scrapes(config['schedule']['hours'], lambda: scrape_and_notify(config))

if __name__ == "__main__":
    main()