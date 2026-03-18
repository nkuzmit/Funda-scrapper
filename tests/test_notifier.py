import pytest
from funda_bot.notifier import TelegramNotifier, EmailNotifier, WhatsAppNotifier, build_notifiers


LISTING = {
    'title': 'Teststraat 1',
    'price': 450000,
    'location': 'Utrecht',
    'size': 90,
    'rooms': 4,
    'bedrooms': 3,
    'url': 'https://funda.nl/detail/1/',
    'photos': [],
    'energy_label': 'A',
}


# ---------------------------------------------------------------------------
# TelegramNotifier
# ---------------------------------------------------------------------------

def test_telegram_notify_success(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append((url, data))
        class R:
            def raise_for_status(self): pass
        return R()

    monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
    notifier = TelegramNotifier('token', 'chat123')
    result = notifier.notify(LISTING)

    assert result is True
    assert len(calls) == 1
    assert 'sendMessage' in calls[0][0]
    assert calls[0][1]['chat_id'] == 'chat123'
    assert 'Teststraat 1' in calls[0][1]['text']


def test_telegram_notify_with_photo(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append((url, data))
        class R:
            def raise_for_status(self): pass
        return R()

    monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
    listing_with_photo = {**LISTING, 'photos': ['https://example.com/photo.jpg']}
    notifier = TelegramNotifier('token', 'chat123')
    result = notifier.notify(listing_with_photo)

    assert result is True
    assert 'sendPhoto' in calls[0][0]
    assert calls[0][1]['photo'] == 'https://example.com/photo.jpg'


def test_telegram_notify_failure_returns_false(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        raise ConnectionError("network down")

    monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
    monkeypatch.setattr('funda_bot.notifier._RETRY_DELAY', 0)
    notifier = TelegramNotifier('token', 'chat123')
    result = notifier.notify(LISTING)
    assert result is False


# ---------------------------------------------------------------------------
# WhatsAppNotifier
# ---------------------------------------------------------------------------

def test_whatsapp_notify_success(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        class R:
            def raise_for_status(self): pass
        return R()

    monkeypatch.setattr('funda_bot.notifier.requests.get', fake_get)
    notifier = WhatsAppNotifier('+31600000000', 'testapikey')
    result = notifier.notify(LISTING)

    assert result is True
    assert calls[0]['phone'] == '+31600000000'
    assert calls[0]['apikey'] == 'testapikey'
    assert 'Teststraat 1' in calls[0]['text']


# ---------------------------------------------------------------------------
# build_notifiers factory
# ---------------------------------------------------------------------------

def test_build_notifiers_telegram(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'tok')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'cid')
    config = {'notifications': {'channels': ['telegram']}}
    notifiers = build_notifiers(config)
    assert len(notifiers) == 1
    assert isinstance(notifiers[0], TelegramNotifier)


def test_build_notifiers_missing_env_skips_channel(monkeypatch):
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.delenv('TELEGRAM_CHAT_ID', raising=False)
    config = {'notifications': {'channels': ['telegram']}}
    notifiers = build_notifiers(config)
    assert len(notifiers) == 0


def test_build_notifiers_multiple_channels(monkeypatch):
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'tok')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', 'cid')
    monkeypatch.setenv('WHATSAPP_PHONE', '+31600000000')
    monkeypatch.setenv('WHATSAPP_APIKEY', 'key')
    config = {'notifications': {'channels': ['telegram', 'whatsapp']}}
    notifiers = build_notifiers(config)
    assert len(notifiers) == 2
    types = {type(n) for n in notifiers}
    assert TelegramNotifier in types
    assert WhatsAppNotifier in types
