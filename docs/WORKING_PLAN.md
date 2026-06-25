# Working Plan

Living development plan for the Funda Scraper Bot, and the source of truth for
sprint status and backlog priority. Update this file in the same session you
change behaviour or status (see the stale-doc audit rule in [CLAUDE.md](../CLAUDE.md)).

Last updated: 2026-06-25

## Status snapshot

- **Shipped to `main` (2026-06-25):** Sprint 1 complete — photo fix, token
  redaction, no-areas guard, M1 input validation, M2 /setlabel normalisation,
  M3 thread-safe config. 34/34 tests.
- **Shipped to `main` (2026-06-25):** H2 config split — `config.yaml` untracked,
  `config.example.yaml` added, bootstrap on first run. Server migration pending.
- **Shipped to `main` (2026-06-25):** Sprint 2 complete — L2 energy_label None
  fix, L3 scheduler raises on failed start, M5 deps pinned, M4 scraper fixture +
  6 Nuxt parser tests. 40/40 tests.

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

## Sprint 2 — Resilience & hygiene · DONE · 2026-06-25

### M4 — Scraper resilience tests · DONE
`tests/fixtures/nuxt_payload.json` captures the double-wrapped Nuxt payload
structure. 6 tests cover happy path, photo filtering, bot-challenge, no-payload,
None energy_label, and empty listing list.

### M5 — Pin dependencies · DONE
`requirements.txt` now pins all 5 direct deps to their known-good versions.

### L1 — Empty dirs · N/A
`src/controllers`, `src/routes`, `src/services` did not exist; nothing to delete.

### L2 — energy_label None · DONE
`notifier.py` uses `or 'N/A'` in both plain-text and HTML formatters.

### L3 — Scheduler raise · DONE
`scheduler.py` re-raises after logging a failed `.start()` so a dead scheduler
is visible to the caller.

---

## Sprint 3 — Setup wizard (feature decision)

The Phase-4 guided 6-step setup lives unmerged on the `setup-wizard` branch. It also
carries an emptied `config.yaml` (test reset) and predates the H1 no-areas fix.
**Decision needed:** finish + merge, or drop. If merging: rebase on main, restore a
real config, confirm the wizard path no longer triggers an all-NL scrape, and
reconcile with H2's config bootstrap.

---

## Known risks

- **Scraper fragility** is the standing operational risk — Funda can change the
  payload or block the UA at any time; failures degrade to empty results, not errors.
  M4 fixture tests will catch payload shape changes.
- **Python 3.14.3** is bleeding-edge; deps are now pinned (M5 done).
