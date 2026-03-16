import pytest
from funda_bot.scraper import load_seen, mark_seen, get_new_listings, _df_to_listings


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
# DataFrame normalisation
# ---------------------------------------------------------------------------

def test_df_to_listings_basic():
    """_df_to_listings maps DataFrame rows to our listing dict format."""
    import pandas as pd
    df = pd.DataFrame([{
        'url': 'https://funda.nl/detail/1/',
        'address': 'Teststraat 1, Utrecht',
        'city': 'Utrecht',
        'price': '450000',
        'living_area': '90',
        'num_of_rooms': '4',
        'energy_label': 'A',
    }])
    listings = _df_to_listings(df)
    assert len(listings) == 1
    item = listings[0]
    assert item['url'] == 'https://funda.nl/detail/1/'
    assert item['title'] == 'Teststraat 1, Utrecht'
    assert item['price'] == '450000'
    assert item['rooms'] == '4'
    assert item['energy_label'] == 'A'


def test_df_to_listings_skips_empty_url():
    """Rows with missing or nan URLs are skipped."""
    import pandas as pd
    df = pd.DataFrame([
        {'url': 'nan', 'address': 'A', 'city': 'X', 'price': '1', 'living_area': '1', 'num_of_rooms': '1', 'energy_label': ''},
        {'url': 'https://funda.nl/detail/2/', 'address': 'B', 'city': 'Y', 'price': '2', 'living_area': '2', 'num_of_rooms': '2', 'energy_label': 'B'},
    ])
    listings = _df_to_listings(df)
    assert len(listings) == 1
    assert listings[0]['url'] == 'https://funda.nl/detail/2/'


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
    monkeypatch.setattr('funda_bot.scraper.scrape_funda', lambda f: fake)

    new = get_new_listings({})
    assert len(new) == 2

    # manually mark one as seen (simulating a delivered notification)
    mark_seen('https://funda.nl/1')

    new2 = get_new_listings({})
    assert len(new2) == 1
    assert new2[0]['url'] == 'https://funda.nl/2'
