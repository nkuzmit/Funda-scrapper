import json
import os
import pytest
from types import SimpleNamespace

from funda_bot.scraper import scrape_funda, load_seen, save_seen, get_new_listings

SAMPLE_HTML = """<html><body>
<div class="search-result__item">
    <h2>Test House</h2>
    <span class="search-result-price">€ 123.456</span>
    <span class="search-result-location">Amsterdam</span>
    <span class="search-result-size">80 m²</span>
    <span class="search-result-rooms">3</span>
    <a href="/detail/123/">link</a>
    <img src="https://example.com/thumb.jpg"/>
</div>
</body></html>"""

class DummyResponse:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass


def test_scrape_funda(monkeypatch):
    def fake_get(url, headers=None):
        return DummyResponse(SAMPLE_HTML)
    monkeypatch.setattr('requests.get', fake_get)

    listings = scrape_funda('amsterdam')
    assert len(listings) == 1
    item = listings[0]
    assert item['title'] == 'Test House'
    assert item['price'] == '€ 123.456'
    assert 'amsterdam' in item['location'].lower()
    assert item['url'].endswith('/detail/123/')
    assert item['thumbnail'] == 'https://example.com/thumb.jpg'


def test_seen_storage(tmp_path, monkeypatch):
    # use a temp directory to avoid polluting repo
    monkeypatch.chdir(tmp_path)
    seen = load_seen()
    assert seen == set()
    save_seen({'foo', 'bar'})
    with open('seen_listings.json') as f:
        data = json.load(f)
    assert set(data) == {'foo', 'bar'}


def test_get_new_listings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # stub scrape_funda to return two entries
    def fake_scrape(city):
        return [
            {'url': 'a', 'title': 'A', 'price': '', 'location': '', 'size': '', 'rooms': '', 'thumbnail': None},
            {'url': 'b', 'title': 'B', 'price': '', 'location': '', 'size': '', 'rooms': '', 'thumbnail': None}
        ]
    monkeypatch.setattr('funda_bot.scraper.scrape_funda', fake_scrape)
    new = get_new_listings('city')
    assert len(new) == 2
    # second call should return empty (urls are saved)
    new2 = get_new_listings('city')
    assert new2 == []
