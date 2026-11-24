import json
from pathlib import Path

import pytest
import requests
from funda_bot.scraper import (
    ScrapeError, load_seen, mark_seen, get_new_listings, scrape_funda,
    _photo_url, _parse_nuxt_listings, _build_url, _empty_ref_value,
)

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
    """Bot-challenge page is a failed scrape, not an empty result."""
    html = '<html><body>Je bent bijna op de pagina die je zocht</body></html>'
    with pytest.raises(ScrapeError, match='bot-challenge'):
        _parse_nuxt_listings(html)


def test_parse_nuxt_no_payload():
    """Page with no matching script tag is a failed scrape."""
    html = '<html><body><script>var x = 1;</script></body></html>'
    with pytest.raises(ScrapeError, match='Nuxt payload not found'):
        _parse_nuxt_listings(html)


def test_parse_nuxt_bad_json():
    html = '<html><body><script>[1, "fetchListings", oops]</script></body></html>'
    with pytest.raises(ScrapeError, match='Failed to parse Nuxt payload'):
        _parse_nuxt_listings(html)


def test_parse_nuxt_no_search_state():
    with pytest.raises(ScrapeError, match='Search state not found'):
        _parse_nuxt_listings(_html([{'fetchListings': None}]))


def test_parse_nuxt_listings_field_not_a_list():
    payload = _load_fixture('nuxt_payload.json')
    payload[3] = {'not': 'a list'}
    with pytest.raises(ScrapeError, match='Listings field is not a list'):
        _parse_nuxt_listings(_html(payload))


def test_parse_nuxt_shallowref_listings():
    """Listings wrapped in a single ShallowRef (Funda's shape since 2026-11-05) still parse.

    Unhandled, the wrapper leaked through as ['ShallowRef', idx], every element was
    skipped, and the scrape logged '0 listings (total available: N)' with N > 0.
    """
    payload = _load_fixture('nuxt_payload.json')
    payload[1] = ['ShallowRef', 3]  # was ShallowReactive -> Reactive -> [4]
    listings, total = _parse_nuxt_listings(_html(payload))
    assert total == 42
    assert len(listings) == 1
    assert listings[0]['title'] == 'Teststraat 1A'


def test_parse_nuxt_count_but_no_listings_raises():
    """An unknown wrapper (total > 0, 0 parsed) is a failed scrape, not a quiet day.

    This is the 2026-11-05 ShallowRef outage shape: every listing was skipped.
    """
    payload = _load_fixture('nuxt_payload.json')
    payload[1] = ['SomeFutureRef', 3]
    with pytest.raises(ScrapeError, match='Funda reports 42 matches'):
        _parse_nuxt_listings(_html(payload))


def test_parse_nuxt_empty_list_with_nonzero_total_raises():
    """An empty listings list while Funda reports matches is also a failure."""
    payload = _load_fixture('nuxt_payload.json')
    payload[3] = []  # clear listing index list; leave totalListingsCount at 42
    with pytest.raises(ScrapeError, match='Funda reports 42 matches'):
        _parse_nuxt_listings(_html(payload))


def test_parse_nuxt_quiet_day_is_not_a_failure(caplog):
    """A live 0-match page (saved 2026-11-24) returns ([], 0) without a warning.

    Its total is ['EmptyRef', i] -> the JSON text '0'.
    """
    caplog.set_level('WARNING', logger='funda_bot.scraper')
    quiet = _load_fixture('nuxt_payload_zero_match.json')
    assert _parse_nuxt_listings(_html(quiet)) == ([], 0)
    assert _skip_warnings(caplog) == []


@pytest.mark.parametrize('total_marker', [
    ['SomeFutureRef', 60],  # an unknown wrapper around the '0'
    ['EmptyRef', 146],      # 'null' -> None
    ['Ref', 4],             # true -> a bool, which Python counts as an int
    'forty-five',           # text, not a number
])
def test_parse_nuxt_total_not_a_number_raises(total_marker):
    """A total that isn't a whole number is a failed scrape, not a quiet day.

    Before 2026-11-24 it was read as 0, so a payload change that broke both the
    total and the listings looked exactly like a day with no matches.
    """
    payload = _load_fixture('nuxt_payload_zero_match.json')
    state = next(x for x in payload if isinstance(x, dict) and 'totalListingsCount' in x)
    payload[state['totalListingsCount']] = total_marker
    with pytest.raises(ScrapeError, match='Total listings count is not a number'):
        _parse_nuxt_listings(_html(payload))


@pytest.mark.parametrize('text, value', [
    ('0', 0), ('false', False), ('null', None), ('""', ''),
    ('_', None),                  # undefined
    ('0n', 0),                    # BigInt 0
    ('not json', 'not json'),     # Nuxt's reviver keeps it as it is
])
def test_empty_ref_value_mirrors_nuxt(text, value):
    assert _empty_ref_value(text) == value


def test_parse_nuxt_empty_ref_in_a_listing_field_is_decoded():
    """An EmptyRef on a listing field reads as its value, not as the marker list.

    Not seen inside listings on the live pages (2026-11-24); unwrap() decodes it
    wherever it appears, like Nuxt does.
    """
    payload = _load_fixture('nuxt_payload.json')
    n = len(payload)
    payload += ['null', ['EmptyRef', n]]
    payload[4]['energy_label'] = n + 1
    listings, _ = _parse_nuxt_listings(_html(payload))
    assert listings[0]['energy_label'] is None


def _skip_warnings(caplog):
    return [
        r.getMessage() for r in caplog.records
        if r.name == 'funda_bot.scraper' and r.levelname == 'WARNING'
    ]


def test_parse_nuxt_skipped_listings_logged_as_one_warning(caplog):
    """Listings the parser drops are counted by reason in one WARNING (review C4).

    Before, they were skipped silently or at DEBUG, below the INFO log level.
    """
    payload = _load_fixture('nuxt_payload.json')
    n = len(payload)
    payload += [
        {'no_id_here': 1},                   # n:   not a listing
        {'id': 2, 'address': 'not-a-dict'},  # n+1: address not a dict
    ]
    payload[3] = [4, n, n + 1, 9999]         # 9999: index out of range -> exception
    caplog.set_level('WARNING', logger='funda_bot.scraper')

    listings, _ = _parse_nuxt_listings(_html(payload))

    assert [l['title'] for l in listings] == ['Teststraat 1A']
    assert _skip_warnings(caplog) == [
        'Skipped 3 of 4 listings while parsing: no id (1), address not a dict (1), '
        'IndexError: list index out of range (1)'
    ]


def test_parse_nuxt_clean_page_logs_no_warning(caplog):
    caplog.set_level('WARNING', logger='funda_bot.scraper')
    _parse_nuxt_listings(_html(_load_fixture('nuxt_payload.json')))
    assert _skip_warnings(caplog) == []


def test_parse_nuxt_all_skipped_logs_reasons_before_raising(caplog):
    """On the outage shape the log says why every listing was dropped."""
    payload = _load_fixture('nuxt_payload.json')
    payload[1] = ['SomeFutureRef', 3]
    caplog.set_level('WARNING', logger='funda_bot.scraper')
    with pytest.raises(ScrapeError):
        _parse_nuxt_listings(_html(payload))
    assert _skip_warnings(caplog) == ['Skipped 2 of 2 listings while parsing: no id (2)']


def test_parse_nuxt_listing_without_url_is_a_logged_skip(caplog):
    """A listing with no URL can't be delivered or marked seen: skip it visibly.

    Before, it was parsed with url None and then dropped silently by
    scrape_funda's duplicate check.
    """
    payload = _load_fixture('nuxt_payload.json')
    n = len(payload)
    payload.append(dict(payload[4], id=2, object_detail_page_relative_url=None))
    payload[3] = [4, n]
    caplog.set_level('WARNING', logger='funda_bot.scraper')

    listings, _ = _parse_nuxt_listings(_html(payload))

    assert [l['url'] for l in listings] == [
        'https://www.funda.nl/koop/amsterdam/huis-12345678-teststraat-1a/'
    ]
    assert _skip_warnings(caplog) == ['Skipped 1 of 2 listings while parsing: no url (1)']


def test_parse_nuxt_no_listing_has_url_raises():
    """A renamed URL field would strip every listing: a failure, not a quiet day."""
    payload = _load_fixture('nuxt_payload.json')
    del payload[4]['object_detail_page_relative_url']
    with pytest.raises(ScrapeError, match='Funda reports 42 matches'):
        _parse_nuxt_listings(_html(payload))


def test_scrape_funda_http_error_raises(monkeypatch):
    """A network error is a failed scrape (no real request is made)."""
    def boom(*args, **kwargs):
        raise requests.ConnectionError('connection refused')
    monkeypatch.setattr('funda_bot.scraper.requests.get', boom)
    with pytest.raises(ScrapeError, match='HTTP error on page 1'):
        scrape_funda({'areas': ['utrecht/oudwijk']})


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
