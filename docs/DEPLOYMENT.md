# Deployment & Operations

Operational runbook for the Funda Scraper Bot on the Linux VPS (Ubuntu, systemd).
The routine deploy command and dev workflow are in [CONTRIBUTING.md](../CONTRIBUTING.md#deploy).

> **In flight:** the gitignored-config model and the migration below land with
> `fix/h2-config-split` (see [WORKING_PLAN.md](WORKING_PLAN.md)). Until that merges,
> `config.yaml` is still tracked; the migration is what you run when you merge it.

## First-time install

```bash
git clone https://github.com/nkuzmit/Funda-scrapper.git
cd Funda-Scrapper
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env                       # fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ...
cp config.example.yaml config.yaml         # or let the bot create it on first run
cp funda-bot.service /etc/systemd/system/  # adjust WorkingDirectory/ExecStart if paths differ
systemctl enable --now funda-bot
```

## One-time migration: config.yaml becomes untracked

With H2, `config.yaml` is gitignored (rewritten live by the Telegram commands).
On a server that still tracks it, run this once so `git pull` stops conflicting:

```bash
cp config.yaml ~/funda-config.bak          # back up your live filters
git fetch origin && git reset --hard origin/main
cp ~/funda-config.bak config.yaml          # restore (now gitignored)
systemctl restart funda-bot
```

## Smoke test (after every deploy)

1. `systemctl status funda-bot` → `active (running)`.
2. `tail -n 30 main.log` → a recent `Found N new listings` line, and **no**
   `bot-challenge` or `Nuxt payload not found` warnings.
3. In Telegram, send `/run`. Within ~30s expect either listings or
   `All caught up — no new listings found.`
4. If a listing arrives, confirm it includes **photos** (regression-prone — the
   tiara-media backend). Photoless ⇒ re-check `scraper._photo_url`.

## Server reference

- Ubuntu VPS, systemd unit `funda-bot`, repo at `/home/Funda-scrapper`.
- Logs: `journalctl -u funda-bot -f` (system) · `tail -f main.log` (app).
- Host/SSH/credentials are recorded in the local `project_deployment` memory (not in git).
