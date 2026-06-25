# Working Plan

Living development plan for the Funda Scraper Bot, and the source of truth for
sprint status and backlog priority. Update this file in the same session you
change behaviour or status (see the stale-doc audit rule in [CLAUDE.md](../CLAUDE.md)).

Last updated: 2026-06-25

## Status snapshot

- **Shipped to `main` (2026-06-25):** photo fix (tiara-media backend), Telegram
  token redaction in logs, scrape skipped when no areas configured — deployed.
- **Shipped to `main` (2026-06-25):** M1 input validation, M2 /setlabel case
  normalisation, M3 thread-safe config — all deployed. 34/34 tests pass.
- **In review:** branch `fix/h2-config-split` (H2 below) — pushed, awaiting merge.

## Do first (cross-cutting, not backlog items)

1. **Deploy `main`** to restore listing photos — see [CONTRIBUTING.md](../CONTRIBUTING.md#deploy).
   The photo fix is the user-visible win and is currently live in code only.
2. **Rotate the Telegram bot token** via @BotFather — it was logged in plaintext
   before redaction (main.log + journald), so treat it as compromised.

---

## Sprint 1 — Robustness & correctness

### H2 — Config tracked-vs-runtime split · done on `fix/h2-config-split`, pending merge
`config.yaml` was git-tracked **and** rewritten at runtime, so any Telegram filter
edit made the next `git pull` deploy conflict. Fixed by untracking `config.yaml`,
adding a tracked `config.example.yaml`, and bootstrapping on first run.
- **Deploy:** needs the one-time server migration in [docs/DEPLOYMENT.md](DEPLOYMENT.md).
- **On merge:** drop the branch's root `PLAN.md` edit (replaced by this file); keep
  main's README deploy pointer over the branch's inline migration note (migration
  now lives in DEPLOYMENT.md); README §3 gains the branch's config-bootstrap note.

### M1 — Input validation on commands/wizard · DONE · 2026-06-25
`int()` in `/setprice`, `/setrooms`, `/setdate` now catches `ValueError` and sends a
usage hint, leaving config unchanged. 10 unit tests cover each parsing path.

### M2 — `/setlabel` case normalisation · S
`/setlabel` stores raw-case args while the wizard upper-cases, so `/setlabel a b`
silently matches nothing in `filters.matches_filters`.
- **Done when:** `/setlabel a b` persists `['A','B']`; covered by a test.

### M3 — Thread-safe config access · DONE · 2026-06-25
`_CONFIG_LOCK` in `commands.py` guards every mutation+save; `scrape_and_notify`
deepcopies filters under the lock before any HTTP call. 34 tests green.

---

## Sprint 2 — Resilience & hygiene

### M4 — Scraper resilience tests · M
The scraper depends on Funda's Nuxt payload shape + the `facebookexternalhit` UA; the
photo break was this fragility going silent. Save a real payload as a fixture and test
`_parse_nuxt_listings` + `_photo_url` against it, so a Funda change fails a test
instead of returning `[]` in production.

### M5 — Pin dependencies · S
`requirements.txt` is unpinned and the bot runs on Python 3.14.3. Pin the known-good
set so a fresh install can't pull an incompatible major.

### L1–L3 — Cleanups · S
- **L1:** delete empty `src/controllers`, `src/routes`, `src/services`.
- **L2:** `notifier.py` `.get('energy_label', 'N/A')` returns `"None"` when present-but-None — use `or 'N/A'`.
- **L3:** `scheduler.py` swallows a failed `.start()`; log/raise so a dead scheduler is visible.

---

## Sprint 3 — Setup wizard (feature decision)

The Phase-4 guided 6-step setup lives unmerged on the `setup-wizard` branch. It also
carries an emptied `config.yaml` (test reset) and predates the H1 no-areas fix.
**Decision needed:** finish + merge, or drop. If merging: rebase on main, restore a
real config, confirm the wizard path no longer triggers an all-NL scrape, and
reconcile with H2's config bootstrap.

---

## Known risks

- **Scraper fragility (M4)** is the standing operational risk — Funda can change the
  payload or block the UA at any time; failures degrade to empty results, not errors.
- **Python 3.14.3** is bleeding-edge; unpinned deps (M5) compound this.
