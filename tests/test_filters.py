import pytest
from funda_bot.filters import parse_price, parse_rooms, matches_filters


def test_parse_price():
    assert parse_price('€ 529.000 k.k.') == 529000
    assert parse_price('€ 1.234.567') == 1234567
    assert parse_price('Not a price') == 0


def test_parse_rooms():
    assert parse_rooms('4 kamers') == 4
    assert parse_rooms('2') == 2
    assert parse_rooms('geen') == 0


def test_matches_filters_basic():
    listing = {'price': '€ 500.000', 'rooms': '3', 'title': 'Nice apartment'}
    filters = {'min_price': 100000, 'max_price': 600000, 'min_bedrooms': 2, 'keywords': []}
    assert matches_filters(listing, filters)

    filters['min_price'] = 600001
    assert not matches_filters(listing, filters)

    filters = {'min_price': 0, 'max_price': 1000000, 'min_bedrooms': 4, 'keywords': []}
    assert not matches_filters(listing, filters)


def test_matches_filters_keywords():
    listing = {'price': '€ 200.000', 'rooms': '2', 'title': 'Lovely studio in centrum'}
    filters = {'min_price': 0, 'max_price': 300000, 'min_bedrooms': 1, 'keywords': ['centrum']}
    assert matches_filters(listing, filters)
    filters['keywords'] = ['garden']
    assert not matches_filters(listing, filters)
