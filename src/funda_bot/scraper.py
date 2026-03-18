"""Funda scraper using the Nuxt SSR payload embedded in each search results page.

Funda.nl renders its search results server-side via Nuxt and embeds the full
listing data as a serialised Vue reactive state array inside a <script> tag.
We extract and deserialise that payload directly — no external library, no
HTML class selectors, no API key required.

How it works
------------
1. Build a search URL from filters (same query format Funda uses natively).
2. Fetch the page with a browser-like User-Agent.
3. Find the inline <script> that starts with a JSON array and contains the
   marker string "fetchListings" — that is the Nuxt state payload.
4. Parse the payload array.  Values in each object are integer indices back
   into the same array (a shared-reference pool), or wrapped in Reactive/Ref
   marker tuples.  We resolve them with a two-level unwrap helper.
5. Locate the search state dict (the one that has both "listings" and
   "totalListingsCount" keys) and iterate the listing objects.
6. Normalise each listing to our internal dict format.

Pagination
----------
Each page returns ~15 listings.  scrape_funda() accepts an optional
n_pages argument (default 1) and adds &page=N to the URL for subsequent
pages, sleeping _PAGE_DELAY seconds between requests.
"""

import json
import logging
import re
import sqlite3
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_FUNDA_BASE = 'https://www.funda.nl/en/zoeken/koop'
_THUMBNAIL_BASE = 'https://cloud.funda.nl/valentina_media'
_HEADERS = {
    'User-Agent': 'facebookexternalhit/1.1',
}
_PAGE_DELAY = 3   # seconds between paginated requests
_DB_PATH = Path(__file__).resolve().parent.parent.parent / 'seen_listings.db'


# ---------------------------------------------------------------------------
# State persistence (SQLite)
# ---------------------------------------------------------------------------

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY)')
    conn.commit()
    return conn


def load_seen() -> set:
    """Return the set of all previously seen listing URLs."""
    with _get_conn() as conn:
        rows = conn.execute('SELECT url FROM seen').fetchall()
    return {r[0] for r in rows}


def mark_seen(url: str):
    """Persist a single listing URL as seen. Call only after confirmed delivery."""
    with _get_conn() as conn:
        conn.execute('INSERT OR IGNORE INTO seen (url) VALUES (?)', (url,))
        conn.commit()


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

def _build_url(filters: dict, page: int = 1) -> str:
    """Build a funda.nl search URL from the filter dict."""
    parts: list[str] = []

    areas = filters.get('areas') or []
    if areas:
        quoted = ','.join(f'"{a}"' for a in areas)
        parts.append(f'selected_area=[{quoted}]')

    min_p = filters.get('price_min')
    max_p = filters.get('price_max')
    if min_p is not None or max_p is not None:
        parts.append(f'price="{min_p or ""}-{max_p or ""}"')

    energy = filters.get('energy_labels') or []
    if energy:
        quoted = ','.join(f'"{e}"' for e in energy)
        parts.append(f'energy_label=[{quoted}]')

    parts.append('sort="date_down"')

    if page > 1:
        parts.append(f'page={page}')

    return _FUNDA_BASE + '?' + '&'.join(parts)


# ---------------------------------------------------------------------------
# Nuxt payload parsing
# ---------------------------------------------------------------------------

def _parse_nuxt_listings(html: str) -> tuple[list[dict], int]:
    """Extract normalised listing dicts and total count from a Funda HTML page.

    Returns (listings, total_count).  total_count is the number of matches
    across all pages; listings contains only the current page.
    """
    # Detect the bot-challenge page before attempting to parse
    if 'Je bent bijna op de pagina' in html or 'je bent bijna' in html.lower():
        logger.warning(
            'Funda returned a bot-challenge page — IP may be rate-limited. '
            'The bot will retry on the next scheduled run.'
        )
        return [], 0

    # Find the Nuxt state payload script
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    payload_raw = None
    for s in scripts:
        stripped = s.strip()
        if stripped.startswith('[') and 'fetchListings' in stripped:
            payload_raw = stripped
            break

    if not payload_raw:
        logger.warning('Nuxt payload not found in page — Funda may have changed structure')
        return [], 0

    try:
        arr = json.loads(payload_raw)
    except json.JSONDecodeError as e:
        logger.error(f'Failed to parse Nuxt payload: {e}')
        return [], 0

    def unwrap(x):
        """Strip Ref/Reactive/ShallowReactive wrappers."""
        while (
            isinstance(x, list)
            and len(x) == 2
            and isinstance(x[0], str)
            and x[0] in ('Ref', 'Reactive', 'ShallowReactive')
        ):
            x = arr[x[1]]
        return x

    def r(x):
        """Resolve an integer index or reactive wrapper, one level."""
        if isinstance(x, int) and 0 <= x < len(arr):
            return unwrap(arr[x])
        return unwrap(x)

    # Locate the search state dict: the one with both 'listings' and 'totalListingsCount'
    search_state = None
    for item in arr:
        if isinstance(item, dict) and 'listings' in item and 'totalListingsCount' in item:
            search_state = item
            break

    if not search_state:
        logger.warning('Search state not found in Nuxt payload')
        return [], 0

    total_count = r(search_state['totalListingsCount'])
    if not isinstance(total_count, int):
        total_count = 0

    # The listings value is a doubly-wrapped reactive list of integer indices
    listing_indices = unwrap(unwrap(arr[search_state['listings']]))
    if not isinstance(listing_indices, list):
        return [], total_count

    results: list[dict] = []
    for li in listing_indices:
        try:
            obj = arr[li] if isinstance(li, int) else li
            if not isinstance(obj, dict) or 'id' not in obj:
                continue

            # address
            addr = r(obj.get('address'))
            if not isinstance(addr, dict):
                continue
            street   = str(r(addr.get('street_name')) or '')
            number   = str(r(addr.get('house_number')) or '')
            suffix   = str(r(addr.get('house_number_suffix')) or '')
            city     = str(r(addr.get('city')) or '')
            postcode = str(r(addr.get('postal_code')) or '')

            # price
            price_obj = r(obj.get('price'))
            price_val = None
            if isinstance(price_obj, dict):
                price_raw = r(price_obj.get('selling_price'))
                price_val = r(price_raw[0]) if isinstance(price_raw, list) else price_raw

            # size
            fa = r(obj.get('floor_area'))
            size = r(fa[0]) if isinstance(fa, list) else fa

            # photos — up to 6, valentina_media only (tiara-media requires auth)
            photo_ids_raw = r(obj.get('photo_image_id'))
            photos: list[str] = []
            if isinstance(photo_ids_raw, list):
                for pid in photo_ids_raw:
                    path = r(pid)
                    if isinstance(path, str) and path.startswith('valentina_media/'):
                        photos.append(f'https://cloud.funda.nl/{path}')
                    if len(photos) == 6:
                        break
            thumbnail = photos[0] if photos else None

            # url
            relative_url = r(obj.get('object_detail_page_relative_url'))
            full_url = ('https://www.funda.nl' + relative_url) if relative_url else None

            results.append({
                'title':            f'{street} {number}{suffix}'.strip(),
                'price':            price_val,
                'location':         f'{postcode} {city}'.strip(),
                'size':             size,
                'rooms':            r(obj.get('number_of_rooms')),
                'bedrooms':         r(obj.get('number_of_bedrooms')),
                'energy_label':     r(obj.get('energy_label')),
                'publication_date': r(obj.get('publish_date')),
                'url':              full_url,
                'thumbnail':        thumbnail,
                'photos':           photos,
            })
        except Exception as e:
            logger.debug(f'Skipping listing due to parse error: {e}')
            continue

    return results, total_count


# ---------------------------------------------------------------------------
# Public scraping interface
# ---------------------------------------------------------------------------

def scrape_funda(filters: dict, n_pages: int = 1) -> list[dict]:
    """Fetch listings from funda.nl matching *filters*.

    Scrapes up to *n_pages* pages (default 1).  Returns a list of normalised
    listing dicts.  Invalid or unparseable listings are silently skipped.
    """
    all_listings: list[dict] = []

    for page in range(1, n_pages + 1):
        if page > 1:
            time.sleep(_PAGE_DELAY)

        url = _build_url(filters, page=page)
        logger.info(f'Fetching page {page}: {url}')

        try:
            response = requests.get(url, headers=_HEADERS, timeout=15)
            response.raise_for_status()
        except Exception as e:
            logger.error(f'HTTP error on page {page}: {e}')
            break

        listings, total = _parse_nuxt_listings(response.text)
        logger.info(f'Page {page}: {len(listings)} listings (total available: {total})')
        all_listings.extend(listings)

        # stop early if we've fetched everything
        if len(all_listings) >= total or not listings:
            break

    # deduplicate by URL (multiple areas can yield duplicates)
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for l in all_listings:
        if l['url'] and l['url'] not in seen_urls:
            seen_urls.add(l['url'])
            unique.append(l)

    return unique


def get_new_listings(filters: dict, n_pages: int = 1) -> list[dict]:
    """Return listings not yet seen.

    Does NOT mark listings as seen — the caller must invoke mark_seen(url)
    for each listing only after successful delivery to avoid silent loss.
    """
    listings = scrape_funda(filters, n_pages=n_pages)
    seen = load_seen()
    return [l for l in listings if l.get('url') and l['url'] not in seen]
