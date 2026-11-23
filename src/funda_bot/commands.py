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
/addkeyword WORD    — add a keyword filter
/removekeyword WORD — remove a keyword filter
"""

import logging
import re
import threading
import time
from pathlib import Path

import requests
import yaml

logger = logging.getLogger(__name__)

# Telegram bot tokens appear in api.telegram.org URLs, which surface inside
# requests' exception messages. Scrub them before anything reaches the logs.
_TOKEN_RE = re.compile(r'bot\d+:[A-Za-z0-9_-]+')


def _redact(text) -> str:
    """Remove Telegram bot tokens from a string before logging."""
    return _TOKEN_RE.sub('bot<redacted>', str(text))


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / 'config.yaml'
_CONFIG_LOCK = threading.Lock()

# Pause after Telegram answers getUpdates with an error (ok: false). A revoked
# token (401) or a second poller (409) repeats until someone acts; 30 s keeps
# that to ~120 log lines an hour.
_TELEGRAM_ERROR_PAUSE = 30

_LABEL_ORDER = ['A+++++', 'A++++', 'A+++', 'A++', 'A+', 'A', 'B', 'C', 'D', 'E', 'F', 'G']


HELP_TEXT = (
    "Funda Bot — available commands:\n\n"
    "/filters — show current filters\n"
    "/run — trigger immediate scrape\n"
    "/setprice 500000 900000 — set price range (null = no bound)\n"
    "/setrooms 2 — set minimum bedrooms\n"
    "/setfloor 90 130 — set floor area range in m² (null = no bound)\n"
    "/setlabel A B C — set energy labels\n"
    "/setdate 3 — set publication days (max 10)\n"
    "/addarea utrecht/oudwijk — add an area slug\n"
    "/removearea utrecht/oudwijk — remove an area slug\n"
    "/addkeyword tuin — add a keyword filter\n"
    "/removekeyword tuin — remove a keyword filter\n"
    "/addamenity bathtub — add an amenity filter\n"
    "/removeamenity bathtub — remove an amenity filter\n"
    "/help — show this message"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send(bot_token: str, chat_id: str, text: str):
    """Send a plain-text message to the configured chat. Failures are logged.

    Telegram rejects a message with a 4xx/5xx and explains why only in the
    body; requests doesn't raise on those by itself, so check explicitly
    (review C2: a rejected reply or alert used to leave no trace).
    """
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={'chat_id': chat_id, 'text': text},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        body = getattr(getattr(e, 'response', None), 'text', '') or ''
        detail = f"{e} | response: {body[:300]}" if body else str(e)
        logger.error(f"Failed to send Telegram message: {_redact(detail)}")


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

    floor_min = filters.get('floor_area_min')
    floor_max = filters.get('floor_area_max')
    floor_str = f"{floor_min or 'any'} — {floor_max or 'any'} m²"

    amenities_str = ', '.join(filters.get('amenities') or []) or '(none)'

    return (
        f"📍 Areas ({len(areas)}):\n{area_lines}\n\n"
        f"💰 Price: {price_str}\n"
        f"🛏️  Min bedrooms: {filters.get('min_bedrooms') or 'any'}\n"
        f"📐 Floor area: {floor_str}\n"
        f"⚡ Energy labels: {labels_str}\n"
        f"📅 Publication: last {filters.get('publication_days')} days\n"
        f"🔍 Keywords: {', '.join(filters.get('keywords') or []) or '(none)'}\n"
        f"🛁 Amenities: {amenities_str}"
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
        result = scrape_fn()  # main.RunResult(delivered, failed, error)
        # Never report a failed scrape or delivery as "nothing new" (2026-11-20).
        if result.error:
            _send(
                bot_token, chat_id,
                f"⚠️ Run failed: {result.error}\n\nSee main.log — will retry next run.",
            )
        elif result.failed:
            _send(
                bot_token, chat_id,
                f"⚠️ {result.failed} new listing(s) could not be sent "
                f"({result.delivered} delivered). See main.log — will retry next run.",
            )
        elif result.delivered == 0:
            _send(bot_token, chat_id, "All caught up — no new listings found.")

    elif cmd == '/setprice':
        if len(args) < 2:
            _send(bot_token, chat_id, "Usage: /setprice 500000 900000  (use null for no bound)")
            return
        try:
            price_min = None if args[0] == 'null' else int(args[0])
            price_max = None if args[1] == 'null' else int(args[1])
        except ValueError:
            _send(bot_token, chat_id, "Usage: /setprice 500000 900000  (use null for no bound)")
            return
        with _CONFIG_LOCK:
            filters['price_min'] = price_min
            filters['price_max'] = price_max
            _save_config(config)
        _send(bot_token, chat_id, f"Price set: {args[0]} — {args[1]}")

    elif cmd == '/setrooms':
        if not args:
            _send(bot_token, chat_id, "Usage: /setrooms 2")
            return
        try:
            rooms = int(args[0])
        except ValueError:
            _send(bot_token, chat_id, "Usage: /setrooms 2")
            return
        with _CONFIG_LOCK:
            filters['min_bedrooms'] = rooms
            _save_config(config)
        _send(bot_token, chat_id, f"Min bedrooms set: {args[0]}")

    elif cmd == '/setlabel':
        if not args:
            _send(bot_token, chat_id, "Usage: /setlabel A B C")
            return
        with _CONFIG_LOCK:
            filters['energy_labels'] = [a.upper() for a in args]
            _save_config(config)
        _send(bot_token, chat_id, f"Energy labels set: {' '.join(args)}")

    elif cmd == '/setdate':
        if not args:
            _send(bot_token, chat_id, "Usage: /setdate 3")
            return
        try:
            days = int(args[0])
        except ValueError:
            _send(bot_token, chat_id, "Usage: /setdate 3")
            return
        with _CONFIG_LOCK:
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
            with _CONFIG_LOCK:
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
            with _CONFIG_LOCK:
                areas.remove(slug)
                _save_config(config)
            _send(bot_token, chat_id, f"Area removed: {slug}")

    elif cmd == '/setfloor':
        if len(args) < 2:
            _send(bot_token, chat_id, "Usage: /setfloor 90 130  (use null for no bound)")
            return
        try:
            floor_min = None if args[0] == 'null' else int(args[0])
            floor_max = None if args[1] == 'null' else int(args[1])
        except ValueError:
            _send(bot_token, chat_id, "Usage: /setfloor 90 130  (use null for no bound)")
            return
        with _CONFIG_LOCK:
            filters['floor_area_min'] = floor_min
            filters['floor_area_max'] = floor_max
            _save_config(config)
        _send(bot_token, chat_id, f"Floor area set: {args[0]} — {args[1]} m²")

    elif cmd == '/addkeyword':
        if not args:
            _send(bot_token, chat_id, "Usage: /addkeyword tuin")
            return
        word = args[0].lower()
        keywords = filters.setdefault('keywords', [])
        if word in keywords:
            _send(bot_token, chat_id, f"Already in list: {word}")
        else:
            with _CONFIG_LOCK:
                keywords.append(word)
                _save_config(config)
            _send(bot_token, chat_id, f"Keyword added: {word}")

    elif cmd == '/removekeyword':
        if not args:
            _send(bot_token, chat_id, "Usage: /removekeyword tuin")
            return
        word = args[0].lower()
        keywords = filters.get('keywords') or []
        if word not in keywords:
            _send(bot_token, chat_id, f"Not in list: {word}")
        else:
            with _CONFIG_LOCK:
                keywords.remove(word)
                _save_config(config)
            _send(bot_token, chat_id, f"Keyword removed: {word}")

    elif cmd == '/addamenity':
        if not args:
            _send(bot_token, chat_id, "Usage: /addamenity bathtub")
            return
        word = args[0].lower()
        amenities = filters.setdefault('amenities', [])
        if word in amenities:
            _send(bot_token, chat_id, f"Already in list: {word}")
        else:
            with _CONFIG_LOCK:
                amenities.append(word)
                _save_config(config)
            _send(bot_token, chat_id, f"Amenity added: {word}")

    elif cmd == '/removeamenity':
        if not args:
            _send(bot_token, chat_id, "Usage: /removeamenity bathtub")
            return
        word = args[0].lower()
        amenities = filters.get('amenities') or []
        if word not in amenities:
            _send(bot_token, chat_id, f"Not in list: {word}")
        else:
            with _CONFIG_LOCK:
                amenities.remove(word)
                _save_config(config)
            _send(bot_token, chat_id, f"Amenity removed: {word}")

    else:
        _send(bot_token, chat_id, "Unknown command. Send /help for the full list.")


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def poll_commands(bot_token: str, chat_id: str, config: dict, scrape_fn):
    """Block the main thread, polling Telegram for incoming commands.

    Dispatches any command from the authorised chat_id to handle_command().
    Ignores all other senders. Retries automatically on network errors and on
    error replies from Telegram, logging each one.
    """
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    logger.info("Telegram command polling started")

    # Drain any pending updates accumulated while the bot was offline
    # so old commands (including /stop or /restart) are not replayed on startup
    try:
        r = requests.get(url, params={'timeout': 0}, timeout=5)
        updates = r.json().get('result', [])
        offset = updates[-1]['update_id'] + 1 if updates else 0
    except Exception:
        offset = 0

    while True:
        try:
            r = requests.get(url, params={'offset': offset, 'timeout': 30}, timeout=35)
            data = r.json()
            if not data.get('ok'):
                # An error reply must not read as an empty inbox: without this
                # the loop re-polled instantly and silently (review C1).
                logger.error(
                    f"Polling error: Telegram replied {data.get('error_code')}: "
                    f"{data.get('description')}"
                )
                time.sleep(_TELEGRAM_ERROR_PAUSE)
                continue
            for update in data.get('result', []):
                offset = update['update_id'] + 1
                msg = update.get('message', {})
                if str(msg.get('chat', {}).get('id')) != str(chat_id):
                    continue
                text = msg.get('text', '')
                if text.startswith('/'):
                    # How long the command took to reach us: measures the
                    # "slow replies" open issue (Telegram shows only minutes).
                    sent = msg.get('date')  # Unix seconds, set by Telegram
                    lag = f"{time.time() - sent:.0f}s" if isinstance(sent, int) else "an unknown time"
                    logger.info(f"Command {text.split()[0]} received {lag} after sending")
                    handle_command(text, config, bot_token, chat_id, scrape_fn)
        except (requests.Timeout, requests.ConnectionError) as e:
            # Network blips on the long poll: about 1% of polls, spread evenly
            # over the day (2026-11 diagnosis). offset isn't advanced, so
            # Telegram re-delivers any pending command on the next poll.
            logger.warning(f"Polling error (network, retrying): {_redact(e)}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Polling error: {_redact(e)}")
            time.sleep(5)
