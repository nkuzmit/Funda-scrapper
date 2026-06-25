# Handoff — 2026-06-25

Branch: main @ 2f43cc7 — deployed.

## What shipped this session
- Photo fix + token redaction + no-areas scrape-gate — deployed.
- M1: ValueError handling on /setprice, /setrooms, /setdate.
- M2: /setlabel args uppercased before storing.
- M3: thread-safe config via `_CONFIG_LOCK` + deepcopy snapshot in scrape_and_notify.
- Telegram token rotated twice (was exposed in session output).
- CLAUDE.md: no-direct-commits-to-main rule added.
- 34 tests green.

## Pick up here next
- **Sprint 2:** M4 (scraper resilience tests), M5 (pin deps), L1–L3 (cleanups).
  Details in [docs/WORKING_PLAN.md](WORKING_PLAN.md).

## Open questions
- `fix/h2-config-split` branch — pushed, awaiting merge + one-time server migration
  (see [docs/DEPLOYMENT.md](DEPLOYMENT.md)).
- `setup-wizard` branch — finish-and-merge or drop? Sprint 3 decision pending.
