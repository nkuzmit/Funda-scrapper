# Funda Scraper Bot

A bot that monitors [funda.nl](https://www.funda.nl) for new house-for-sale listings and delivers matches across multiple notification channels.

## Features

- Fetches listings by extracting the Nuxt server-side payload from funda.nl (structured JSON data, no fragile HTML parsing)
- Filters by price, bedrooms, area, energy label, and keywords
- Notifications via **Telegram**, **Email (SMTP/HTML)**, and **WhatsApp (CallMeBot)**
- Sends up to 6 listing photos as a Telegram album per notification
- Persists seen listings in SQLite to avoid duplicate notifications
- Listings are only marked as seen after confirmed delivery — failed sends are retried on the next run
- Scheduled daily runs at configurable times (Europe/Amsterdam timezone)
- Filters configurable live via Telegram commands — no restart needed

## Requirements

- Python 3.10+
- Internet connection
- At least one notification channel configured (see Setup)

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in the credentials for whichever channels you want active:

```bash
cp .env.example .env
```

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Email (SMTP — Gmail by default)
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENT=recipient@example.com

# WhatsApp (CallMeBot)
WHATSAPP_PHONE=+31612345678
WHATSAPP_APIKEY=your_callmebot_apikey
```

Credentials never go in `config.yaml` — `.env` is gitignored.

### 3. Enable channels in config.yaml

```yaml
notifications:
  channels: ["telegram"]          # add "email" and/or "whatsapp" as needed
```

### 4. Run the bot

```bash
python main.py
```

---

## Channel Setup

### Telegram

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts — copy the bot token
3. Start a conversation with your bot, then visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find the `chat.id` value in the response

### Email

The bot uses SMTP with STARTTLS (Gmail by default, port 587).

For Gmail, generate an **App Password** (requires 2FA enabled):
`Google Account → Security → 2-Step Verification → App passwords`

Use the app password as `EMAIL_PASSWORD` — not your regular account password.

To use a different provider, pass `smtp_host` and `smtp_port` when constructing `EmailNotifier` in `notifier.py` (defaults: `smtp.gmail.com`, `587`).

### WhatsApp (CallMeBot)

1. Add the CallMeBot number to your WhatsApp contacts: **+34 644 59 97 23**
2. Send this message to that number via WhatsApp:
   `I allow callmebot to send me messages`
3. You'll receive an API key in reply — set it as `WHATSAPP_APIKEY` in `.env`
4. Set `WHATSAPP_PHONE` to your full international number (e.g. `+31612345678`)

> CallMeBot is a free, unofficial service — suitable for personal use but not production-grade.

---

## Configuration

Edit `config.yaml` to customise filters and schedule. Credentials are in `.env` only.

```yaml
notifications:
  channels: ["telegram"]        # active channels: telegram, email, whatsapp

filters:
  areas:                        # funda.nl area slugs; empty = no filter
    - "utrecht/oudwijk"
  price_min: 550000             # null = no lower bound
  price_max: null               # null = no upper bound
  publication_days: 3           # listings published within this many days
  energy_labels: ["A", "B"]    # null or empty = no filter
  min_bedrooms: 1               # null = no lower bound
  keywords: []                  # match any keyword in listing title; empty = no filter

schedule:
  hours: ["7:00", "9:00", "12:00", "15:00", "16:00", "18:00"]
```

**Area slugs** are neighbourhood path fragments from funda.nl. To find a slug: navigate to a neighbourhood on funda.nl, then copy the `city/neighbourhood` portion from the URL (e.g. `utrecht/oudwijk`).

**Schedule times** are in `HH:MM` format (24-hour, Europe/Amsterdam timezone). The bot must be restarted to pick up schedule changes.

---

## Telegram Commands

When Telegram is configured, the bot accepts commands directly in the chat:

| Command | Description |
|---------|-------------|
| `/filters` | Show current active filters |
| `/run` | Trigger an immediate scrape |
| `/setprice 500000 null` | Set price range (`null` = no bound) |
| `/setrooms 2` | Set minimum bedrooms |
| `/setlabel A B C` | Set energy labels |
| `/setdate 3` | Set publication days (max 10) |
| `/addarea utrecht/oudwijk` | Add an area slug |
| `/removearea utrecht/oudwijk` | Remove an area slug |
| `/addkeyword tuin` | Add a keyword filter |
| `/removekeyword tuin` | Remove a keyword filter |
| `/help` | List all commands |

Filter changes take effect on the next scheduled run and are written back to `config.yaml` automatically. If no areas are configured on startup, the bot sends a help message prompting you to set up your filters.

---

## Project Structure

```
main.py                  Entry point — wires config, notifiers, and scheduler
src/funda_bot/
  scraper.py             Extracts listings from Funda Nuxt payload; manages SQLite seen-state
  filters.py             Post-scrape filter matching (price, rooms, labels, keywords)
  notifier.py            Notifier protocol + Telegram / Email / WhatsApp implementations
  scheduler.py           APScheduler wrapper; runs callback at configured daily times
  commands.py            Telegram command handler + polling loop for live config changes
config.yaml              Non-sensitive configuration (filters, schedule, active channels)
.env                     Secrets (credentials) — gitignored, never committed
requirements.txt         Runtime dependencies
requirements-dev.txt     Development dependencies (pytest)
```

**Runtime files** (auto-created, gitignored):
- `seen_listings.db` — SQLite database of delivered listing URLs
- `main.log` — application log

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Deployment (Linux / Hetzner)

### 1. Clone and install

```bash
git clone https://github.com/nkuzmit/Funda-scrapper.git
cd Funda-Scrapper
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Create `.env` with credentials

```bash
cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, etc.
```

### 3. Install systemd service

```bash
cp funda-bot.service /etc/systemd/system/
# edit WorkingDirectory and ExecStart paths if your install path differs
systemctl enable --now funda-bot
systemctl status funda-bot
```

### Useful commands

```bash
systemctl status funda-bot                            # check status
journalctl -u funda-bot -f                            # live system logs
tail -f main.log                                      # app logs
systemctl restart funda-bot                           # restart after config change
git pull origin main && systemctl restart funda-bot   # deploy update
```

---

## Notes

- **Personal use only.** Scraping funda.nl for commercial purposes violates their Terms of Service. The bot is designed for fast new-listing alerts, not as a full Funda browsing replacement.
- The bot uses the Dutch-language Funda endpoint (`/zoeken/koop`). The English endpoint (`/en/zoeken/koop`) excludes same-day listings even with `publication_date` set, so the Dutch endpoint is required for timely alerts.
- `publication_days` is applied both server-side (in the Funda search URL) and client-side (by comparing the `publication_date` field in the Nuxt payload). Listings without a date pass the client-side check unchanged. Recommended maximum is **5 days**; do not exceed 10.
- All schedule times are interpreted in the **Europe/Amsterdam** timezone regardless of server locale.
- On startup the bot runs one immediate scrape before the first scheduled run — useful after a restart so no listings are missed.
