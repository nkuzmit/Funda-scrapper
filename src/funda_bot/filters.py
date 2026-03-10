import re
import logging

logger = logging.getLogger(__name__)


def parse_price(price_str: str) -> int:
    """Parse a price string to an integer (e.g. '€ 529.000 k.k.' -> 529000).

    Non-numeric characters are stripped. If parsing fails, return 0.
    """
    try:
        cleaned = re.sub(r'[€\s\.k\.]+', '', price_str)
        return int(cleaned)
    except Exception:
        logger.debug(f"Failed to parse price from '{price_str}'")
        return 0


def parse_rooms(rooms_str: str) -> int:
    """Extract the first integer from a rooms string; returns 0 on failure."""
    try:
        return int(re.search(r'\d+', rooms_str).group())
    except Exception:
        logger.debug(f"Failed to parse rooms from '{rooms_str}'")
        return 0


from datetime import datetime, timedelta


def _parse_date(date_str: str) -> datetime | None:
    """Attempt to parse an ISO‑like date string; return None on failure."""
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


def matches_filters(listing: dict, filters: dict) -> bool:
    """Determine whether a listing satisfies the provided filter set.

    The filters dict may contain keys:
    ``price_min`` ``price_max`` ``min_bedrooms`` ``keywords``
    ``publication_days`` ``energy_labels``
    (areas are applied when building the URL).
    """
    try:
        price = parse_price(listing.get('price', ''))
        if price < filters.get('price_min', 0) or price > filters.get('price_max', float('inf')):
            return False

        rooms = parse_rooms(listing.get('rooms', ''))
        if rooms < filters.get('min_bedrooms', 0):
            return False

        # energy label filter if listing contains it
        labels = filters.get('energy_labels') or []
        if labels:
            if listing.get('energy_label') not in labels:
                return False

        if filters.get('publication_days'):
            pub = listing.get('publication_date')
            if pub:
                pub_date = _parse_date(pub)
                if pub_date:
                    cutoff = datetime.now() - timedelta(days=filters['publication_days'])
                    if pub_date < cutoff:
                        return False

        kw_list = filters.get('keywords') or []
        if kw_list:
            title_lower = listing.get('title', '').lower()
            if not any(kw.lower() in title_lower for kw in kw_list):
                return False

        return True
    except Exception as e:
        logger.error(f"Error matching filters: {e}")
        return False
