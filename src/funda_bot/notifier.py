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

import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

import requests

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_RETRY_DELAY = 3  # seconds


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _post_with_retry(url: str, data: dict | None = None, params: dict | None = None) -> requests.Response | None:
    """POST (or GET if params-only) with up to _MAX_RETRIES retries."""
    for attempt in range(1, _MAX_RETRIES + 2):
        try:
            if params and not data:
                response = requests.get(url, params=params, timeout=10)
            else:
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


def _format_plain(listing: dict) -> str:
    return (
        f"🏠 {listing.get('title')}\n"
        f"💰 {listing.get('price')}\n"
        f"📍 {listing.get('location')}\n"
        f"📐 {listing.get('size')}\n"
        f"🛏️  {listing.get('rooms')}\n"
        f"🔗 {listing.get('url')}"
    )


def _format_html(listing: dict) -> str:
    return f"""
<html><body>
<h2>🏠 {listing.get('title')}</h2>
<table>
  <tr><td><b>Price</b></td><td>{listing.get('price')}</td></tr>
  <tr><td><b>Location</b></td><td>{listing.get('location')}</td></tr>
  <tr><td><b>Size</b></td><td>{listing.get('size')}</td></tr>
  <tr><td><b>Rooms</b></td><td>{listing.get('rooms')}</td></tr>
  <tr><td><b>Energy label</b></td><td>{listing.get('energy_label', 'N/A')}</td></tr>
</table>
<p><a href="{listing.get('url')}">View on Funda</a></p>
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

    def notify(self, listing: dict) -> bool:
        message = _format_plain(listing)
        photo = listing.get('thumbnail')
        if photo:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            data = {'chat_id': self.chat_id, 'caption': message, 'photo': photo}
        else:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {'chat_id': self.chat_id, 'text': message}
        return _post_with_retry(url, data) is not None


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
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🏠 New listing: {listing.get('title')} — {listing.get('price')}"
            msg['From'] = self.sender
            msg['To'] = self.recipient
            msg.attach(MIMEText(_format_plain(listing), 'plain'))
            msg.attach(MIMEText(_format_html(listing), 'html'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, self.recipient, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
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
        return _post_with_retry(self._API_URL, params=params) is not None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_notifiers(config: dict) -> list[Notifier]:
    """Instantiate all active notifiers from config + environment variables."""
    channels = config.get('notifications', {}).get('channels', [])
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
