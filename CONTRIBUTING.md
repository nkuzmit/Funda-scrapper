# Contributing

A personal project, but these conventions keep deploys boring and safe.

## Local setup

```bash
python3 -m venv venv
venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt   # Windows
# venv/bin/pip on Linux
```

Always use the **venv** Python, not system Python (system Python lacks the deps):

```bash
venv/Scripts/python main.py            # run locally
venv/Scripts/python -m pytest -q       # tests
```

## Workflow

Three tiers: `feat/*` | `fix/*` → `dev` → `main`.

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
- **One branch per fix/feature**, cut from `dev` (e.g. `fix/h2-config-split`).
  Implement + test there, then merge to `dev` once it works. As soon as a task touches
  more than one file or carries any uncertainty about the approach, branch first.
- **Merge `dev` → `main` only when you intend to deploy.** That merge is the gate.
- **Test locally before committing** — `pytest` green is the gate; for Telegram or
  scraper changes, also run the bot or a live check.
- Keep commits atomic and revertable — one concern per commit, and say in the body what
  changed *and what didn't*. Never commit `.env`, `config.yaml`, `seen_listings.db`,
  or `*.log` (all gitignored).

## Deploy

After merging `dev` → `main`, deploy from the server:

```bash
git pull origin main && systemctl restart funda-bot
```

Full install, the one-time config migration, and the post-deploy smoke test are in
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Plan and backlog: [docs/WORKING_PLAN.md](docs/WORKING_PLAN.md).
