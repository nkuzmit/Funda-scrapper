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
  failed deliveries instead of "All caught up". 61/61 tests. Trigger: Telegram
  couldn't download one Bekkerstraat 25 photo (`WEBPAGE_CURL_FAILED`; the server
  fetches it fine, cause unknown). **Confirmed live** 2026-11-20 15:53: Telegram
  rejected photo #3, it was dropped without retries, and the listing was delivered
  on the next send — which also confirms Telegram's `#N` is 1-based.
- **Deployed (2026-11-20, `591275e`):** `.gitignore` covers rotated logs
  (`main.log.1`–`.3`).
- **Deployed (2026-11-20 16:21, `fc262bf`):** a failed scrape raises `ScrapeError`
  instead of returning `[]`. `/run` replies `⚠️ Run failed: <reason>`. After 2 failed
  runs in a row the bot sends one Telegram alert, then a recovery message (in-memory
  counter, so a restart resets it). 72/72 tests. Verified against two saved live pages
  (3 matches → 3 listings, 0 matches → no error). **Confirmed live** 2026-11-20: the
  startup scrape (16:21) and an owner `/run` (16:23) on the real filters returned
  `0 listings (total available: 0)` with no error. A simulated failure on the server
  (`get_new_listings` patched, no Funda request) sent the 🚨 alert on the 2nd failure
  and ✅ on recovery; the owner confirmed both arrived.

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
list. Logging only at the time; superseded by the scrape-failure alert (see the status
snapshot), which turns both cases into a failed run.

---

## Sprint 4 — Log hygiene · PLANNED

Logs are kept by size (5 MB × 4 = 20 MB cap), not age. 8 months came to 5.3 MB
(2026-03-19 → 2026-11-20). **Decision (2026-11-20): no age-based deletion.** The log is
the bot's health record, and rare failures need a long history: the "alert after 2"
threshold rested on 2 timeouts in July/August that a 30-day window would have deleted.
Deleting `main.log` wouldn't remove the data anyway: every line also goes to the systemd
journal (bot lines back to 2026-07-01, default retention). The real problem is noise —
about 40% of the volume:

| Content | Share of bytes |
|---|---|
| Scrape lines (search URL, page counts) | 53% |
| APScheduler INFO ("Running job", "Job executed", "Added job") | 29% |
| `Polling error` ERRORs (4,486) | 13% |
| Everything else | 5% |

### L4 — Quiet APScheduler · BUILT, not yet deployed (`feat/quiet-apscheduler`)
The `apscheduler` logger is set to WARNING in `main.py`. In APScheduler 3.10.4 a missed
run and a skipped overlapping run log at WARNING, and a job that raised logs at ERROR,
so they still get through. The startup "Added job" lines are replaced by one line from
`funda_bot.scheduler`: `Scheduler started: N runs a day (Europe/Amsterdam) at …`.
Expect about 29% less volume. 74/74 tests. Verify after deploy: the `Scheduler
started: 14 runs a day` line, and no `apscheduler` INFO lines after the next
scheduled run.

### L5 — Polling errors: diagnose, then decide the level
`poll_commands` logs every failed `getUpdates` as ERROR. That buries real errors when
you search for `ERROR`. Counts (2026-03 → 2026-11-20): 4,401 `Read timed out (read
timeout=35)`, 63 `Connection reset by peer`, 20 `Max retries exceeded`. They're rising:
2 in March, 207 in May, 613 in June, 953 in each of September and October (about 31
a day, more than one an hour). Telegram's long poll should answer within 30 s, and the
client waits 35 s. **Diagnose first, not assumed benign:** does a timeout ever line up
with a command the owner sent that got no reply? Do they cluster by time of day? Only
then choose: log an expected read timeout below ERROR, keep anything else at ERROR.
Falsifier for "benign": a `/run` or `/filters` sent during a timeout window that was
never answered.

### L6 — Scrub the 2 old-token log lines (one-off, server) · DONE · 2026-11-20
`main.log.1` held 2 lines from 2026-05-14 with the Telegram bot token unredacted. They
predate the redaction fix and the token rotation (both 2026-06-25). The token differed
from the current one, and the journal had no copies. The token was replaced in place
with `bot<redacted>`, the same form the code uses. The lines were kept, not deleted, so
L5's counts still hold. Afterwards: 0 token matches in `main.log` and `main.log.1`, and
both line counts unchanged. Not done (owner's choice): a `getMe` check that the old token
is revoked.

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

- **`/run` with no areas configured replies "All caught up"** — the scrape is skipped,
  not run. Can't happen on the server today (areas are set); cut from the
  scrape-failure branch as a separate concern.

---

## Known risks

- **Scraper fragility** — Funda can change the payload or block the UA at any time.
  The M4 fixture tests **cannot** detect an upstream change, because the fixture is a
  frozen snapshot. They only guard against our own regressions, as the 2026-11-05
  ShallowRef outage proved. Detection is the scrape-failure alert, plus
  `main.log` (see the smoke test in [DEPLOYMENT.md](DEPLOYMENT.md)).
- **What the scrape-failure alert can't see:**
  - *A change that zeroes the match count too.* On a 0-match page Funda sends the total
    as `['EmptyRef', i]` → the string `'0'` (live page, 2026-11-20). `unwrap()` doesn't
    know `EmptyRef`, so the parser coerces any non-int total to 0. That's what keeps
    quiet days quiet (45% of runs), but it also means a shape change that broke both the
    total and the listings would still read as a quiet day. Closing it means decoding
    `EmptyRef`, then treating a non-int total as a failure; not done.
  - *A partial parse* (Funda reports 5, 3 parse) is not a failure.
  - *A dead process.* A bot that isn't running can't alert. systemd restarts it after a
    crash; a hang would go unnoticed. Closing that needs an outside dead-man's switch,
    which is a second moving part.
- **Python 3.14.3** is bleeding-edge; deps are now pinned (M5).
