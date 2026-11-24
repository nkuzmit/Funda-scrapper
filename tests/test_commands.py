"""Unit tests for commands.py (commands, sending, saving, polling) and main.py
(scrape_and_notify, the failure alert, load_config). No real Telegram or Funda call."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from funda_bot.commands import handle_command, _CONFIG_LOCK


def _make_config(min_bedrooms=2, price_min=400000, price_max=800000, pub_days=3):
    return {
        'filters': {
            'min_bedrooms': min_bedrooms,
            'price_min': price_min,
            'price_max': price_max,
            'publication_days': pub_days,
            'areas': [],
            'energy_labels': [],
            'keywords': [],
            'floor_area_min': None,
            'floor_area_max': None,
            'amenities': [],
        }
    }


@pytest.fixture()
def ctx():
    """Return (config, send_mock) with _send and _save_config patched out."""
    config = _make_config()
    send = MagicMock()
    with (
        patch('funda_bot.commands._send', send),
        patch('funda_bot.commands._save_config'),
    ):
        yield config, send


# ---------------------------------------------------------------------------
# /setrooms
# ---------------------------------------------------------------------------

def test_setrooms_bad_input_sends_hint(ctx):
    config, send = ctx
    handle_command('/setrooms two', config, 'tok', '123', MagicMock())
    send.assert_called_once()
    assert 'Usage' in send.call_args[0][2]


def test_setrooms_bad_input_leaves_config_unchanged(ctx):
    config, send = ctx
    handle_command('/setrooms two', config, 'tok', '123', MagicMock())
    assert config['filters']['min_bedrooms'] == 2


def test_setrooms_valid_input_updates_config(ctx):
    config, send = ctx
    with patch('funda_bot.commands._save_config') as save:
        handle_command('/setrooms 4', config, 'tok', '123', MagicMock())
        assert config['filters']['min_bedrooms'] == 4
        save.assert_called_once()


# ---------------------------------------------------------------------------
# /setprice
# ---------------------------------------------------------------------------

def test_setprice_bad_first_arg_sends_hint(ctx):
    config, send = ctx
    handle_command('/setprice abc 900000', config, 'tok', '123', MagicMock())
    send.assert_called_once()
    assert 'Usage' in send.call_args[0][2]


def test_setprice_bad_second_arg_sends_hint(ctx):
    config, send = ctx
    handle_command('/setprice 500000 abc', config, 'tok', '123', MagicMock())
    send.assert_called_once()
    assert 'Usage' in send.call_args[0][2]


def test_setprice_bad_input_leaves_config_unchanged(ctx):
    config, send = ctx
    handle_command('/setprice abc 900000', config, 'tok', '123', MagicMock())
    assert config['filters']['price_min'] == 400000
    assert config['filters']['price_max'] == 800000


def test_setprice_valid_input_updates_config(ctx):
    config, send = ctx
    with patch('funda_bot.commands._save_config') as save:
        handle_command('/setprice 500000 null', config, 'tok', '123', MagicMock())
        assert config['filters']['price_min'] == 500000
        assert config['filters']['price_max'] is None
        save.assert_called_once()


# ---------------------------------------------------------------------------
# /setdate
# ---------------------------------------------------------------------------

def test_setdate_bad_input_sends_hint(ctx):
    config, send = ctx
    handle_command('/setdate three', config, 'tok', '123', MagicMock())
    send.assert_called_once()
    assert 'Usage' in send.call_args[0][2]


def test_setdate_bad_input_leaves_config_unchanged(ctx):
    config, send = ctx
    handle_command('/setdate three', config, 'tok', '123', MagicMock())
    assert config['filters']['publication_days'] == 3


def test_setdate_valid_input_updates_config(ctx):
    config, send = ctx
    with patch('funda_bot.commands._save_config') as save:
        handle_command('/setdate 7', config, 'tok', '123', MagicMock())
        assert config['filters']['publication_days'] == 7
        save.assert_called_once()


# ---------------------------------------------------------------------------
# /setfloor
# ---------------------------------------------------------------------------

def test_setfloor_bad_input_sends_hint(ctx):
    config, send = ctx
    handle_command('/setfloor abc 130', config, 'tok', '123', MagicMock())
    send.assert_called_once()
    assert 'Usage' in send.call_args[0][2]


def test_setfloor_bad_input_leaves_config_unchanged(ctx):
    config, send = ctx
    handle_command('/setfloor abc 130', config, 'tok', '123', MagicMock())
    assert config['filters']['floor_area_min'] is None


def test_setfloor_valid_input_updates_config(ctx):
    config, send = ctx
    with patch('funda_bot.commands._save_config') as save:
        handle_command('/setfloor 90 130', config, 'tok', '123', MagicMock())
        assert config['filters']['floor_area_min'] == 90
        assert config['filters']['floor_area_max'] == 130
        save.assert_called_once()


# ---------------------------------------------------------------------------
# /setlabel
# ---------------------------------------------------------------------------

def test_setlabel_normalises_to_uppercase(ctx):
    config, send = ctx
    with patch('funda_bot.commands._save_config'):
        handle_command('/setlabel a b+ c', config, 'tok', '123', MagicMock())
    assert config['filters']['energy_labels'] == ['A', 'B+', 'C']


# ---------------------------------------------------------------------------
# /run
# ---------------------------------------------------------------------------

@pytest.fixture()
def main_mod(monkeypatch):
    """The main module, with the consecutive-failure counter reset to 0.

    Tests patch main.get_new_listings, never funda_bot.scraper's — patching the
    latter can miss main's own reference and make a real Funda request.
    """
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
    import main
    monkeypatch.setattr(main, '_failed_runs', 0)
    return main


def _run_result(delivered=0, failed=0, error=None):
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
    from main import RunResult
    return RunResult(delivered, failed, error)


def test_run_reports_failed_deliveries(ctx):
    """A listing that failed to send must not be reported as 'All caught up'."""
    config, send = ctx
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=_run_result(0, 1)))
    last = send.call_args_list[-1][0][2]
    assert 'could not be sent' in last and 'All caught up' not in last


def test_run_reports_failed_scrape(ctx):
    """A failed scrape must not be reported as 'All caught up'."""
    config, send = ctx
    result = _run_result(error='Funda returned a bot-challenge page')
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=result))
    last = send.call_args_list[-1][0][2]
    assert 'Run failed' in last and 'bot-challenge' in last
    assert 'All caught up' not in last


def test_run_all_caught_up_only_when_nothing_new(ctx):
    config, send = ctx
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=_run_result()))
    assert 'All caught up' in send.call_args_list[-1][0][2]


def test_run_silent_after_successful_delivery(ctx):
    """Delivered listings speak for themselves — only 'Running scrape...' is sent."""
    config, send = ctx
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=_run_result(2, 0)))
    assert send.call_count == 1


def test_scrape_and_notify_counts_failed_deliveries(main_mod, monkeypatch):
    """A listing every channel fails on is counted as failed and left unseen."""
    listings = [{'url': 'https://funda.nl/a', 'title': 'A'}, {'url': 'https://funda.nl/b', 'title': 'B'}]
    seen = []
    monkeypatch.setattr(main_mod, 'get_new_listings', lambda filters: listings)
    monkeypatch.setattr(main_mod, 'matches_filters', lambda listing, filters: True)
    monkeypatch.setattr(main_mod, 'mark_seen', seen.append)

    notifier = MagicMock()
    notifier.notify.side_effect = lambda listing: listing['title'] == 'A'
    config = {'filters': {'areas': ['utrecht/oudwijk']}}

    assert main_mod.scrape_and_notify(config, [notifier]) == (1, 1, None)
    assert seen == ['https://funda.nl/a']


# ---------------------------------------------------------------------------
# Failed scrapes and the consecutive-failure alert
# ---------------------------------------------------------------------------

_CONFIG = {'filters': {'areas': ['utrecht/oudwijk']}}


def _failing(main_mod, monkeypatch):
    from funda_bot.scraper import ScrapeError

    def boom(filters):
        raise ScrapeError('Funda returned a bot-challenge page')
    monkeypatch.setattr(main_mod, 'get_new_listings', boom)


def test_scrape_failure_is_reported_not_raised(main_mod, monkeypatch):
    _failing(main_mod, monkeypatch)
    result = main_mod.scrape_and_notify(_CONFIG, [])
    assert result == (0, 0, 'Funda returned a bot-challenge page')


def test_unexpected_error_is_a_failure_and_keeps_delivered_count(main_mod, monkeypatch):
    """A crash mid-delivery still reports what was delivered, plus the error."""
    listings = [{'url': 'https://funda.nl/a', 'title': 'A'}, {'url': 'https://funda.nl/b', 'title': 'B'}]
    monkeypatch.setattr(main_mod, 'get_new_listings', lambda filters: listings)
    monkeypatch.setattr(main_mod, 'matches_filters', lambda listing, filters: True)
    monkeypatch.setattr(main_mod, 'mark_seen', lambda url: None)
    notifier = MagicMock()
    notifier.notify.side_effect = [True, RuntimeError('boom')]

    result = main_mod.scrape_and_notify(_CONFIG, [notifier])
    assert result.delivered == 1 and result.error == 'RuntimeError: boom'


def test_alert_once_after_two_failures_then_recovery(main_mod, monkeypatch):
    alert = MagicMock()
    _failing(main_mod, monkeypatch)
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    assert alert.call_count == 0                       # one failure: a blip, retried quietly
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    assert alert.call_count == 1                       # two in a row: alert
    assert 'failed 2 runs in a row' in alert.call_args[0][0]
    assert 'bot-challenge' in alert.call_args[0][0]
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    assert alert.call_count == 1                       # still failing: no repeat

    monkeypatch.setattr(main_mod, 'get_new_listings', lambda filters: [])
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    assert alert.call_count == 2
    assert 'recovered after 3 failed runs' in alert.call_args[0][0]
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    assert alert.call_count == 2                       # healthy: silent


def test_single_failure_then_success_sends_nothing(main_mod, monkeypatch):
    alert = MagicMock()
    _failing(main_mod, monkeypatch)
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    monkeypatch.setattr(main_mod, 'get_new_listings', lambda filters: [])
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    assert alert.call_count == 0
    assert main_mod._failed_runs == 0


def test_no_areas_skip_does_not_touch_the_counter(main_mod, monkeypatch):
    """A skipped run is neither a failure nor a recovery."""
    alert = MagicMock()
    _failing(main_mod, monkeypatch)
    main_mod.scrape_and_notify(_CONFIG, [], alert)
    main_mod.scrape_and_notify({'filters': {'areas': []}}, [], alert)
    assert main_mod._failed_runs == 1 and alert.call_count == 0


def test_alert_without_telegram_is_only_logged(main_mod, monkeypatch):
    """With no alert callable the run still completes (the message goes to the log)."""
    _failing(main_mod, monkeypatch)
    main_mod.scrape_and_notify(_CONFIG, [])
    assert main_mod.scrape_and_notify(_CONFIG, []).error is not None


# ---------------------------------------------------------------------------
# _send — replies and alerts (C2)
# ---------------------------------------------------------------------------

def _telegram_reply(status, body):
    import requests
    r = requests.models.Response()
    r.status_code = status
    r.reason = 'Unauthorized' if status == 401 else 'OK'
    r._content = body.encode()
    r.url = 'https://api.telegram.org/bot123456:SECRETtoken/sendMessage'
    return r


def test_send_logs_a_rejected_message(monkeypatch, caplog):
    """Telegram's error reply must leave an ERROR line with its reason, token redacted."""
    from funda_bot import commands
    body = '{"ok":false,"error_code":401,"description":"Unauthorized"}'
    monkeypatch.setattr(commands.requests, 'post', lambda *a, **k: _telegram_reply(401, body))
    with caplog.at_level('ERROR', logger='funda_bot.commands'):
        commands._send('123456:SECRETtoken', '1', 'hello')
    message = caplog.records[-1].getMessage()
    assert message.startswith('Failed to send Telegram message: 401')
    assert '"description":"Unauthorized"' in message
    assert 'SECRETtoken' not in message


def test_send_success_logs_nothing(monkeypatch, caplog):
    from funda_bot import commands
    monkeypatch.setattr(commands.requests, 'post', lambda *a, **k: _telegram_reply(200, '{"ok":true}'))
    with caplog.at_level('DEBUG', logger='funda_bot.commands'):
        commands._send('123456:SECRETtoken', '1', 'hello')
    assert caplog.records == []


# ---------------------------------------------------------------------------
# _save_config — atomic write (C3)
# ---------------------------------------------------------------------------

_OLD_CONFIG = 'filters:\n  areas:\n  - utrecht/oudwijk\n'


def test_save_config_crash_leaves_the_old_file(tmp_path, monkeypatch):
    """A failure mid-write (e.g. disk full) must not leave config.yaml empty."""
    from funda_bot import commands
    path = tmp_path / 'config.yaml'
    path.write_text(_OLD_CONFIG)
    monkeypatch.setattr(commands, '_CONFIG_PATH', path)

    def crash(*args, **kwargs):
        raise OSError('No space left on device')
    monkeypatch.setattr(commands.yaml, 'dump', crash)
    with pytest.raises(OSError):
        commands._save_config({'filters': {'areas': ['utrecht/wittevrouwen']}})
    assert path.read_text() == _OLD_CONFIG


def test_save_config_replaces_the_file_and_leaves_no_temp(tmp_path, monkeypatch):
    import yaml
    from funda_bot import commands
    path = tmp_path / 'config.yaml'
    path.write_text(_OLD_CONFIG)
    monkeypatch.setattr(commands, '_CONFIG_PATH', path)
    commands._save_config({'filters': {'areas': ['utrecht/wittevrouwen']}})
    assert yaml.safe_load(path.read_text()) == {'filters': {'areas': ['utrecht/wittevrouwen']}}
    assert [p.name for p in tmp_path.iterdir()] == ['config.yaml']


# ---------------------------------------------------------------------------
# M3 — Thread safety
# ---------------------------------------------------------------------------

def test_config_lock_is_threading_lock():
    # threading.Lock is a factory function before Python 3.13 (production runs
    # 3.12), so isinstance() against it raises; compare with a real lock's type.
    assert isinstance(_CONFIG_LOCK, type(threading.Lock()))


def test_lock_released_after_mutation(ctx):
    config, _ = ctx
    with patch('funda_bot.commands._save_config'):
        handle_command('/setrooms 3', config, 'tok', '123', MagicMock())
    acquired = _CONFIG_LOCK.acquire(blocking=False)
    assert acquired, "lock still held after command — deadlock risk"
    _CONFIG_LOCK.release()


def test_scrape_snapshot_is_independent(main_mod, monkeypatch):
    """scrape_and_notify must deepcopy filters so mid-scrape mutations don't corrupt it."""
    captured = {}

    def fake_get_new_listings(filters):
        captured['filters'] = filters
        return []

    # Patch where main looks it up; patching funda_bot.scraper only worked when
    # main happened to be first imported after the patch (else: a live Funda hit).
    monkeypatch.setattr(main_mod, 'get_new_listings', fake_get_new_listings)

    config = {
        'filters': {'areas': ['utrecht/oudwijk'], 'price_min': 400000, 'price_max': 800000,
                    'min_bedrooms': 2, 'energy_labels': [], 'keywords': [], 'publication_days': 3},
    }
    main_mod.scrape_and_notify(config, [])

    # mutate original after the snapshot was taken — captured copy must be unaffected
    config['filters']['price_min'] = 999999
    assert captured['filters']['price_min'] == 400000


# ---------------------------------------------------------------------------
# Polling loop — log levels (L5)
# ---------------------------------------------------------------------------

class _StopPolling(BaseException):
    """Raised from the patched time.sleep to break out of the infinite loop."""


def _poll(monkeypatch, *polls):
    """Run poll_commands over canned getUpdates results until an error-path sleep.

    Each item is a list of updates (a successful poll) or an exception to raise.
    The last item must be an exception; its sleep(5) ends the loop. Returns the
    handle_command mock. No real Telegram call is made.
    """
    from funda_bot import commands

    def response(updates):
        r = MagicMock()
        r.json.return_value = {'ok': True, 'result': updates}   # Telegram always sends ok
        return r

    calls = iter([response([])] + [p if isinstance(p, BaseException) else response(p) for p in polls])

    def fake_get(*args, **kwargs):
        item = next(calls)
        if isinstance(item, BaseException):
            raise item
        return item

    def stop(seconds):
        raise _StopPolling

    handled = MagicMock()
    monkeypatch.setattr(commands.requests, 'get', fake_get)
    monkeypatch.setattr(commands.time, 'sleep', stop)
    monkeypatch.setattr(commands, 'handle_command', handled)
    with pytest.raises(_StopPolling):
        commands.poll_commands('123:abc', '1', {'filters': {}}, MagicMock())
    return handled


def _poll_once(monkeypatch, error):
    _poll(monkeypatch, error)


def _update(update_id, text, date=None):
    msg = {'chat': {'id': 1}, 'text': text}
    if date is not None:
        msg['date'] = date
    return {'update_id': update_id, 'message': msg}


def test_polling_logs_how_late_a_command_arrived(monkeypatch, caplog):
    import re
    import time as _time
    import requests
    sent = int(_time.time()) - 60
    with caplog.at_level('INFO', logger='funda_bot.commands'):
        handled = _poll(monkeypatch, [_update(1, '/setdate 10', sent)], requests.ReadTimeout('t'))
    handled.assert_called_once()
    line = next(r.getMessage() for r in caplog.records if 'received' in r.getMessage())
    m = re.fullmatch(r'Command /setdate received (\d+)s after sending', line)
    assert m and 59 <= int(m.group(1)) <= 62    # command name only, not its arguments


def test_polling_without_a_date_says_so(monkeypatch, caplog):
    import requests
    with caplog.at_level('INFO', logger='funda_bot.commands'):
        _poll(monkeypatch, [_update(1, '/filters')], requests.ReadTimeout('t'))
    assert 'Command /filters received an unknown time after sending' in caplog.text


@pytest.mark.parametrize('error', [
    __import__('requests').ReadTimeout('Read timed out. (read timeout=35)'),
    __import__('requests').ConnectionError('Connection reset by peer'),
])
def test_polling_network_blip_is_a_warning(monkeypatch, caplog, error):
    with caplog.at_level('WARNING', logger='funda_bot.commands'):
        _poll_once(monkeypatch, error)
    record = caplog.records[-1]
    assert record.levelname == 'WARNING'
    assert 'Polling error (network, retrying)' in record.getMessage()


def test_polling_telegram_error_reply_is_logged_and_paused(monkeypatch, caplog):
    """An error reply (e.g. a revoked token) must not read as an empty inbox (C1)."""
    from funda_bot import commands
    reply = MagicMock()
    reply.json.return_value = {'ok': False, 'error_code': 401, 'description': 'Unauthorized'}
    monkeypatch.setattr(commands.requests, 'get', lambda *args, **kwargs: reply)
    paused = []

    def stop(seconds):
        paused.append(seconds)
        raise _StopPolling
    monkeypatch.setattr(commands.time, 'sleep', stop)
    with caplog.at_level('ERROR', logger='funda_bot.commands'), pytest.raises(_StopPolling):
        commands.poll_commands('123:abc', '1', {'filters': {}}, MagicMock())
    assert caplog.records[-1].getMessage() == 'Polling error: Telegram replied 401: Unauthorized'
    assert paused == [30]


def test_polling_other_error_stays_an_error(monkeypatch, caplog):
    """A bug (e.g. in a command handler) must still log at ERROR."""
    with caplog.at_level('WARNING', logger='funda_bot.commands'):
        _poll_once(monkeypatch, ValueError('handler bug'))
    record = caplog.records[-1]
    assert record.levelname == 'ERROR'
    assert record.getMessage() == 'Polling error: handler bug'


# ---------------------------------------------------------------------------
# C7 — access check, redaction in the polling loop
# ---------------------------------------------------------------------------

def test_polling_ignores_a_foreign_chat(monkeypatch, caplog):
    """The chat-id check is the bot's only access control: other chats are ignored."""
    import requests
    foreign = {'update_id': 1, 'message': {'chat': {'id': 2}, 'text': '/setdate 10', 'date': 0}}
    with caplog.at_level('INFO', logger='funda_bot.commands'):
        handled = _poll(monkeypatch, [foreign, _update(2, '/filters')], requests.ReadTimeout('t'))
    assert [c.args[0] for c in handled.call_args_list] == ['/filters']
    assert '/setdate' not in caplog.text


@pytest.mark.parametrize('error, level', [
    (__import__('requests').ConnectionError(
        "HTTPSConnectionPool(host='api.telegram.org', port=443): Max retries exceeded "
        "with url: /bot123:abc/getUpdates?offset=0&timeout=30"), 'WARNING'),
    (ValueError('unexpected reply from https://api.telegram.org/bot123:abc/getUpdates'), 'ERROR'),
])
def test_polling_errors_redact_the_token(monkeypatch, caplog, error, level):
    """requests puts the URL, token included, in its exception text."""
    with caplog.at_level('WARNING', logger='funda_bot.commands'):
        _poll_once(monkeypatch, error)
    record = caplog.records[-1]
    assert record.levelname == level
    assert 'bot<redacted>/getUpdates' in record.getMessage()
    assert '123:abc' not in caplog.text


# ---------------------------------------------------------------------------
# C7 — the six list commands, /help, unknown commands
# ---------------------------------------------------------------------------

_LIST_COMMANDS = [
    # add, remove, filter key, argument as typed, as stored
    ('/addarea', '/removearea', 'areas', 'utrecht/oudwijk', 'utrecht/oudwijk'),
    ('/addkeyword', '/removekeyword', 'keywords', 'Tuin', 'tuin'),
    ('/addamenity', '/removeamenity', 'amenities', 'Bathtub', 'bathtub'),
]


@pytest.mark.parametrize('add, remove, key, typed, stored', _LIST_COMMANDS)
def test_list_command_round_trip(add, remove, key, typed, stored):
    config = _make_config()
    send = MagicMock()
    with patch('funda_bot.commands._send', send), patch('funda_bot.commands._save_config') as save:
        handle_command(f'{add} {typed}', config, 'tok', '123', MagicMock())
        assert config['filters'][key] == [stored]
        handle_command(f'{add} {typed}', config, 'tok', '123', MagicMock())
        assert config['filters'][key] == [stored]
        assert send.call_args[0][2] == f'Already in list: {stored}'
        handle_command(f'{remove} {typed}', config, 'tok', '123', MagicMock())
        assert config['filters'][key] == []
        handle_command(f'{remove} {typed}', config, 'tok', '123', MagicMock())
        assert send.call_args[0][2] == f'Not in list: {stored}'
    assert save.call_count == 2    # only the real add and remove write config.yaml


@pytest.mark.parametrize('add, remove, key, typed, stored', _LIST_COMMANDS)
def test_list_command_when_the_key_is_missing(add, remove, key, typed, stored):
    """A config.yaml without the key (e.g. hand-edited) neither crashes nor loses the add."""
    config = _make_config()
    del config['filters'][key]
    with patch('funda_bot.commands._send') as send, patch('funda_bot.commands._save_config'):
        handle_command(f'{remove} {typed}', config, 'tok', '123', MagicMock())
        assert send.call_args[0][2] == f'Not in list: {stored}'
        handle_command(f'{add} {typed}', config, 'tok', '123', MagicMock())
    assert config['filters'][key] == [stored]


@pytest.mark.parametrize('cmd', [c for row in _LIST_COMMANDS for c in row[:2]])
def test_list_command_without_argument_sends_usage(ctx, cmd):
    config, send = ctx
    before = {k: list(v) for k, v in config['filters'].items() if isinstance(v, list)}
    with patch('funda_bot.commands._save_config') as save:
        handle_command(cmd, config, 'tok', '123', MagicMock())
    assert send.call_args[0][2].startswith(f'Usage: {cmd} ')
    save.assert_not_called()
    assert {k: v for k, v in config['filters'].items() if k in before} == before


def test_help_sends_the_command_list(ctx):
    from funda_bot.commands import HELP_TEXT
    config, send = ctx
    handle_command('/Help', config, 'tok', '123', MagicMock())   # commands are case-insensitive
    assert send.call_args[0][2] == HELP_TEXT


def test_unknown_command_points_to_help(ctx):
    config, send = ctx
    handle_command('/frobnicate now', config, 'tok', '123', MagicMock())
    assert send.call_args[0][2] == 'Unknown command. Send /help for the full list.'


# ---------------------------------------------------------------------------
# C7 — config.yaml bootstrap (main.load_config)
# ---------------------------------------------------------------------------

def test_load_config_bootstraps_from_the_template(main_mod, monkeypatch, tmp_path):
    example = tmp_path / 'config.example.yaml'
    example.write_text(_OLD_CONFIG)
    monkeypatch.setattr(main_mod, '_CONFIG_PATH', tmp_path / 'config.yaml')
    monkeypatch.setattr(main_mod, '_CONFIG_EXAMPLE_PATH', example)

    assert main_mod.load_config() == {'filters': {'areas': ['utrecht/oudwijk']}}
    assert (tmp_path / 'config.yaml').read_text() == _OLD_CONFIG


def test_load_config_keeps_an_existing_config(main_mod, monkeypatch, tmp_path):
    (tmp_path / 'config.yaml').write_text('filters:\n  areas: []\n')
    (tmp_path / 'config.example.yaml').write_text(_OLD_CONFIG)
    monkeypatch.setattr(main_mod, '_CONFIG_PATH', tmp_path / 'config.yaml')
    monkeypatch.setattr(main_mod, '_CONFIG_EXAMPLE_PATH', tmp_path / 'config.example.yaml')
    assert main_mod.load_config() == {'filters': {'areas': []}}


def test_load_config_without_template_fails_clearly(main_mod, monkeypatch, tmp_path):
    monkeypatch.setattr(main_mod, '_CONFIG_PATH', tmp_path / 'config.yaml')
    monkeypatch.setattr(main_mod, '_CONFIG_EXAMPLE_PATH', tmp_path / 'config.example.yaml')
    with pytest.raises(FileNotFoundError, match='config.example.yaml is missing'):
        main_mod.load_config()
    assert list(tmp_path.iterdir()) == []


def test_load_and_save_use_the_same_config_file(main_mod):
    """Filters set via Telegram must survive a restart: the file main loads is the
    file commands saves, next to the template (review C8)."""
    from funda_bot import commands
    assert main_mod._CONFIG_PATH == commands._CONFIG_PATH
    assert main_mod._CONFIG_PATH.parent == main_mod._CONFIG_EXAMPLE_PATH.parent


def test_real_template_loads_and_has_every_section(main_mod):
    """config.example.yaml is what a fresh install runs on: it must parse and be complete."""
    import yaml
    config = yaml.safe_load(main_mod._CONFIG_EXAMPLE_PATH.read_text())
    assert {'notifications', 'filters', 'schedule'} <= set(config)
    assert config['schedule']['hours']
