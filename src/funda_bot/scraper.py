import requests
from bs4 import BeautifulSoup
import json
import os
import logging

logger = logging.getLogger(__name__)


def _build_query(filters: dict) -> str:
    """Compose the query portion of a funda.nl search URL from filters."""
    parts: list[str] = []
    # areas are quoted strings inside a JSON-like array
    areas = filters.get('areas')
    if areas:
        quoted = ','.join(f'"{a}"' for a in areas)
        parts.append(f'selected_area=[{quoted}]')
    # price range
    minp = filters.get('price_min')
    maxp = filters.get('price_max')
    if minp is not None or maxp is not None:
        minp = '' if minp is None else minp
        maxp = '' if maxp is None else maxp
        parts.append(f'price=\"{minp}-{maxp}\"')
    # publication date filter
    if filters.get('publication_days') is not None:
        parts.append(f'publication_date=\"{filters["publication_days"]}\"')
    # energy labels
    energy = filters.get('energy_labels')
    if energy:
        quoted = ','.join(f'"{e}"' for e in energy)
        parts.append(f'energy_label=[{quoted}]')
    # sort by newest first
    parts.append('sort=\"date_down\"')
    return '&'.join(parts)


def scrape_funda(filters: dict) -> list:
    """Scrape funda.nl using the given filters.

    The *filters* dict should mirror the configuration file; the URL
    will be constructed from it.  Returns a list of listing dictionaries
    containing at least the keys used by :func:`filters.matches_filters`.
    """
    base = "https://www.funda.nl/zoeken/koop?"
    query = _build_query(filters)
    url = base + query
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        listings = []
        # Selector placeholders – update when site structure changes
        for item in soup.find_all('div', class_='search-result__item'):
            try:
                title_elem = item.find('h2') or item.find('a', href=True)
                title = title_elem.text.strip() if title_elem else 'Unknown'

                price_elem = item.find('span', class_='search-result-price')
                price = price_elem.text.strip() if price_elem else 'Unknown'

                location_elem = item.find('span', class_='search-result-location')
                location = location_elem.text.strip() if location_elem else 'Unknown'

                size_elem = item.find('span', class_='search-result-size')
                size = size_elem.text.strip() if size_elem else 'Unknown'

                rooms_elem = item.find('span', class_='search-result-rooms')
                rooms = rooms_elem.text.strip() if rooms_elem else 'Unknown'

                # optional additional fields
                pub_elem = item.find('span', class_='search-result-publication-date')  # placeholder
                publication_date = pub_elem.text.strip() if pub_elem else None

                energy_elem = item.find('span', class_='search-result-energy-label')  # placeholder
                energy_label = energy_elem.text.strip() if energy_elem else None

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
                    'publication_date': publication_date,
                    'energy_label': energy_label,
                    'url': listing_url,
                    'thumbnail': thumbnail
                })
            except Exception as e:
                logger.error(f"Error parsing listing: {e}")
                continue
        return listings
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return []


def load_seen() -> set:
    """Load seen listing URLs from JSON file."""
    if os.path.exists('seen_listings.json'):
        try:
            with open('seen_listings.json', 'r') as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_seen(seen: set):
    """Save seen listing URLs to JSON file."""
    try:
        with open('seen_listings.json', 'w') as f:
            json.dump(list(seen), f)
    except Exception as e:
        logger.error(f"Error saving seen listings: {e}")


def get_new_listings(filters: dict) -> list:
    """Get new listings not seen before.

    Does NOT persist seen state — the caller must call mark_seen(url)
    for each listing only after it has been successfully delivered,
    to avoid silently dropping listings on notification failure.
    """
    listings = scrape_funda(filters)
    seen = load_seen()
    return [l for l in listings if l['url'] not in seen and l['url'] != 'Unknown']


def mark_seen(url: str):
    """Mark a single listing URL as seen and persist immediately."""
    seen = load_seen()
    seen.add(url)
    save_seen(seen)