"""Funda scraper using the Nuxt SSR payload embedded in each search results page.

Funda.nl renders its search results server-side via Nuxt and embeds the full
listing data as a serialised Vue reactive state array inside a <script> tag.
We extract and deserialise that payload directly — no external library, no
HTML class selectors, no API key required.

How it works
------------
1. Build a search URL from filters (same query format Funda uses natively).
2. Fetch the page with the User-Agent in _HEADERS (a link-preview crawler's,
   facebookexternalhit/1.1 — not a browser's).
3. Find the inline <script> that starts with a JSON array and contains the
   marker string "fetchListings" — that is the Nuxt state payload.
4. Parse the payload array.  Values in each object are integer indices back
   into the same array (a shared-reference pool), or wrapped in
   Ref/Reactive/ShallowReactive/ShallowRef marker tuples.  We resolve them
   with an unwrap helper.  An unrecognised marker on the listings empties
   the result (this happened when Funda switched to ShallowRef on
   2026-11-05) — which now raises ScrapeError when Funda reports matches.
5. Locate the search state dict (the one that has both "listings" and
   "totalListingsCount" keys) and iterate the listing objects.
6. Normalise each listing to our internal dict format.

Failure vs. a quiet day
-----------------------
A failed scrape raises ScrapeError; a quiet market returns an empty list.
Never collapse the two — that hid the ShallowRef outage for 15 days.

Pagination
----------
Each page returns ~15 listings.  scrape_funda() accepts an optional
n_pages argument (default 1) and adds &page=N to the URL for subsequent
pages, sleeping _PAGE_DELAY_SECONDS between requests.
"""

import json
import logging
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_FUNDA_BASE = 'https://www.funda.nl/zoeken/koop'
_HEADERS = {
    'User-Agent': 'facebookexternalhit/1.1',
}
_PAGE_DELAY_SECONDS = 3
_DB_PATH = Path(__file__).resolve().parent.parent.parent / 'seen_listings.db'

# Listing photos are served from Funda's media CDN.  The current backend is
# tiara-media (sized via an ?options=width query); valentina_media is the
# legacy backend still used by some older listings.
_PHOTO_HOST = 'https://cloud.funda.nl'
_PHOTO_WIDTH = 720
# Kept per listing. The Telegram notifier sends 6 and uses the rest as spares
# for photos Telegram fails to fetch. Search results carry 7-12 (2026-11-20).
_MAX_PHOTOS = 10


class ScrapeError(Exception):
    """The scrape failed — distinct from a successful scrape that found nothing."""


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
        quoted = ','.join(f'"{e.replace("+", "%2B")}"' for e in energy)
        parts.append(f'energy_label=[{quoted}]')

    pub_days = filters.get('publication_days')
    if pub_days:
        parts.append(f'publication_date="{pub_days}"')

    min_fa = filters.get('floor_area_min')
    max_fa = filters.get('floor_area_max')
    if min_fa is not None or max_fa is not None:
        parts.append(f'floor_area="{min_fa or ""}-{max_fa or ""}"')

    min_bed = filters.get('min_bedrooms')
    if min_bed:
        parts.append(f'bedrooms="{min_bed}-"')

    amenities = filters.get('amenities') or []
    if amenities:
        quoted = ','.join(f'"{a}"' for a in amenities)
        parts.append(f'amenities=[{quoted}]')

    parts.append('sort="date_down"')

    if page > 1:
        parts.append(f'page={page}')

    return _FUNDA_BASE + '?' + '&'.join(parts)


# ---------------------------------------------------------------------------
# Nuxt payload parsing
# ---------------------------------------------------------------------------

def _photo_url(path) -> str | None:
    """Build a public listing-image URL from a resolved photo path.

    Funda serves listing photos from ``tiara-media/<uuid>/<uuid>`` paths
    (sized via an ``?options=width`` query) and legacy ``valentina_media/...``
    paths.  Anything else — agent logos, unknown formats, non-strings —
    returns None and is skipped by the caller.
    """
    if not isinstance(path, str):
        return None
    if path.startswith('tiara-media/'):
        return f'{_PHOTO_HOST}/{path}?options=width={_PHOTO_WIDTH}'
    if path.startswith('valentina_media/'):
        return f'{_PHOTO_HOST}/{path}'
    return None


def _parse_nuxt_listings(html: str) -> tuple[list[dict], int]:
    """Extract normalised listing dicts and total count from a Funda HTML page.

    Returns (listings, total_count).  total_count is the number of matches
    across all pages; listings contains only the current page.  Raises
    ScrapeError when the page can't be read — see the module docstring.
    """
    # Detect the bot-challenge page before attempting to parse
    if 'Je bent bijna op de pagina' in html or 'je bent bijna' in html.lower():
        raise ScrapeError('Funda returned a bot-challenge page — IP may be rate-limited')

    # Find the Nuxt state payload script
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    payload_raw = None
    for s in scripts:
        stripped = s.strip()
        if stripped.startswith('[') and 'fetchListings' in stripped:
            payload_raw = stripped
            break

    if not payload_raw:
        raise ScrapeError('Nuxt payload not found in page — Funda may have changed structure')

    try:
        arr = json.loads(payload_raw)
    except json.JSONDecodeError as e:
        raise ScrapeError(f'Failed to parse Nuxt payload: {e}') from e

    def unwrap(x):
        """Strip Ref/Reactive/ShallowReactive/ShallowRef wrappers."""
        while (
            isinstance(x, list)
            and len(x) == 2
            and isinstance(x[0], str)
            and x[0] in ('Ref', 'Reactive', 'ShallowReactive', 'ShallowRef')
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
        raise ScrapeError('Search state not found in Nuxt payload')

    total_count = r(search_state['totalListingsCount'])
    # On a 0-match page Funda sends ['EmptyRef', i] -> '0' (a string), which
    # unwrap() doesn't know (verified on a live page, 2026-11-20).  Treating
    # a non-int as 0 is what keeps quiet days quiet — don't make it an error.
    if not isinstance(total_count, int):
        total_count = 0

    # The listings value is a reactive-wrapped list of integer indices
    listing_indices = unwrap(unwrap(arr[search_state['listings']]))
    if not isinstance(listing_indices, list):
        raise ScrapeError(
            f'Listings field is not a list ({type(listing_indices).__name__}) '
            f'but Funda reports {total_count} matches — payload shape may have changed'
        )

    results: list[dict] = []
    skipped: Counter[str] = Counter()
    for li in listing_indices:
        try:
            obj = arr[li] if isinstance(li, int) else li
            if not isinstance(obj, dict) or 'id' not in obj:
                skipped['no id'] += 1
                continue

            # address
            addr = r(obj.get('address'))
            if not isinstance(addr, dict):
                skipped['address not a dict'] += 1
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

            # photos — up to _MAX_PHOTOS, resolved through the media CDN
            photo_paths = r(obj.get('photo_image_id'))
            photos: list[str] = []
            if isinstance(photo_paths, list):
                for pid in photo_paths:
                    if len(photos) >= _MAX_PHOTOS:
                        break
                    photo = _photo_url(r(pid))
                    if photo:
                        photos.append(photo)
            thumbnail = photos[0] if photos else None

            # url — the listing's identity: without one it can't be delivered or
            # marked seen.  A skip, so a renamed field fails the scrape (below).
            relative_url = r(obj.get('object_detail_page_relative_url'))
            if not relative_url:
                skipped['no url'] += 1
                continue
            full_url = 'https://www.funda.nl' + relative_url

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
            skipped[f'{type(e).__name__}: {e}'] += 1
            continue

    # One line per page, so a dropped listing is visible at the INFO log level.
    # A partial parse is still not a failure (see the ScrapeError check below).
    if skipped:
        reasons = ', '.join(f'{reason} ({n})' for reason, n in skipped.items())
        logger.warning(
            f'Skipped {sum(skipped.values())} of {len(listing_indices)} listings '
            f'while parsing: {reasons}'
        )

    # Funda counted matches but none survived parsing: a payload-shape change,
    # not a quiet market. (The 2026-11-05 ShallowRef outage looked exactly
    # like this for 15 days with no warning.)
    if total_count > 0 and not results:
        raise ScrapeError(
            f'Parsed 0 listings but Funda reports {total_count} matches — '
            'payload shape may have changed'
        )

    return results, total_count


# ---------------------------------------------------------------------------
# Public scraping interface
# ---------------------------------------------------------------------------

def scrape_funda(filters: dict, n_pages: int = 1) -> list[dict]:
    """Fetch listings from funda.nl matching *filters*.

    Scrapes up to *n_pages* pages (default 1).  Returns a list of normalised
    listing dicts — empty on a quiet day.  Individual unparseable listings are
    skipped, with one WARNING per page giving the reasons; a page that can't
    be fetched or read raises ScrapeError (nothing is marked seen, so the next
    run simply tries again).
    """
    all_listings: list[dict] = []

    for page in range(1, n_pages + 1):
        if page > 1:
            time.sleep(_PAGE_DELAY_SECONDS)

        url = _build_url(filters, page=page)
        logger.info(f'Fetching page {page}: {url}')

        try:
            response = requests.get(url, headers=_HEADERS, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            raise ScrapeError(f'HTTP error on page {page}: {e}') from e

        listings, total = _parse_nuxt_listings(response.text)
        logger.info(f'Page {page}: {len(listings)} listings (total available: {total})')
        all_listings.extend(listings)

        # stop early if we've fetched everything
        if len(all_listings) >= total or not listings:
            break

    # deduplicate by URL (every listing has one; the parser skips those without)
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for listing in all_listings:
        if listing['url'] not in seen_urls:
            seen_urls.add(listing['url'])
            unique.append(listing)

    return unique


def get_new_listings(filters: dict, n_pages: int = 1) -> list[dict]:
    """Return listings not yet seen.

    Does NOT mark listings as seen — the caller must invoke mark_seen(url)
    for each listing only after successful delivery to avoid silent loss.
    Raises ScrapeError if the scrape failed (see scrape_funda).
    """
    listings = scrape_funda(filters, n_pages=n_pages)
    seen = load_seen()
    return [l for l in listings if l.get('url') and l['url'] not in seen]
