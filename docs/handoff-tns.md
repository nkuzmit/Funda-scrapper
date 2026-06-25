# Handoff — 2026-06-25

Branch: main @ 59ac665, fix/h2-config-split @ 257740d (H2, pushed, awaiting merge)
Last shipped: photo restore + token redaction + no-areas scrape-gate on main (1ebea60), pushed — not yet deployed.

## Pick up here next
- **Deploy `main`** so the photo fix reaches the user — it is live in code only.
  Deploy command and post-deploy smoke test: [CONTRIBUTING.md](../CONTRIBUTING.md#deploy) / [docs/DEPLOYMENT.md](DEPLOYMENT.md).
- Then start **M1** (command/wizard input validation), the next item in [docs/WORKING_PLAN.md](WORKING_PLAN.md).

## Open question
- `setup-wizard` branch — finish-and-merge or drop? It carries an unfinished wizard and
  an emptied config. User to decide; tracked in [docs/WORKING_PLAN.md](WORKING_PLAN.md) Sprint 3.
- Telegram token rotation (exposed pre-redaction) — confirm the user rotated it via @BotFather.
