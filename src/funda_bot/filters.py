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


def matches_filters(listing: dict, filters: dict) -> bool:
    """Determine whether a listing satisfies the provided filter set.

    The filters dict is expected to contain keys:
    ``min_price`` ``max_price`` ``min_bedrooms`` ``keywords``
    (city is handled elsewhere).
    """
    try:
        price = parse_price(listing.get('price', ''))
        if price < filters.get('min_price', 0) or price > filters.get('max_price', float('inf')):
            return False

        rooms = parse_rooms(listing.get('rooms', ''))
        if rooms < filters.get('min_bedrooms', 0):
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
