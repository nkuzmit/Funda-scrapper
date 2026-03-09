import requests
import logging

logging.basicConfig(filename='notifier.log', level=logging.ERROR)

def send_telegram_message(bot_token, chat_id, message, photo_url=None):
    """
    Send a message to Telegram, with optional photo.
    """
    try:
        if photo_url:
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            data = {'chat_id': chat_id, 'caption': message}
            # For photo, need to send as file or URL
            # Assuming photo_url is direct URL
            data['photo'] = photo_url
            response = requests.post(url, data=data)
        else:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {'chat_id': chat_id, 'text': message}
            response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error sending Telegram message: {e}")
        return None

def notify_listing(bot_token, chat_id, listing):
    """
    Notify about a new listing via Telegram.
    """
    message = f"🏠 {listing['title']}\n💰 {listing['price']}\n📍 {listing['location']}\n📐 {listing['size']}\n🛏️ {listing['rooms']}\n🔗 {listing['url']}"
    photo = listing.get('thumbnail')
    send_telegram_message(bot_token, chat_id, message, photo)