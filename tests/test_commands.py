"""Unit tests for handle_command — input validation (M1)."""

from unittest.mock import MagicMock, patch

import pytest

from funda_bot.commands import handle_command


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
