"""Unit tests for handle_command — input validation (M1) and thread safety (M3)."""

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

def test_run_reports_failed_deliveries(ctx):
    """A listing that failed to send must not be reported as 'All caught up'."""
    config, send = ctx
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=(0, 1)))
    last = send.call_args_list[-1][0][2]
    assert 'could not be sent' in last and 'All caught up' not in last


def test_run_all_caught_up_only_when_nothing_new(ctx):
    config, send = ctx
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=(0, 0)))
    assert 'All caught up' in send.call_args_list[-1][0][2]


def test_run_silent_after_successful_delivery(ctx):
    """Delivered listings speak for themselves — only 'Running scrape...' is sent."""
    config, send = ctx
    handle_command('/run', config, 'tok', '123', MagicMock(return_value=(2, 0)))
    assert send.call_count == 1


def test_scrape_and_notify_counts_failed_deliveries(monkeypatch):
    """A listing every channel fails on is counted as failed and left unseen."""
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
    import main as main_mod

    listings = [{'url': 'https://funda.nl/a', 'title': 'A'}, {'url': 'https://funda.nl/b', 'title': 'B'}]
    seen = []
    monkeypatch.setattr(main_mod, 'get_new_listings', lambda filters: listings)
    monkeypatch.setattr(main_mod, 'matches_filters', lambda listing, filters: True)
    monkeypatch.setattr(main_mod, 'mark_seen', seen.append)

    notifier = MagicMock()
    notifier.notify.side_effect = lambda listing: listing['title'] == 'A'
    config = {'filters': {'areas': ['utrecht/oudwijk']}}

    assert main_mod.scrape_and_notify(config, [notifier]) == (1, 1)
    assert seen == ['https://funda.nl/a']


# ---------------------------------------------------------------------------
# M3 — Thread safety
# ---------------------------------------------------------------------------

def test_config_lock_is_threading_lock():
    assert isinstance(_CONFIG_LOCK, threading.Lock)


def test_lock_released_after_mutation(ctx):
    config, _ = ctx
    with patch('funda_bot.commands._save_config'):
        handle_command('/setrooms 3', config, 'tok', '123', MagicMock())
    acquired = _CONFIG_LOCK.acquire(blocking=False)
    assert acquired, "lock still held after command — deadlock risk"
    _CONFIG_LOCK.release()


def test_scrape_snapshot_is_independent(monkeypatch):
    """scrape_and_notify must deepcopy filters so mid-scrape mutations don't corrupt it."""
    import copy
    import sys
    sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))

    import main as main_mod

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
