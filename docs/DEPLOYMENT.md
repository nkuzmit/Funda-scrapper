# Deployment & Operations

Operational runbook for the Funda Scraper Bot on the Linux VPS (Ubuntu, systemd).
The routine deploy command and dev workflow are in [CONTRIBUTING.md](../CONTRIBUTING.md#deploy).

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

1. `systemctl status funda-bot` → `active (running)`.
2. `tail -n 30 main.log` → a recent `Found N new listings` line, and **no**
   `bot-challenge` or `Nuxt payload not found` warnings.
   On the `Page 1: N listings (total available: M)` line, **N must equal M** whenever
   M ≤ 15. If N is 0 while M > 0, Funda changed the payload shape and the parser is
   dropping listings silently (this was the 2026-11-05 ShallowRef outage).
3. In Telegram, send `/run`. Within ~30s expect either listings or
   `All caught up — no new listings found.`
4. If a listing arrives, confirm it includes **photos** (regression-prone — the
   tiara-media backend). Photoless ⇒ re-check `scraper._photo_url`.

## Server reference

- Hetzner VPS (Ubuntu 24.04), systemd unit `funda-bot`, repo at `/home/Funda-scrapper`.
- **Runs as `root`** — there is no `ubuntu` user on this server. `funda-bot.service`
  in the repo matches this as of 2026-08-15; it previously did not.
- Sanity-check after any unit change:
  `systemctl show funda-bot -p WorkingDirectory -p User`
- Logs: `journalctl -u funda-bot -f` (system) · `tail -f main.log` (app).
- Host/SSH/credentials are recorded in the local `project_deployment` memory (not in git).
