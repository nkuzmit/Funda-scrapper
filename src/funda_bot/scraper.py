import sqlite3
import logging
import time
from pathlib import Path
from funda_scraper import FundaScraper

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent.parent.parent / 'seen_listings.db'
_AREA_DELAY = 2  # seconds between area requests to be polite to the server


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
# Scraping
# ---------------------------------------------------------------------------

def _df_to_listings(df) -> list[dict]:
    """Normalise a funda-scraper DataFrame row to our internal listing format."""
    listings = []
    for _, row in df.iterrows():
        url = str(row.get('url', ''))
        if not url or url in ('nan', 'None'):
            continue
        listings.append({
            'title': str(row.get('address', 'Unknown')),
            'price': str(row.get('price', 'Unknown')),
            'location': str(row.get('city', row.get('address', 'Unknown'))),
            'size': str(row.get('living_area', row.get('size', 'Unknown'))),
            'rooms': str(row.get('num_of_rooms', 'Unknown')),
            'energy_label': str(row.get('energy_label', '')) or None,
            'publication_date': None,  # no longer available from Funda without login
            'url': url,
            'thumbnail': None,
        })
    return listings


def scrape_funda(filters: dict) -> list[dict]:
    """Scrape funda.nl for each configured area using the funda-scraper library.

    Loops over ``filters['areas']``, waits _AREA_DELAY seconds between each
    request, and returns a combined list of normalised listing dicts.
    """
    areas = filters.get('areas') or []
    days_since = filters.get('publication_days')
    min_price = filters.get('price_min')
    max_price = filters.get('price_max')

    all_listings: list[dict] = []

    for i, area in enumerate(areas):
        if i > 0:
            time.sleep(_AREA_DELAY)
        try:
            scraper = FundaScraper(
                area=area,
                want_to='buy',
                find_sold=False,
                page_start=1,
                n_pages=1,
                min_price=min_price,
                max_price=max_price,
                days_since=days_since,
            )
            df = scraper.run(raw_data=False, save=False)
            if df is not None and not df.empty:
                all_listings.extend(_df_to_listings(df))
                logger.info(f"Area '{area}': {len(df)} listings fetched")
            else:
                logger.info(f"Area '{area}': no listings returned")
        except Exception as e:
            logger.error(f"Error scraping area '{area}': {e}")
            continue

    return all_listings


def get_new_listings(filters: dict) -> list[dict]:
    """Return listings not yet seen.

    Does NOT mark listings as seen — the caller must invoke mark_seen(url)
    for each listing only after successful delivery to avoid silent loss.
    """
    listings = scrape_funda(filters)
    seen = load_seen()
    return [l for l in listings if l['url'] not in seen]
