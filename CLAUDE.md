# CLAUDE.md

Guidance for Claude Code working in this repo. Keep it short; link, don't restate.

## What this is

A personal bot that watches funda.nl for new for-sale listings and pushes matches to
Telegram (and optionally email / WhatsApp). Python, single-user, deployed on a Linux
VPS as a systemd service. Design ethos: **AK-47** — simple, robust, no overengineering
(see `.github/instructions/instruction.instructions.md`).

## Commands

```bash
venv/Scripts/python -m pytest -q     # tests (venv Python, not system)
venv/Scripts/python main.py          # run the bot locally
```

## Conventions

- **venv Python only** — system Python (also 3.14.x) lacks the deps.
- **Test before commit**; `pytest` green is the gate.
- **Branch per fix/feature** off `main`; `main` is the deploy trunk. See [CONTRIBUTING.md](CONTRIBUTING.md).
  **Never commit directly to `main`.** Always create a branch (e.g. `fix/m2-setlabel`), implement there, then merge.
- Secrets in `.env`; live config in `config.yaml` (gitignored). Never commit either.

## Stale-doc audit rule

Each fact has exactly one home. When you change behaviour or status, update the doc
that owns that fact **in the same session** — never let two docs state it:

- Sprint status / backlog → [docs/WORKING_PLAN.md](docs/WORKING_PLAN.md)
- Deploy command + workflow → [CONTRIBUTING.md](CONTRIBUTING.md)
- Deploy runbook / smoke test → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Session handoff → `docs/handoff-tns.md` (overwrite each session; delete if no carryover)

If a handoff or sprint claim contradicts `docs/WORKING_PLAN.md`, fix WORKING_PLAN.md —
don't restate it elsewhere.
