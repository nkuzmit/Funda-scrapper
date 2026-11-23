"""Notification channel abstractions.

Each channel implements the Notifier protocol.  The active set of channels
is assembled by build_notifiers() from the loaded config + environment.

Adding a new channel:
  1. Implement a class with notify(listing: dict) -> bool
  2. Add its env-var credentials to .env
  3. Register it in build_notifiers()
  4. Add the channel name to notifications.channels in config.yaml
"""

from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import requests

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY = 3  # seconds

# Photos per notification. The scraper keeps a few more as spares: when
# Telegram can't fetch one, it is dropped and the next spare moves up.
_PHOTOS_PER_MESSAGE = 6
_MAX_PHOTO_SKIPS = 3

# Telegram's (undocumented) error text when one album item can't be fetched,
# e.g. 'failed to send message #3 with the error message "WEBPAGE_CURL_FAILED"'.
_REJECTED_PHOTO_RE = re.compile(r'failed to send message #(\d+)')

# Credentials travel in request URLs and leak through requests' exception
# messages: the Telegram bot token in the path, CallMeBot's API key and phone
# number as query params (review C5). Scrub them before logging.
_TOKEN_RE = re.compile(r'bot\d+:[A-Za-z0-9_-]+')
_QUERY_SECRET_RE = re.compile(r'(?<=[?&])(apikey|phone)=[^&\s\'"]+')


def _redact(text) -> str:
    """Remove the Telegram bot token and CallMeBot credentials from a string before logging."""
    text = _TOKEN_RE.sub('bot<redacted>', str(text))
    return _QUERY_SECRET_RE.sub(r'\1=<redacted>', text)


def _error_detail(e: Exception) -> str:
    """The exception text plus, for HTTP errors, the start of the response body.

    Telegram explains a 400 only in the body (e.g. which media item it rejected);
    the exception message alone just says 'Bad Request'.
    """
    detail = str(e)
    response = getattr(e, 'response', None)
    if response is not None and response.text:
        detail += f' | response: {response.text[:300]}'
    return _redact(detail)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fmt_price(price) -> str:
    """Format a raw integer price as '€ 875,000'."""
    try:
        return f"€ {int(price):,}".replace(',', '.')
    except (TypeError, ValueError):
        return str(price) if price is not None else 'Unknown'


def _is_permanent(e: Exception) -> bool:
    """True for a 4xx other than 429: resending the same request fails the same way."""
    status = getattr(getattr(e, 'response', None), 'status_code', None)
    return status is not None and 400 <= status < 500 and status != 429


def _request_with_retry(
    url: str, data: dict | None = None, params: dict | None = None
) -> tuple[requests.Response | None, Exception | None]:
    """HTTP request with up to _MAX_RETRIES retries. Uses POST when data is provided, GET otherwise.

    Returns (response, None) on success, (None, last_error) on failure.
    A permanent 4xx is not retried.
    """
    for attempt in range(1, _MAX_RETRIES + 2):
        try:
            if data:
                response = requests.post(url, data=data, timeout=10)
            else:
                response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response, None
        except Exception as e:
            if _is_permanent(e):
                logger.error(f"Request rejected, not retrying: {_error_detail(e)}")
                return None, e
            if attempt <= _MAX_RETRIES:
                logger.warning(f"Attempt {attempt} failed ({_error_detail(e)}), retrying in {_RETRY_DELAY}s...")
                time.sleep(_RETRY_DELAY)
            else:
                logger.error(f"All {_MAX_RETRIES + 1} attempts failed: {_error_detail(e)}")
                return None, e
    return None, None  # unreachable: the loop always returns


def _rejected_photo(error: Exception | None, n_sent: int) -> int | None:
    """0-based index of the album photo Telegram says it couldn't send, or None.

    Telegram numbers album items from 1 (confirmed live 2026-11-20: dropping
    '#3' = photos[2] made the resend succeed). If that ever changes, the resend
    fails too and notify() falls back to text.
    """
    response = getattr(error, 'response', None)
    if response is None:
        return None
    match = _REJECTED_PHOTO_RE.search(response.text or '')
    if not match:
        return None
    index = int(match.group(1)) - 1
    return index if 0 <= index < n_sent else None


def _format_plain(listing: dict) -> str:
    """Format listing as a plain-text message."""
    return (
        f"🏠 {listing.get('title')}\n"
        f"💰 {_fmt_price(listing.get('price'))}\n"
        f"📍 {listing.get('location')}\n"
        f"📐 {listing.get('size')} m²\n"
        f"🛏️  {listing.get('bedrooms')} bedrooms / {listing.get('rooms')} rooms\n"
        f"⚡ {listing.get('energy_label') or 'N/A'}\n"
        f"🔗 {listing.get('url')}"
    )


def _format_html(listing: dict) -> str:
    """Format listing as an HTML email body."""
    photos = (listing.get('photos') or [])[:_PHOTOS_PER_MESSAGE]
    imgs = ''.join(
        f'<img src="{p}" style="width:48%;margin:1%;border-radius:6px;">'
        for p in photos
    )
    photo_block = f'<div style="margin-bottom:12px;">{imgs}</div>' if imgs else ''
    return f"""
<html><body style="font-family:sans-serif;max-width:600px;">
{photo_block}
<h2>🏠 {listing.get('title')}</h2>
<table cellpadding="6">
  <tr><td><b>Price</b></td><td>{_fmt_price(listing.get('price'))}</td></tr>
  <tr><td><b>Location</b></td><td>{listing.get('location')}</td></tr>
  <tr><td><b>Size</b></td><td>{listing.get('size')} m²</td></tr>
  <tr><td><b>Rooms</b></td><td>{listing.get('bedrooms')} bedrooms / {listing.get('rooms')} total</td></tr>
  <tr><td><b>Energy label</b></td><td>{listing.get('energy_label') or 'N/A'}</td></tr>
</table>
<p><a href="{listing.get('url')}">View on Funda →</a></p>
</body></html>
"""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class Notifier(Protocol):
    def notify(self, listing: dict) -> bool:
        """Send notification for *listing*. Returns True on success."""
        ...


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def _send(self, message: str, photos: list[str]) -> tuple[bool, Exception | None]:
        """One send: an album for 2+ photos, a photo for 1, plain text for none.

        Returns (ok, error) — the error lets notify() see which photo was rejected.
        """
        api = f"https://api.telegram.org/bot{self.bot_token}"
        if len(photos) > 1:
            media = [
                {'type': 'photo', 'media': url, **({"caption": message} if i == 0 else {})}
                for i, url in enumerate(photos)
            ]
            url = f"{api}/sendMediaGroup"
            data = {'chat_id': self.chat_id, 'media': json.dumps(media)}
        elif photos:
            url = f"{api}/sendPhoto"
            data = {'chat_id': self.chat_id, 'caption': message, 'photo': photos[0]}
        else:
            url = f"{api}/sendMessage"
            data = {'chat_id': self.chat_id, 'text': message}
        response, error = _request_with_retry(url, data)
        return response is not None, error

    def notify(self, listing: dict) -> bool:
        message = _format_plain(listing)
        photos = list(listing.get('photos') or [])

        # Telegram downloads photo URLs itself and can fail on one we can fetch
        # fine (WEBPAGE_CURL_FAILED, 2026-11-20). Drop the photo it names and let
        # the next spare move up; with no spares the album just gets smaller.
        for _ in range(_MAX_PHOTO_SKIPS + 1):
            batch = photos[:_PHOTOS_PER_MESSAGE]
            ok, error = self._send(message, batch)
            if ok:
                return True
            bad = _rejected_photo(error, len(batch))
            if bad is None:
                break
            logger.warning(f"Telegram could not send photo {bad + 1} of {len(batch)}, dropping it: {batch[bad]}")
            del photos[bad]

        if not batch:  # the last attempt was already text-only
            return False
        # Never lose the listing over a photo.
        logger.warning(f"Telegram send with photos failed, sending text only. Photo URLs were: {batch}")
        ok, _ = self._send(message, [])
        return ok


# ---------------------------------------------------------------------------
# Email (SMTP / HTML)
# ---------------------------------------------------------------------------

class EmailNotifier:
    def __init__(self, sender: str, password: str, recipient: str, smtp_host: str = 'smtp.gmail.com', smtp_port: int = 587):
        self.sender = sender
        self.password = password
        self.recipient = recipient
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def notify(self, listing: dict) -> bool:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🏠 New listing: {listing.get('title')} — {_fmt_price(listing.get('price'))}"
        msg['From'] = self.sender
        msg['To'] = self.recipient
        msg.attach(MIMEText(_format_plain(listing), 'plain'))
        msg.attach(MIMEText(_format_html(listing), 'html'))

        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.ehlo()
                    server.starttls()
                    server.login(self.sender, self.password)
                    server.sendmail(self.sender, self.recipient, msg.as_string())
                return True
            except Exception as e:
                if attempt <= _MAX_RETRIES:
                    logger.warning(f"Email attempt {attempt} failed ({e}), retrying in {_RETRY_DELAY}s...")
                    time.sleep(_RETRY_DELAY)
                else:
                    logger.error(f"Email send failed after {_MAX_RETRIES + 1} attempts: {e}")
        return False


# ---------------------------------------------------------------------------
# WhatsApp (CallMeBot)
# ---------------------------------------------------------------------------

class WhatsAppNotifier:
    _API_URL = 'https://api.callmebot.com/whatsapp.php'

    def __init__(self, phone: str, apikey: str):
        self.phone = phone
        self.apikey = apikey

    def notify(self, listing: dict) -> bool:
        params = {
            'phone': self.phone,
            'text': _format_plain(listing),
            'apikey': self.apikey,
        }
        response, _ = _request_with_retry(self._API_URL, params=params)
        return response is not None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_notifiers(config: dict) -> list[Notifier]:
    """Instantiate all active notifiers from config + environment variables."""
    # An empty YAML key loads as None; treat it as "no channels" (review C13).
    channels = (config.get('notifications') or {}).get('channels') or []
    notifiers: list[Notifier] = []

    if 'telegram' in channels:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if token and chat_id:
            notifiers.append(TelegramNotifier(token, chat_id))
        else:
            logger.warning("Telegram channel enabled but TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set.")

    if 'email' in channels:
        sender = os.getenv('EMAIL_SENDER')
        password = os.getenv('EMAIL_PASSWORD')
        recipient = os.getenv('EMAIL_RECIPIENT')
        if sender and password and recipient:
            notifiers.append(EmailNotifier(sender, password, recipient))
        else:
            logger.warning("Email channel enabled but EMAIL_SENDER / EMAIL_PASSWORD / EMAIL_RECIPIENT not set.")

    if 'whatsapp' in channels:
        phone = os.getenv('WHATSAPP_PHONE')
        apikey = os.getenv('WHATSAPP_APIKEY')
        if phone and apikey:
            notifiers.append(WhatsAppNotifier(phone, apikey))
        else:
            logger.warning("WhatsApp channel enabled but WHATSAPP_PHONE / WHATSAPP_APIKEY not set.")

    return notifiers
