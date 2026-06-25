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

- **`main` is the deploy trunk.** The server runs whatever is on `origin/main`.
- **One branch per fix/feature**, branched off `main` (e.g. `fix/h2-config-split`).
  Implement + test there, then merge to `main` once reviewed.
- **Test locally before committing** — `pytest` green is the gate; for Telegram or
  scraper changes, also run the bot or a live check.
- Keep commits atomic and revertable. Never commit `.env`, `config.yaml`,
  `seen_listings.db`, or `*.log` (all gitignored).

## Deploy

After merging to `main`, deploy from the server:

```bash
git pull origin main && systemctl restart funda-bot
```

Full install, the one-time config migration, and the post-deploy smoke test are in
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Plan and backlog: [docs/WORKING_PLAN.md](docs/WORKING_PLAN.md).
