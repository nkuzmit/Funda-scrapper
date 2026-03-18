import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _parse_date(date_str: str) -> datetime | None:
    """Attempt to parse an ISO-like date string; return None on failure."""
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


def matches_filters(listing: dict, filters: dict) -> bool:
    """Determine whether a listing satisfies the provided filter set.

    The filters dict may contain keys:
    ``price_min`` ``price_max`` ``min_bedrooms`` ``keywords``
    ``publication_days`` ``energy_labels``
    (areas and publication_days are also applied upstream at scrape time).
    """
    title = listing.get('title', '?')
    try:
        price = listing.get('price') or 0
        price_min = filters.get('price_min') or 0
        price_max = filters.get('price_max') or float('inf')
        if price < price_min or price > price_max:
            logger.info(f"FILTERED {title!r}: price {price} not in [{price_min}, {price_max}]")
            return False

        bedrooms = listing.get('bedrooms') or 0
        if bedrooms < (filters.get('min_bedrooms') or 0):
            logger.info(f"FILTERED {title!r}: bedrooms {bedrooms} < {filters.get('min_bedrooms')}")
            return False

        labels = filters.get('energy_labels') or []
        if labels:
            if listing.get('energy_label') not in labels:
                logger.info(f"FILTERED {title!r}: energy_label {listing.get('energy_label')!r} not in list")
                return False

        # publication_date is extracted from the Nuxt payload (ISO 8601 string).
        # Listings without a date are passed through unchanged.
        if filters.get('publication_days'):
            pub = listing.get('publication_date')
            if pub:
                pub_date = _parse_date(pub)
                if pub_date:
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                    cutoff = datetime.now(timezone.utc) - timedelta(days=filters['publication_days'])
                    if pub_date < cutoff:
                        logger.info(f"FILTERED {title!r}: publication_date {pub} older than {filters['publication_days']} days")
                        return False

        kw_list = filters.get('keywords') or []
        if kw_list:
            title_lower = listing.get('title', '').lower()
            if not any(kw.lower() in title_lower for kw in kw_list):
                logger.info(f"FILTERED {title!r}: no keyword match")
                return False

        logger.info(f"PASSED {title!r}")
        return True
    except Exception as e:
        logger.error(f"Error matching filters for {title!r}: {e}")
        return False
