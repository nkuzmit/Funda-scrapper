# Handoff — 2026-06-25

Branch: main @ 68780ea — deployed.

## What shipped this session
- Photo fix + token redaction + no-areas scrape-gate — deployed.
- M1: ValueError handling on /setprice, /setrooms, /setdate — deployed. 30 tests green.
- Telegram token rotated and re-uploaded to server (token was exposed in session output — needs **one more rotation** before next session).

## Pick up here next
- **Rotate Telegram token one more time** — it appeared in raw `repr()` output during this session (see conversation). Same flow: BotFather → revoke → update local `.env` → tell Claude to re-upload.
- Then start **M2** (`/setlabel` case normalisation) — next item in [docs/WORKING_PLAN.md](WORKING_PLAN.md).

## Open question
- `fix/h2-config-split` branch — pushed, awaiting merge. Needs one-time server migration (see [docs/DEPLOYMENT.md](DEPLOYMENT.md)).
- `setup-wizard` branch — finish-and-merge or drop? Tracked in [docs/WORKING_PLAN.md](WORKING_PLAN.md) Sprint 3.
