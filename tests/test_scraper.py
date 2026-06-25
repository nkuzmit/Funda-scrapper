import json
from pathlib import Path

import pytest
from funda_bot.scraper import load_seen, mark_seen, get_new_listings, _photo_url, _parse_nuxt_listings, _build_url

_FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def _html(payload) -> str:
    """Wrap a payload (list) as a minimal Funda-shaped HTML page."""
    return f'<html><body><script>{json.dumps(payload)}</script></body></html>'


def _load_fixture(name: str):
    with open(_FIXTURE_DIR / name) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# _build_url — new filter params appear in the search URL
# ---------------------------------------------------------------------------

def test_build_url_floor_area():
    url = _build_url({'floor_area_min': 90, 'floor_area_max': 130})
    assert 'floor_area="90-130"' in url


def test_build_url_bedrooms():
    url = _build_url({'min_bedrooms': 2})
    assert 'bedrooms="2-"' in url


def test_build_url_amenities():
    url = _build_url({'amenities': ['bathtub', 'parking']})
    assert 'amenities=["bathtub","parking"]' in url


def test_build_url_floor_area_min_only():
    url = _build_url({'floor_area_min': 90})
    assert 'floor_area="90-"' in url


# ---------------------------------------------------------------------------
# _parse_nuxt_listings — fixture-based tests guard against Funda payload changes
# ---------------------------------------------------------------------------

def test_parse_nuxt_happy_path():
    """Fixture payload round-trips correctly through the Nuxt parser."""
    payload = _load_fixture('nuxt_payload.json')
    listings, total = _parse_nuxt_listings(_html(payload))

    assert total == 42
    assert len(listings) == 1
    l = listings[0]
    assert l['title'] == 'Teststraat 1A'
    assert l['price'] == 450000
    assert l['location'] == '1234 AB Amsterdam'
    assert l['size'] == 90
    assert l['bedrooms'] == 2
    assert l['rooms'] == 4
    assert l['energy_label'] == 'A'
    assert l['url'] == 'https://www.funda.nl/koop/amsterdam/huis-12345678-teststraat-1a/'


def test_parse_nuxt_photo_filtering():
    """tiara-media and valentina_media photos are kept; agent-logo paths are dropped."""
    payload = _load_fixture('nuxt_payload.json')
    listings, _ = _parse_nuxt_listings(_html(payload))
    photos = listings[0]['photos']

    assert len(photos) == 2
    assert photos[0] == 'https://cloud.funda.nl/tiara-media/abc123/def456?options=width=720'
    assert photos[1] == 'https://cloud.funda.nl/valentina_media/old/path.jpg'
    assert listings[0]['thumbnail'] == photos[0]


def test_parse_nuxt_energy_label_none():
    """energy_label field is None (not the string 'None') when absent from the listing."""
    payload = _load_fixture('nuxt_payload.json')
    payload[4]['energy_label'] = None
    listings, _ = _parse_nuxt_listings(_html(payload))
    assert listings[0]['energy_label'] is None


def test_parse_nuxt_bot_challenge():
    """Bot-challenge page returns empty results without raising."""
    html = '<html><body>Je bent bijna op de pagina die je zocht</body></html>'
    listings, total = _parse_nuxt_listings(html)
    assert listings == [] and total == 0


def test_parse_nuxt_no_payload():
    """Page with no matching script tag returns empty results without raising."""
    html = '<html><body><script>var x = 1;</script></body></html>'
    listings, total = _parse_nuxt_listings(html)
    assert listings == [] and total == 0


def test_parse_nuxt_empty_listing_list():
    """Payload with zero listings returns empty list; total still parses correctly."""
    payload = _load_fixture('nuxt_payload.json')
    payload[3] = []  # clear listing index list; leave totalListingsCount alone
    listings, total = _parse_nuxt_listings(_html(payload))
    assert listings == [] and total == 42


# ---------------------------------------------------------------------------
# Photo URL construction (guards against Funda media-backend changes)
# ---------------------------------------------------------------------------

def test_photo_url_tiara_current_backend():
    """Current tiara-media paths build a sized cloud.funda.nl URL."""
    assert _photo_url('tiara-media/abc/def') == (
        'https://cloud.funda.nl/tiara-media/abc/def?options=width=720'
    )


def test_photo_url_valentina_legacy_backend():
    """Legacy valentina_media paths still resolve, unsized."""
    assert _photo_url('valentina_media/210/547/012.jpg') == (
        'https://cloud.funda.nl/valentina_media/210/547/012.jpg'
    )


def test_photo_url_unknown_is_dropped():
    """Unrecognised paths and non-strings are skipped, not crashed on."""
    assert _photo_url('office_logo/x') is None
    assert _photo_url(None) is None
    assert _photo_url(123) is None


# ---------------------------------------------------------------------------
# SQLite state helpers
# ---------------------------------------------------------------------------

def test_seen_storage(tmp_path, monkeypatch):
    """load_seen returns empty set initially; mark_seen persists a URL."""
    monkeypatch.setattr('funda_bot.scraper._DB_PATH', tmp_path / 'seen.db')
    seen = load_seen()
    assert seen == set()

    mark_seen('https://funda.nl/1')
    seen = load_seen()
    assert 'https://funda.nl/1' in seen


def test_mark_seen_idempotent(tmp_path, monkeypatch):
    """Calling mark_seen twice with the same URL does not raise."""
    monkeypatch.setattr('funda_bot.scraper._DB_PATH', tmp_path / 'seen.db')
    mark_seen('https://funda.nl/x')
    mark_seen('https://funda.nl/x')  # should not raise
    assert len(load_seen()) == 1


# ---------------------------------------------------------------------------
# get_new_listings
# ---------------------------------------------------------------------------

def test_get_new_listings_filters_seen(tmp_path, monkeypatch):
    """get_new_listings excludes URLs already in the seen database."""
    monkeypatch.setattr('funda_bot.scraper._DB_PATH', tmp_path / 'seen.db')

    fake = [
        {'url': 'https://funda.nl/1', 'title': 'A', 'price': '', 'location': '', 'size': '', 'rooms': '', 'thumbnail': None, 'energy_label': None, 'publication_date': None},
        {'url': 'https://funda.nl/2', 'title': 'B', 'price': '', 'location': '', 'size': '', 'rooms': '', 'thumbnail': None, 'energy_label': None, 'publication_date': None},
    ]
    monkeypatch.setattr('funda_bot.scraper.scrape_funda', lambda f, n_pages=1: fake)

    new = get_new_listings({})
    assert len(new) == 2

    # manually mark one as seen (simulating a delivered notification)
    mark_seen('https://funda.nl/1')

    new2 = get_new_listings({})
    assert len(new2) == 1
    assert new2[0]['url'] == 'https://funda.nl/2'
