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


def _telegram_400(description: str):
    """Build the HTTPError requests raises for a Telegram 400 with *description*."""
    import requests
    resp = requests.Response()
    resp.status_code = 400
    resp._content = ('{"ok":false,"error_code":400,"description":"%s"}' % description).encode()
    return requests.HTTPError('400 Client Error: Bad Request', response=resp)


def test_telegram_falls_back_to_text_when_photos_fail(monkeypatch):
    """If the album is rejected, the listing still goes out as a plain message."""
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(url)
        if 'sendMessage' not in url:
            raise _telegram_400('Bad Request: wrong type of the web page content')
        class R:
            def raise_for_status(self): pass
        return R()

    monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
    monkeypatch.setattr('funda_bot.notifier._RETRY_DELAY', 0)
    listing = {**LISTING, 'photos': ['https://example.com/a.jpg', 'https://example.com/b.jpg']}
    result = TelegramNotifier('token', 'chat123').notify(listing)

    assert result is True
    assert 'sendMediaGroup' in calls[0]
    assert 'sendMessage' in calls[-1]


def _album_calls(monkeypatch, reject):
    """Patch requests.post; reject(media_urls) returns a Telegram description to fail with, or None."""
    import json
    sent = []

    def fake_post(url, data=None, timeout=None):
        if 'sendMediaGroup' in url:
            media = [m['media'] for m in json.loads(data['media'])]
        elif 'sendPhoto' in url:
            media = [data['photo']]
        else:
            media = []
        sent.append(media)
        description = reject(media)
        if description:
            raise _telegram_400(description)
        class R:
            def raise_for_status(self): pass
        return R()

    monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
    return sent


def _reject_photo(bad_url):
    """A Telegram that can't fetch *bad_url*, reporting it by 1-based album position."""
    def reject(media):
        if bad_url in media and len(media) > 1:
            pos = media.index(bad_url) + 1
            return f'Bad Request: failed to send message #{pos} with the error message \\"WEBPAGE_CURL_FAILED\\"'
        return None
    return reject


def test_telegram_rejected_photo_is_replaced_by_a_spare(monkeypatch):
    """8 photos: 6 sent; when #3 is rejected it is dropped and spare #7 moves up."""
    photos = [f'https://example.com/{i}.jpg' for i in range(1, 9)]
    sent = _album_calls(monkeypatch, _reject_photo(photos[2]))
    result = TelegramNotifier('token', 'chat123').notify({**LISTING, 'photos': photos})

    assert result is True
    assert sent[0] == photos[:6]
    assert sent[1] == photos[:2] + photos[3:7]


def test_telegram_rejected_photo_without_spares_sends_fewer(monkeypatch):
    """4 photos, #2 rejected, no spares: the album goes out with the other 3."""
    photos = [f'https://example.com/{i}.jpg' for i in range(1, 5)]
    sent = _album_calls(monkeypatch, _reject_photo(photos[1]))
    result = TelegramNotifier('token', 'chat123').notify({**LISTING, 'photos': photos})

    assert result is True
    assert sent == [photos, [photos[0], photos[2], photos[3]]]


def test_telegram_sends_at_most_six_photos(monkeypatch):
    photos = [f'https://example.com/{i}.jpg' for i in range(1, 11)]
    sent = _album_calls(monkeypatch, lambda media: None)
    TelegramNotifier('token', 'chat123').notify({**LISTING, 'photos': photos})
    assert sent == [photos[:6]]


def test_permanent_4xx_is_not_retried_but_5xx_and_429_are(monkeypatch):
    """A 400 fails the same way every time; 5xx and 429 are worth retrying."""
    import requests
    from funda_bot.notifier import _request_with_retry

    def failing_post(status):
        calls = []
        def fake_post(url, data=None, timeout=None):
            calls.append(url)
            resp = requests.Response()
            resp.status_code = status
            resp._content = b'{}'
            raise requests.HTTPError(f'{status} error', response=resp)
        return calls, fake_post

    monkeypatch.setattr('funda_bot.notifier._RETRY_DELAY', 0)
    for status, expected_calls in ((400, 1), (429, 3), (502, 3)):
        calls, fake_post = failing_post(status)
        monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
        response, error = _request_with_retry('https://example.com', data={'x': 1})
        assert response is None and error is not None
        assert len(calls) == expected_calls, status


def test_telegram_http_error_logs_response_body_and_photos(monkeypatch, caplog):
    """A Telegram 400 logs its description (token redacted) and the photo URLs sent."""
    import requests

    def fake_post(url, data=None, timeout=None):
        resp = requests.Response()
        resp.status_code = 400
        resp._content = b'{"ok":false,"description":"Bad Request: failed to send message #2"}'
        raise requests.HTTPError(f'400 Client Error: Bad Request for url: {url}', response=resp)

    monkeypatch.setattr('funda_bot.notifier.requests.post', fake_post)
    monkeypatch.setattr('funda_bot.notifier._RETRY_DELAY', 0)
    photos = ['https://example.com/a.jpg', 'https://example.com/b.jpg']
    notifier = TelegramNotifier('123:secret-token', 'chat123')
    with caplog.at_level('WARNING', logger='funda_bot.notifier'):
        result = notifier.notify({**LISTING, 'photos': photos})

    assert result is False
    assert 'failed to send message #2' in caplog.text
    assert 'https://example.com/b.jpg' in caplog.text
    assert 'secret-token' not in caplog.text


# ---------------------------------------------------------------------------
# EmailNotifier — HTML body (C17)
# ---------------------------------------------------------------------------

def test_email_html_escapes_listing_values():
    """Funda's strings go into HTML: markup characters must not break it (C17)."""
    from funda_bot.notifier import _format_html
    listing = {
        **LISTING,
        'title': 'Kerk & Zn <b>1</b>',
        'location': '3500 AA <Utrecht>',
        'url': 'https://funda.nl/detail/1/"onmouseover="x',
        'photos': ['https://example.com/a.jpg?w=1&h=2"x'],
    }
    body = _format_html(listing)
    assert 'Kerk &amp; Zn &lt;b&gt;1&lt;/b&gt;' in body
    assert '3500 AA &lt;Utrecht&gt;' in body
    assert 'href="https://funda.nl/detail/1/&quot;onmouseover=&quot;x"' in body
    assert 'src="https://example.com/a.jpg?w=1&amp;h=2&quot;x"' in body
    assert '<b>1</b>' not in body and '"onmouseover' not in body


def test_email_html_plain_listing_is_unchanged():
    """Ordinary values render exactly as before the escaping."""
    from funda_bot.notifier import _format_html
    body = _format_html({**LISTING, 'photos': ['https://example.com/a.jpg'], 'energy_label': None})
    assert '<h2>🏠 Teststraat 1</h2>' in body
    assert '<td>€ 450.000</td>' in body
    assert '<td>90 m²</td>' in body
    assert '<td>3 bedrooms / 4 total</td>' in body
    assert '<td>N/A</td>' in body
    assert '<a href="https://funda.nl/detail/1/">' in body
    assert '<img src="https://example.com/a.jpg" ' in body


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


@pytest.mark.parametrize('status', [400, 502])   # rejected once / retried, then given up
def test_whatsapp_failure_log_redacts_credentials(monkeypatch, caplog, status):
    """CallMeBot takes the API key and phone as GET params, so requests puts
    them in its error text (review C5). Neither may reach the log."""
    import requests

    def fake_get(url, params=None, timeout=None):
        full = requests.Request('GET', url, params=params).prepare().url
        resp = requests.Response()
        resp.status_code = status
        raise requests.HTTPError(f'{status} Client Error: Bad Request for url: {full}', response=resp)

    monkeypatch.setattr('funda_bot.notifier.requests.get', fake_get)
    monkeypatch.setattr('funda_bot.notifier._RETRY_DELAY', 0)
    with caplog.at_level('WARNING', logger='funda_bot.notifier'):
        assert WhatsAppNotifier('+31612345678', 'SECRETkey123').notify(LISTING) is False

    assert caplog.records
    assert 'SECRETkey123' not in caplog.text
    assert '31612345678' not in caplog.text
    assert 'apikey=<redacted>' in caplog.text and 'phone=<redacted>' in caplog.text


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


@pytest.mark.parametrize('config', [
    {'notifications': {'channels': None}},   # "channels:" left empty in YAML
    {'notifications': None},                 # "notifications:" left empty
    {},
])
def test_build_notifiers_empty_channels_means_none(config):
    """An empty key means no channels, not a TypeError at startup (C13)."""
    assert build_notifiers(config) == []


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
