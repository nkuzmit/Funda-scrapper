"""Telegram command handler and polling loop.

Runs on the main thread (blocking). The BackgroundScheduler handles
timed scrapes concurrently in a background thread.

Commands
--------
/help               — list all commands
/filters            — show current active filters
/run                — trigger an immediate scrape
/setprice MIN MAX   — set price range (use "null" for no bound)
/setrooms N         — set minimum bedrooms
/setlabel A B ...   — set energy labels
/setdate N          — set publication_days
/addarea SLUG       — add a funda area slug (e.g. utrecht/oudwijk)
/removearea SLUG    — remove a funda area slug
"""

import logging
import time
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config.yaml'

_LABEL_ORDER = ['A+++++', 'A++++', 'A+++', 'A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']


HELP_TEXT = (
    "Funda Bot — available commands:\n\n"
    "/filters — show current filters\n"
    "/run — trigger immediate scrape\n"
    "/setprice 500000 900000 — set price range (null = no bound)\n"
    "/setrooms 2 — set minimum bedrooms\n"
    "/setlabel A B C — set energy labels\n"
    "/setdate 3 — set publication days (max 10)\n"
    "/addarea utrecht/oudwijk — add an area slug\n"
    "/removearea utrecht/oudwijk — remove an area slug\n"
    "/help — show this message"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send(bot_token: str, chat_id: str, text: str):
    """Send a plain-text message to the configured chat."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={'chat_id': chat_id, 'text': text},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")


def _save_config(config: dict):
    """Write the in-memory config back to config.yaml."""
    with open(_CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _fmt_filters(filters: dict) -> str:
    """Format filters dict as a readable string."""
    areas = filters.get('areas') or []
    area_lines = '\n'.join(f'  • {a}' for a in areas) if areas else '  (none)'

    price_min = filters.get('price_min')
    price_max = filters.get('price_max')
    price_str = f"€{price_min:,}".replace(',', '.') if price_min else 'no min'
    price_str += ' — '
    price_str += f"€{price_max:,}".replace(',', '.') if price_max else 'no max'

    labels = sorted(
        filters.get('energy_labels') or [],
        key=lambda l: _LABEL_ORDER.index(l) if l in _LABEL_ORDER else 99,
    )
    labels_str = ' '.join(labels) if labels else '(none)'

    return (
        f"📍 Areas ({len(areas)}):\n{area_lines}\n\n"
        f"💰 Price: {price_str}\n"
        f"🛏️  Min bedrooms: {filters.get('min_bedrooms') or 'any'}\n"
        f"⚡ Energy labels: {labels_str}\n"
        f"📅 Publication: last {filters.get('publication_days')} days\n"
        f"🔍 Keywords: {', '.join(filters.get('keywords') or []) or '(none)'}"
    )


# ---------------------------------------------------------------------------
# Command dispatcher
# ---------------------------------------------------------------------------

def handle_command(text: str, config: dict, bot_token: str, chat_id: str, scrape_fn):
    """Parse and execute a single command string."""
    parts = text.strip().split()
    cmd = parts[0].lower()
    args = parts[1:]
    filters = config['filters']

    if cmd == '/help':
        _send(bot_token, chat_id, HELP_TEXT)

    elif cmd == '/filters':
        _send(bot_token, chat_id, _fmt_filters(filters))

    elif cmd == '/run':
        _send(bot_token, chat_id, "Running scrape...")
        delivered = scrape_fn()
        if delivered == 0:
            _send(bot_token, chat_id, "All caught up — no new listings found.")

    elif cmd == '/setprice':
        if len(args) < 2:
            _send(bot_token, chat_id, "Usage: /setprice 500000 900000  (use null for no bound)")
            return
        filters['price_min'] = None if args[0] == 'null' else int(args[0])
        filters['price_max'] = None if args[1] == 'null' else int(args[1])
        _save_config(config)
        _send(bot_token, chat_id, f"Price set: {args[0]} — {args[1]}")

    elif cmd == '/setrooms':
        if not args:
            _send(bot_token, chat_id, "Usage: /setrooms 2")
            return
        filters['min_bedrooms'] = int(args[0])
        _save_config(config)
        _send(bot_token, chat_id, f"Min bedrooms set: {args[0]}")

    elif cmd == '/setlabel':
        if not args:
            _send(bot_token, chat_id, "Usage: /setlabel A B C")
            return
        filters['energy_labels'] = args
        _save_config(config)
        _send(bot_token, chat_id, f"Energy labels set: {' '.join(args)}")

    elif cmd == '/setdate':
        if not args:
            _send(bot_token, chat_id, "Usage: /setdate 3")
            return
        days = int(args[0])
        filters['publication_days'] = days
        _save_config(config)
        _send(bot_token, chat_id, f"Publication days set: {days}")

    elif cmd == '/addarea':
        if not args:
            _send(bot_token, chat_id, "Usage: /addarea utrecht/oudwijk")
            return
        slug = args[0]
        areas = filters.setdefault('areas', [])
        if slug in areas:
            _send(bot_token, chat_id, f"Already in list: {slug}")
        else:
            areas.append(slug)
            _save_config(config)
            _send(bot_token, chat_id, f"Area added: {slug}")

    elif cmd == '/removearea':
        if not args:
            _send(bot_token, chat_id, "Usage: /removearea utrecht/oudwijk")
            return
        slug = args[0]
        areas = filters.get('areas') or []
        if slug not in areas:
            _send(bot_token, chat_id, f"Not in list: {slug}")
        else:
            areas.remove(slug)
            _save_config(config)
            _send(bot_token, chat_id, f"Area removed: {slug}")

    else:
        _send(bot_token, chat_id, f"Unknown command. Send /help for the full list.")


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def poll_commands(bot_token: str, chat_id: str, config: dict, scrape_fn):
    """Block the main thread, polling Telegram for incoming commands.

    Dispatches any command from the authorised chat_id to handle_command().
    Ignores all other senders. Retries automatically on network errors.
    """
    offset = 0
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    logger.info("Telegram command polling started")

    while True:
        try:
            r = requests.get(url, params={'offset': offset, 'timeout': 30}, timeout=35)
            for update in r.json().get('result', []):
                offset = update['update_id'] + 1
                msg = update.get('message', {})
                if str(msg.get('chat', {}).get('id')) != str(chat_id):
                    continue
                text = msg.get('text', '')
                if text.startswith('/'):
                    handle_command(text, config, bot_token, chat_id, scrape_fn)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
