import time
import requests
import logging

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY = 3  # seconds


def _post_with_retry(url: str, data: dict) -> requests.Response | None:
    """POST to *url* with *data*, retrying up to _MAX_RETRIES times on failure."""
    for attempt in range(1, _MAX_RETRIES + 2):
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt <= _MAX_RETRIES:
                logger.warning(f"Attempt {attempt} failed ({e}), retrying in {_RETRY_DELAY}s...")
                time.sleep(_RETRY_DELAY)
            else:
                logger.error(f"All {_MAX_RETRIES + 1} attempts failed: {e}")
    return None


def send_telegram_message(bot_token: str, chat_id: str, message: str, photo_url: str | None = None) -> bool:
    """Send a Telegram message or photo with caption. Returns True on success."""
    if photo_url:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        data = {'chat_id': chat_id, 'caption': message, 'photo': photo_url}
    else:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {'chat_id': chat_id, 'text': message}

    response = _post_with_retry(url, data)
    return response is not None


def notify_listing(bot_token: str, chat_id: str, listing: dict) -> bool:
    """Format a listing as text and send via Telegram. Returns True on success."""
    message = (
        f"🏠 {listing.get('title')}\n"
        f"💰 {listing.get('price')}\n"
        f"📍 {listing.get('location')}\n"
        f"📐 {listing.get('size')}\n"
        f"🛏️ {listing.get('rooms')}\n"
        f"🔗 {listing.get('url')}"
    )
    photo = listing.get('thumbnail')
    return send_telegram_message(bot_token, chat_id, message, photo)
