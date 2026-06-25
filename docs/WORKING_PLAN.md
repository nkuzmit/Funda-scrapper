# Working Plan

Living development plan for the Funda Scraper Bot, and the source of truth for
sprint status and backlog priority. Update this file in the same session you
change behaviour or status (see the stale-doc audit rule in [CLAUDE.md](../CLAUDE.md)).

Last updated: 2026-06-25

## Status snapshot

- **Deployed (2026-06-25):** Sprint 1 — photo fix, token redaction, no-areas guard,
  M1 input validation, M2 /setlabel normalisation, M3 thread-safe config.
- **Deployed (2026-06-25):** H2 config split — `config.yaml` untracked,
  `config.example.yaml` added, bootstrap on first run, server migration run.
- **Deployed (2026-06-25):** Sprint 2 — L2 energy_label None fix, L3 scheduler
  raises on failed start, M5 deps pinned, M4 scraper fixture + 6 Nuxt parser tests.
  40/40 tests. Telegram token rotated.

---

## Sprint 1 — Robustness & correctness · DONE · 2026-06-25

### H2 — Config tracked-vs-runtime split · DONE
`config.yaml` was git-tracked and rewritten at runtime, causing `git pull` deploy
conflicts. Fixed: `config.yaml` gitignored, `config.example.yaml` tracked as
template, `load_config()` bootstraps on first run. Server migration run 2026-06-25.

### M1 — Input validation on commands · DONE
`int()` in `/setprice`, `/setrooms`, `/setdate` catches `ValueError` and sends a
usage hint, leaving config unchanged. 10 unit tests.

### M2 — `/setlabel` case normalisation · DONE
`/setlabel` now uppercases args before persisting, matching the wizard behaviour.
Covered by a test.

### M3 — Thread-safe config access · DONE
`_CONFIG_LOCK` in `commands.py` guards every mutation+save; `scrape_and_notify`
deepcopies filters under the lock before any HTTP call.

---

## Sprint 2 — Resilience & hygiene · DONE · 2026-06-25

### M4 — Scraper resilience tests · DONE
`tests/fixtures/nuxt_payload.json` captures the double-wrapped Nuxt payload
structure. 6 tests cover happy path, photo filtering, bot-challenge, no-payload,
None energy_label, and empty listing list.

### M5 — Pin dependencies · DONE
`requirements.txt` pins all 5 direct deps to known-good versions.

### L2 — energy_label None · DONE
`notifier.py` uses `or 'N/A'` in both plain-text and HTML formatters.

### L3 — Scheduler raise · DONE
`scheduler.py` re-raises after logging a failed `.start()` so a dead scheduler
is visible to the caller.

---

## Sprint 3 — Setup wizard · PARKED

The Phase-4 guided 6-step Telegram setup wizard lives on the unmerged
`setup-wizard` branch. **Decision: park it.** It works as the seed for a bigger
future feature — see Future Vision below.

**Do not merge or deploy** `setup-wizard` as-is: it carries a wiped `config.yaml`,
predates the H1 no-areas fix, and needs reconciliation with H2's bootstrap logic.

---

## Future Vision — Multi-user / multi-channel

The setup wizard is the entry point for making this bot usable by independent
users without manual config editing. When that work resumes, the scope is:

- **Setup wizard**: rebase `setup-wizard` on main, fix the H1/H2 regressions,
  expose it as `/start` so a new user can configure the bot conversationally.
- **WhatsApp channel**: extend `notifier.py` + `build_notifiers()` for WhatsApp
  (CallMeBot plumbing already exists, just needs wiring into wizard onboarding).
- **Multi-user**: each chat_id gets its own filter config (config keyed by chat_id).

This is a meaningful scope expansion — treat it as a new sprint when prioritised.

---

## Known risks

- **Scraper fragility** — Funda can change the payload or block the UA at any time;
  failures degrade to empty results, not errors. M4 fixture tests will catch
  payload shape changes.
- **Python 3.14.3** is bleeding-edge; deps are now pinned (M5).
