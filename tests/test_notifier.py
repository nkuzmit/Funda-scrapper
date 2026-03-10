import pytest
from funda_bot.notifier import send_telegram_message, notify_listing

class DummyResp:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {'ok': True}
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP error")
    def json(self):
        return self._data


def test_send_message(monkeypatch):
    calls = []
    def fake_post(url, data=None):
        calls.append((url, data))
        return DummyResp()
    monkeypatch.setattr('requests.post', fake_post)

    res = send_telegram_message('token', 'chat', 'hi')
    assert res['ok']
    assert len(calls) == 1
    assert 'sendMessage' in calls[0][0]
    assert calls[0][1]['text'] == 'hi'

    # test photo
    calls.clear()
    res2 = send_telegram_message('token', 'chat', 'hi', photo_url='http://img')
    assert res2['ok']
    assert len(calls) == 1
    assert 'sendPhoto' in calls[0][0]
    assert calls[0][1]['photo'] == 'http://img'


def test_notify_listing(monkeypatch):
    sent = []
    def fake_send(bot_token, chat_id, message, photo_url=None):
        sent.append((bot_token, chat_id, message, photo_url))
    monkeypatch.setattr('funda_bot.notifier.send_telegram_message', fake_send)

    listing = {'title': 'T', 'price': 'P', 'location': 'L', 'size': 'S', 'rooms': 'R', 'url': 'U'}
    notify_listing('tok', 'cid', listing)
    assert sent
    bot, chat, msg, photo = sent[0]
    assert '🏠 T' in msg
    assert photo is None
