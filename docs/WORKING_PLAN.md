# Working Plan

Living development plan for the Funda Scraper Bot, and the source of truth for
sprint status and backlog priority. Update this file in the same session you
change behaviour or status (see the stale-doc audit rule in [CLAUDE.md](../CLAUDE.md)).

Last updated: 2026-11-16

## Status snapshot

- **Deployed (2026-06-25):** Sprint 1 — photo fix, token redaction, no-areas guard,
  M1 input validation, M2 /setlabel normalisation, M3 thread-safe config.
- **Deployed (2026-06-25):** H2 config split — `config.yaml` untracked,
  `config.example.yaml` added, bootstrap on first run, server migration run.
- **Deployed (2026-06-25):** Sprint 2 — L2 energy_label None fix, L3 scheduler
  raises on failed start, M5 deps pinned, M4 scraper fixture + 6 Nuxt parser tests.
  40/40 tests. Telegram token rotated.
- **Deployed (2026-06-25):** floor_area filter (URL param + post-filter + /setfloor),
  amenities filter (/addamenity /removeamenity), bedrooms sent as URL param.
  48/48 tests. Server filter values were updated to match.
- **On `dev`, not yet deployed (2026-11-16):** ShallowRef parser fix — see the
  incident below. 49/49 tests. **The server is still broken until `dev` → `main` is
  merged and deployed.**
- **On branch `feat/parse-mismatch-warning`, not merged:** WARNING when Funda reports
  matches but 0 parse. 51/51 tests on that branch. Awaiting a merge decision.

> Live filter values are **not** recorded here — `config.yaml` on the server is their
> only home (it's rewritten by the Telegram commands, so any copy here goes stale the
> next time someone sends `/addarea`). Check with `/filters` in Telegram.

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

## Incident — ShallowRef payload change · FIXED on dev · 2026-11-16

**Outage:** 2026-11-05 12:00 → fix deploy. Funda's Nuxt payload started wrapping the
search-state `listings` list in `['ShallowRef', idx]`. `unwrap()` only knew
`Ref`/`Reactive`/`ShallowReactive`, so every listing was dropped silently. `main.log`
showed `Page 1: 0 listings (total available: N)` with N > 0 on 125 runs, with no
warning. The owner caught it via two Funda e-mail alerts (published 11-10 and 11-12)
that the bot never sent.

**Fix (`fix/nuxt-shallowref`, merged to dev):** add `'ShallowRef'` to the unwrap
tuple, plus a regression test using the live single-ShallowRef shape. It was verified
against a saved live search page: total 2 → 2 listings.

**Follow-up (`feat/parse-mismatch-warning`, unmerged):** log a WARNING when
`totalListingsCount > 0` but 0 listings parse, or when the listings field isn't a
list. Logging only: no Telegram alert, no retry. Alerting is still an open decision
(see Known risks).

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
  failures degrade to empty results, not errors. The M4 fixture tests **cannot**
  detect an upstream change, because the fixture is a frozen snapshot. They only
  guard against our own regressions, as the 2026-11-05 ShallowRef outage proved.
  Detection relies on `main.log` (see the smoke test in
  [DEPLOYMENT.md](DEPLOYMENT.md)). Nothing alerts on Telegram yet.
- **Python 3.14.3** is bleeding-edge; deps are now pinned (M5).
