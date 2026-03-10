# Funda Scraper Bot

This is an MVP scraper bot that monitors www.funda.nl for new house-for-sale listings and sends matches to Telegram.

## Features

- Scrapes house listings from funda.nl
- Filters by price, bedrooms, city, keywords
- Sends notifications to Telegram with photo if available
- Persists seen listings to avoid duplicates
- Scheduled runs

## Setup

1. **Get a Telegram Bot Token:**
   - Open Telegram and search for @BotFather
   - Send `/newbot` and follow the instructions
   - Copy the bot token

2. **Get your Chat ID:**
   - Start a conversation with your bot
   - Send a message to the bot
   - Visit `https://api.telegram.org/bot<YourBOTToken>/getUpdates` in your browser
   - Find the "chat" object and copy the "id" value

3. **Configure config.yaml:**
   - Replace `YOUR_TELEGRAM_BOT_TOKEN` with your bot token
   - Replace `YOUR_TELEGRAM_CHAT_ID` with your chat ID
   - Adjust filters and schedule as needed

4. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

5. **Run the bot:**
   ```
   python main.py
   ```

## Configuration

Edit `config.yaml` to customize:

- `telegram`: bot_token and chat_id
- `filters`: set the various criteria used to build the Funda query.
  * `areas`: list of area slugs (for example `utrecht/tuinwijk-oost`).
  * `price_min` / `price_max`: numeric bounds. Leave `price_max` null for no upper limit.
  * `publication_days`: number of past days to include (null for any age).
  * `energy_labels`: whitelist of energy ratings (e.g. `["A+++","A++"]`).
  * `min_bedrooms`: minimum number of rooms.
  * `keywords`: list of keywords to look for in the title.
- `schedule`: hours (list of times to run each day).
  Entries may be simple integers (``9`` = 09:00) or strings like ``"16:08"`` or
  ``"18:30:00"``; missing minutes default to ``:00``.  For example
  ``hours: [7, 9, "12:30", "16:08:00"]`` produces four jobs at 07:00, 09:00,
  12:30 and 16:08.  The scheduler requires the bot to be restarted when the
  configuration is changed.

## Scraper Structure

Here's a simple breakdown of what each file does:

- `main.py`: The main script that starts the bot. It loads the configuration, sets up the scheduler, and runs the scraping and notification process.
- `scraper.py`: Contains functions to scrape listings from Funda.nl. A private helper builds the search URL from the filter settings, then it fetches the webpage, parses the HTML to extract listing details (including optional energy label and publication date), and keeps track of seen listings to avoid duplicates.
- `notifier.py`: Handles sending notifications to Telegram. It formats the listing information into a message and sends it, including a photo if available.
- `scheduler.py`: Manages the timing of scrapes. It uses a scheduler to run the scraping process at specified hours every day.
- `config.yaml`: A configuration file where you set your Telegram bot details, filters for listings, and the schedule for running scrapes.
- `requirements.txt`: Lists all the Python packages needed to run the bot.
- `requirements-dev.txt`: Development dependencies (tests).
- `seen_listings.json`: A file created automatically to store URLs of listings that have already been processed, so you don't get duplicate notifications.
- Log files: `main.log`, `scraper.log`, `notifier.log`, `scheduler.log` for debugging any issues.

## Running Tests

A small test suite verifies the parsing utilities, filter logic, scraper parsing from sample HTML, and notification formatting. To run them:

```bash
pip install -r requirements-dev.txt
pytest
```

## Notes

- The scraper uses BeautifulSoup with requests. If the site requires JavaScript, you may need to switch to Playwright.
- CSS selectors in `scraper.py` are placeholders and may need updating if the site structure changes.
- Logs are saved to `main.log`, `scraper.log`, `notifier.log`, `scheduler.log`
- Seen listings are stored in `seen_listings.json`

## Requirements

- Python 3.9+
- Internet connection
- Telegram account