import requests
from bs4 import BeautifulSoup
import json
import os
import logging

logging.basicConfig(filename='scraper.log', level=logging.ERROR)

def scrape_funda(city):
    """
    Scrape funda.nl for house listings in the given city.
    Returns a list of dicts with listing details.
    """
    url = f"https://www.funda.nl/koop/{city}/"
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        listings = []
        # Assuming listings are in div.search-result or similar
        # This selector may need adjustment based on actual HTML
        for item in soup.find_all('div', class_='search-result__item'):  # Placeholder selector
            try:
                title_elem = item.find('h2') or item.find('a', href=True)
                title = title_elem.text.strip() if title_elem else 'Unknown'
                
                price_elem = item.find('span', class_='search-result-price')  # Placeholder
                price = price_elem.text.strip() if price_elem else 'Unknown'
                
                location_elem = item.find('span', class_='search-result-location')  # Placeholder
                location = location_elem.text.strip() if location_elem else 'Unknown'
                
                size_elem = item.find('span', class_='search-result-size')  # Placeholder
                size = size_elem.text.strip() if size_elem else 'Unknown'
                
                rooms_elem = item.find('span', class_='search-result-rooms')  # Placeholder
                rooms = rooms_elem.text.strip() if rooms_elem else 'Unknown'
                
                url_elem = item.find('a', href=True)
                listing_url = 'https://www.funda.nl' + url_elem['href'] if url_elem and url_elem['href'].startswith('/') else 'Unknown'
                
                thumbnail_elem = item.find('img')
                thumbnail = thumbnail_elem['src'] if thumbnail_elem else None
                
                listings.append({
                    'title': title,
                    'price': price,
                    'location': location,
                    'size': size,
                    'rooms': rooms,
                    'url': listing_url,
                    'thumbnail': thumbnail
                })
            except Exception as e:
                logging.error(f"Error parsing listing: {e}")
                continue
        return listings
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return []

def load_seen():
    """Load seen listing URLs from JSON file."""
    if os.path.exists('seen_listings.json'):
        try:
            with open('seen_listings.json', 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_seen(seen):
    """Save seen listing URLs to JSON file."""
    try:
        with open('seen_listings.json', 'w') as f:
            json.dump(list(seen), f)
    except Exception as e:
        logging.error(f"Error saving seen listings: {e}")

def get_new_listings(city):
    """
    Get new listings not seen before.
    Updates the seen set.
    """
    listings = scrape_funda(city)
    seen = load_seen()
    new_listings = [l for l in listings if l['url'] not in seen and l['url'] != 'Unknown']
    seen.update(l['url'] for l in new_listings)
    save_seen(seen)
    return new_listings