from datetime import datetime, timedelta, timezone

from funda_bot.filters import matches_filters


def test_matches_filters_price():
    listing = {'price': 500000, 'bedrooms': 3, 'title': 'Nice apartment'}
    filters = {'price_min': 100000, 'price_max': 600000, 'min_bedrooms': 2, 'keywords': []}
    assert matches_filters(listing, filters)

    filters['price_min'] = 600001
    assert not matches_filters(listing, filters)


def test_matches_filters_bedrooms():
    listing = {'price': 500000, 'bedrooms': 2, 'title': 'A'}
    filters = {'price_min': 0, 'price_max': 1000000, 'min_bedrooms': 3, 'keywords': []}
    assert not matches_filters(listing, filters)


def test_matches_filters_keywords():
    listing = {'price': 200000, 'bedrooms': 2, 'title': 'Lovely studio in centrum'}
    filters = {'price_min': 0, 'price_max': 300000, 'min_bedrooms': 1, 'keywords': ['centrum']}
    assert matches_filters(listing, filters)
    filters['keywords'] = ['garden']
    assert not matches_filters(listing, filters)


def test_matches_filters_energy_labels():
    listing = {'price': 100000, 'bedrooms': 1, 'title': 'A', 'energy_label': 'A++'}
    filters = {'price_min': 0, 'price_max': 200000, 'min_bedrooms': 0,
               'keywords': [], 'energy_labels': ['A++']}
    assert matches_filters(listing, filters)

    filters['energy_labels'] = ['B', 'C']
    assert not matches_filters(listing, filters)


def test_matches_filters_publication_days():
    listing = {
        'price': 100000, 'bedrooms': 1, 'title': 'A',
        'energy_label': 'A++',
        'publication_date': datetime.now(timezone.utc).isoformat(),
    }
    filters = {'price_min': 0, 'price_max': 200000, 'min_bedrooms': 0,
               'keywords': [], 'energy_labels': ['A++'], 'publication_days': 1}
    assert matches_filters(listing, filters)

    # listing published 5 days ago — should be filtered out
    listing['publication_date'] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    assert not matches_filters(listing, filters)


def test_matches_filters_no_date_passes_through():
    """Listings without a publication_date are not filtered out."""
    listing = {'price': 100000, 'bedrooms': 1, 'title': 'A', 'publication_date': None}
    filters = {'price_min': 0, 'price_max': 200000, 'min_bedrooms': 0,
               'keywords': [], 'publication_days': 1}
    assert matches_filters(listing, filters)


def test_matches_filters_naive_publication_date():
    """Naive datetime strings from the Funda payload are handled without TypeError."""
    listing = {
        'price': 100000, 'bedrooms': 1, 'title': 'A',
        'publication_date': datetime.now().isoformat(),  # naive — no timezone
    }
    filters = {'price_min': 0, 'price_max': 200000, 'min_bedrooms': 0,
               'keywords': [], 'publication_days': 3}
    assert matches_filters(listing, filters)
