# Working Plan

Living development plan for the Funda Scraper Bot, and the source of truth for
sprint status and backlog priority. Update this file in the same session you
change behaviour or status (see the stale-doc audit rule in [CLAUDE.md](../CLAUDE.md)).

Last updated: 2026-11-20

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
- **Deployed (2026-11-20 15:14):** ShallowRef parser fix (see the incident below),
  plus a WARNING when Funda reports matches but 0 parse. 51/51 tests. Server on
  `ad5e01b`. **Confirmed live** 2026-11-20 15:20: `Page 1: 3 listings (total
  available: 3)` (owner test with publication_days temporarily set to 10).
- **Deployed (2026-11-20, `00e44bc`):** failed Telegram sends log Telegram's error
  description and the photo URLs.
- **Deployed (2026-11-20 15:52, `4b442f0`):** Telegram photo handling — a rejected
  photo is dropped and replaced by a spare (scraper now keeps 10, sends 6), text-only
  fallback if the album still fails, no retries on a permanent 4xx; `/run` reports
  failed deliveries instead of "All caught up". 61/61 tests.

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

## Incident — ShallowRef payload change · RESOLVED · 2026-11-20

**Outage:** 2026-11-05 12:00 → 2026-11-20 15:14 (deploy), 15 days. Funda's Nuxt
payload started wrapping the search-state `listings` list in `['ShallowRef', idx]`.
`unwrap()` only knew `Ref`/`Reactive`/`ShallowReactive`, so every listing was dropped
silently. `main.log` showed `Page 1: 0 listings (total available: N)` with N > 0 on
172 runs (last on 2026-11-19 20:00), with no warning. The owner caught it via two
Funda e-mail alerts (published 11-10 and 11-12) that the bot never sent. The fix sat
on an unpushed local `dev` from 11-16 to 11-20, which added 4 days to the outage.

**Fix (`fix/nuxt-shallowref`, deployed 2026-11-20):** add `'ShallowRef'` to the unwrap
tuple, plus a regression test using the live single-ShallowRef shape. It was verified
against a saved live search page (total 2 → 2 listings), then on the server on
2026-11-20 15:20 (total 3 → 3 listings).

**Follow-up (`feat/parse-mismatch-warning`, deployed 2026-11-20):** log a WARNING when
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

## Open issues

- **Telegram `sendMediaGroup` 400** — fix deployed 2026-11-20 15:52. 2026-11-20:
  Bekkerstraat 25 failed on two runs (15:20, 15:36) with `failed to send message #3
  with the error message "WEBPAGE_CURL_FAILED"` — Telegram could not download photo
  #3, although the server fetches it fine (`200 image/jpeg`). Why Telegram fails on
  it is unknown. The fix doesn't depend on that: skip the photo / fall back to text.
  Still unverified: that Telegram's `#N` is 1-based — the first live retry of
  Bekkerstraat after deploy will show it (`dropping it:` line, then delivery).
- **`/run` said "All caught up" after a failed send** — fix deployed 2026-11-20 15:52.
  A scrape that *errors* (HTTP error, bot-challenge) still reads as "All caught up";
  that's part of the health-signal gap in Known risks.
- **Telegram polling `Read timed out (read timeout=35)`** — logged as ERROR roughly
  hourly. Not investigated; may be benign long-poll noise.
- **Telegram alerting on parse mismatch** — see Known risks.

---

## Known risks

- **Scraper fragility** — Funda can change the payload or block the UA at any time;
  failures degrade to empty results, not errors. The M4 fixture tests **cannot**
  detect an upstream change, because the fixture is a frozen snapshot. They only
  guard against our own regressions, as the 2026-11-05 ShallowRef outage proved.
  Detection relies on `main.log` (see the smoke test in
  [DEPLOYMENT.md](DEPLOYMENT.md)). Nothing alerts on Telegram yet.
- **Python 3.14.3** is bleeding-edge; deps are now pinned (M5).
