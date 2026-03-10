import requests
import logging

logger = logging.getLogger(__name__)


def send_telegram_message(bot_token: str, chat_id: str, message: str, photo_url: str | None = None):
    """Send a Telegram message or photo with caption."""
    try:
        if photo_url:
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            data = {'chat_id': chat_id, 'caption': message, 'photo': photo_url}
            response = requests.post(url, data=data)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {'chat_id': chat_id, 'text': message}
            response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return None


def notify_listing(bot_token: str, chat_id: str, listing: dict):
    """Format a listing as text and send via Telegram."""
    message = (
        f"🏠 {listing.get('title')}\n"
        f"💰 {listing.get('price')}\n"
        f"📍 {listing.get('location')}\n"
        f"📐 {listing.get('size')}\n"
        f"🛏️ {listing.get('rooms')}\n"
        f"🔗 {listing.get('url')}"
    )
    photo = listing.get('thumbnail')
    send_telegram_message(bot_token, chat_id, message, photo)
