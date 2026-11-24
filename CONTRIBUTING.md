# Contributing

A personal project, but these conventions keep deploys boring and safe.

## Local setup

Use **Python 3.12**, the version production runs, so tests run on the same interpreter.
If you don't have it, `uv python install 3.12.3` will install it.

```bash
python3.12 -m venv venv
venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt   # Windows
# venv/bin/pip on Linux
```

Always use the **venv** Python, not system Python (system Python lacks the deps):

```bash
venv/Scripts/python main.py            # run locally
venv/Scripts/python -m pytest -q       # tests
```

## Workflow

Three tiers: a short-lived `<kind>/<topic>` branch → `dev` → `main`. The kinds in use
are `feat/`, `fix/`, `docs/`, `test/` and `deps/`.

```
feat/listing-history ─┐
fix/scraper-retry ────┼─►  dev  ─►  main  ─►  server
docs/whatever ────────┘        (deploy gate)
```

- **`main` is the deploy trunk.** The server runs whatever is on `origin/main`.
  **Never commit to it directly.**
- **`dev` is the integration branch.** Finished, tested work accumulates here. Don't
  accumulate speculative or half-finished work on it either — that's what the
  per-change branches are for.
- **A branch for any change that touches more than one file or carries any
  uncertainty about the approach**, cut from `dev` (e.g. `fix/scraper-retry`) before
  the first edit. Implement + test there, then merge to `dev` once it works.
- **A single-file docs change goes straight to `dev`** when it records something
  already settled: a deploy record, a status line, the session handoff. One commit, no
  branch, no merge.
- **Merge `dev` → `main` only when you intend to deploy.** That merge is the gate.
- **Test locally before committing** — `pytest` green is the gate; for Telegram or
  scraper changes, also run the bot or a live check.
- Keep commits atomic and revertable — one concern per commit, and say in the body what
  changed *and what didn't*. Never commit `.env`, `config.yaml`, `seen_listings.db`,
  or `*.log` (all gitignored).

## Deploy

After merging `dev` → `main`, deploy from the server:

```bash
git pull origin main && venv/bin/pip install -q -r requirements.txt && systemctl restart funda-bot
```

`pip install` makes the server's venv match `requirements.txt`, and does nothing when it
already does. Skipping it let the server drift: it ran APScheduler 3.11.2 for 8 months
while the pins said 3.10.4 (found 2026-11-23).

The command doesn't install `funda-bot.service`: a change to the unit needs the step
under "Server reference" in DEPLOYMENT.md.

Full install, the one-time config migration, and the post-deploy smoke test are in
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Plan and backlog: [docs/WORKING_PLAN.md](docs/WORKING_PLAN.md).
