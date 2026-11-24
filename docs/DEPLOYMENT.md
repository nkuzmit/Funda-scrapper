# Deployment & Operations

Operational runbook for the Funda Scraper Bot on the Linux VPS (Ubuntu, systemd).
The routine deploy command and dev workflow are in [CONTRIBUTING.md](../CONTRIBUTING.md#deploy).

## First-time install

```bash
cd /home                                   # funda-bot.service expects /home/Funda-scrapper
git clone https://github.com/nkuzmit/Funda-scrapper.git
cd Funda-scrapper                          # lowercase s, as cloned
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env                       # fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ...
cp config.example.yaml config.yaml         # or let the bot create it on first run
cp funda-bot.service /etc/systemd/system/  # adjust WorkingDirectory/ExecStart if paths differ
systemctl enable --now funda-bot
```

## One-time migration: config.yaml becomes untracked

> **Already run on the production VPS (2026-06-25).** Kept for reference and for
> standing up a new server from an old clone. Don't re-run it on a working
> server — `git reset --hard` will discard any uncommitted local state.

With H2, `config.yaml` is gitignored (rewritten live by the Telegram commands).
On a server that still tracks it, run this once so `git pull` stops conflicting:

```bash
cp config.yaml ~/funda-config.bak          # back up your live filters
git fetch origin && git reset --hard origin/main
cp ~/funda-config.bak config.yaml          # restore (now gitignored)
systemctl restart funda-bot
```

## Smoke test (after every deploy)

1. `systemctl status funda-bot` → `active (running)`, and `grep "Scheduler started"
   main.log | tail -1` lists the same times as `schedule.hours` in the server's
   `config.yaml`.
2. `tail -n 30 main.log` → a recent `Found N new listings` line, and **no**
   `Scrape failed:` or `Error in scrape_and_notify` lines (the reason follows, e.g.
   `bot-challenge`, `Nuxt payload not found`, `Parsed 0 listings but Funda reports M
   matches` — the last one is a payload-shape change like the 2026-11-05 ShallowRef
   outage). Also **no** `Skipped K of L listings while parsing: <reasons>` WARNING: the
   parser dropped listings. That's a partial parse, logged but not treated as a failure,
   so it never alerts. Two more ERROR lines to check for:
   - `Polling error: Telegram replied <code>: …`: Telegram is refusing the bot's polls,
     for example a revoked token (401) or a second poller (409). Commands won't work.
   - `Failed to send Telegram message: …`: a command reply, or the scrape-failure alert,
     was rejected.
3. In Telegram, send `/run`. Within ~30s expect either listings or
   `All caught up — no new listings found.` Other replies:
   - `⚠️ N new listing(s) could not be sent` — delivery failed, check `main.log`.
   - `⚠️ Run failed: <reason>` — the scrape itself failed. One failure can be a blip;
     after 2 failed runs in a row the bot sends a `🚨 Scraping has failed` alert on its
     own, and `✅ Scraping recovered` once a run succeeds again.
4. If a listing arrives, confirm it includes **photos** (regression-prone — the
   tiara-media backend). Photoless ⇒ first check `main.log` for `sending text only`
   (Telegram rejected the photos; the text fallback kicked in), else re-check
   `scraper._photo_url`.

## Server reference

- Hetzner VPS (Ubuntu 24.04), systemd unit `funda-bot`, repo at `/home/Funda-scrapper`.
- **Runs as `root`** — there is no `ubuntu` user on this server. `funda-bot.service`
  in the repo matches this as of 2026-08-15; it previously did not.
- **A change to `funda-bot.service` needs one manual step.** `git pull` updates the
  repo copy only; systemd runs `/etc/systemd/system/funda-bot.service`. After the
  deploy, from the repo:
  `cp funda-bot.service /etc/systemd/system/ && systemctl daemon-reload`.
  A restart isn't needed for ordering changes (`After=`, `Wants=`): they apply at the
  next boot.
- Sanity-check after any unit change:
  `systemctl show funda-bot -p WorkingDirectory -p User -p After -p Wants`, and
  `diff /etc/systemd/system/funda-bot.service funda-bot.service` prints nothing.
- Logs: `journalctl -u funda-bot -f` (system) · `tail -f main.log` (app).
- Host/SSH/credentials are recorded in the local `project_deployment` memory (not in git).
