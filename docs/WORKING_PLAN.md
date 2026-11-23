# Working Plan

Living development plan for the Funda Scraper Bot, and the source of truth for
sprint status and backlog priority. Update this file in the same session you
change behaviour or status (see the stale-doc audit rule in [CLAUDE.md](../CLAUDE.md)).

Last updated: 2026-11-23

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
- **Deployed (2026-11-20, last at 17:23, `6e93afb`):** Sprint 4, log hygiene. APScheduler
  is quiet, polling network errors log as WARNING, and each command logs how late it
  arrived. 79/79 tests. Details and live confirmation are in the Sprint 4 section below.
- **Deployed (2026-11-23 13:54, `0ba6c32`):** review actions 1–3. 88/88 tests.
  - *Polling error replies* (`5d3d001`): when Telegram answers `getUpdates` with
    `ok: false` (e.g. 401 revoked token, 409 second poller), polling logs ERROR
    `Polling error: Telegram replied <code>: <description>` and pauses 30 s. Before, it
    re-polled instantly with no log line (offline simulation: 1,000 polls in 2 ms).
  - *Send check* (`9ead3f2`): command replies, the no-areas prompt and the scrape-failure
    alert log ERROR `Failed to send Telegram message: … | response: …` (token redacted)
    when Telegram rejects the message. Before, nothing was logged (live fake-token call:
    401, no log line). No retry, by owner's choice.
  - *Config robustness*: `config.yaml` is saved via a temp file + `fsync` + rename, so a
    failed write keeps the old file (`dba6583`; a leftover `config.yaml.tmp` is left
    visible on purpose: it means a save failed). A schedule time like `'25:00'` is skipped
    with a WARNING instead of crashing startup (`da4e1ee`). An empty `channels:` or
    `notifications:` means no channels instead of a `TypeError` (`15ea741`).
  - **Confirmed live** 2026-11-23: startup scrape `0 listings (total available: 0)`,
    `Scheduler started: 14 runs a day`, polling started. Owner sent `/filters` and
    `/setdate 3` (same value): both answered, both logged as received 1 s after sending.
    `config.yaml` was rewritten at the moment of `/setdate` (13:55:19) with an identical
    checksum and no `.tmp` left behind. 0 ERROR lines since the restart.
- **Deployed (2026-11-23 14:11, `2cd494b`):** review action 4 (C4, `58b4310`). The parser
  logs listings it drops as one WARNING per page: `Skipped K of L listings while parsing:
  <reason> (n), …`. Before, they were dropped silently or at DEBUG. A partial parse is
  still not a failure. 91/91 tests. Startup scrape: `0 listings (total available: 0)`,
  0 WARNING/ERROR lines. **Not yet confirmed live:** a run where Funda reports matches.
  If the WARNING shows on a page where N equals M, Funda's list holds non-listing entries
  and the WARNING is noise (the falsifier).
  Server logs 2026-03-19 → 2026-11-23 (3,562 page lines): N < M only on the 172 ShallowRef
  outage runs (N = 0). A partial parse never happened.
- **Deployed (2026-11-23 14:46, `7aa804c`):** review follow-ups 6, 7, 11 and hygiene
  batch 1. In production terms:
  - A listing without a URL is a parser skip, and a renamed URL field fails the scrape
    instead of reading as a quiet day.
  - WhatsApp credentials are redacted from logs.
  - The bot-challenge check is one clause instead of two (same pages match).
  - The pins equal the server's packages.

  116/116 tests on 3.14.3, and on 3.12.3 with the server's packages. This was the first
  deploy with `pip install` in the command: a `pip freeze` diff before and after was
  empty. **Confirmed live** 2026-11-23:
  - The startup scrape and an owner `/run` (14:47) both returned `0 listings (total
    available: 0)`. `/run` was received 0 s after sending and answered `All caught up`.
  - 0 WARNING/ERROR lines in `main.log`, and 0 errors in the systemd journal.

  **Not yet confirmed live:** a run with matches. The C4 falsifier above applies to the
  new `no url` reason too.

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

## Sprint 4 — Log hygiene · DONE · 2026-11-22

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

### L4 — Quiet APScheduler · DEPLOYED · 2026-11-20 16:45 (`77ac550`)
The `apscheduler` logger is set to WARNING in `main.py`. In APScheduler 3.10.4 and 3.11.2
(production; both checked 2026-11-23) a missed run and a skipped overlapping run log at
WARNING, and a job that raised logs at ERROR, so they still get through. The startup "Added job" lines are replaced by one line from
`funda_bot.scheduler`: `Scheduler started: N runs a day (Europe/Amsterdam) at …`.
Expect about 29% less volume. 74/74 tests. **Confirmed live** 2026-11-20: at startup
(16:45) the line read `Scheduler started: 14 runs a day … at 07:00 … 20:00`, matching
`schedule.hours`. The 17:00 scheduled run logged 3 lines (fetch, page count, found)
instead of 5, with 0 `apscheduler` INFO lines and 0 `apscheduler` warnings or errors.

### L5 — Polling errors · DEPLOYED · 2026-11-20 17:23 (`6e93afb`)

**Confirmed live** 2026-11-22 06:38, about 37 h after deploy: 43 polling errors, all
WARNING `Polling error (network, retrying)` (about 28 a day, as diagnosed), 0 polling
ERRORs, and 0 ERROR lines of any kind. The same deploy shipped the command-latency line
(see Open issues); first samples: `/filters` 3 s, `/run` 0 s.

**Diagnosis (2026-11-20):** the errors run at 25–38 a day, spread evenly over all
24 hours (157–218 per hour of day, nights included), so they aren't tied to scrapes or
load. They're isolated: 1 of 599 November errors came within 10 s of the previous one.
That's about 1% of polls. Commands aren't lost: `offset` isn't advanced on an error, so
Telegram re-delivers on the next poll, at most about 40 s late. Runtime trace: an error
at 2026-06-25 16:38:27 was followed by a `/run` scrape 6 s later. The owner reports no
command ever went unanswered. Not known: whether Telegram answers late (after 35 s) or
the connection stalls; testing that (option B) was judged not worth two deploys.
**Decision: option A.** `requests.Timeout` / `requests.ConnectionError` now log as
WARNING `Polling error (network, retrying): …`. Anything else, including a crash in a
command handler, stays ERROR `Polling error: …`. 77/77 tests.

Original plan, kept for the record:
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

## Review follow-ups · IN PROGRESS · 2026-11-23

From the 2026-11-23 compliance review, measured against the AK-47 ethos (report, private
to the owner: https://claude.ai/artifact/4HTNMUmwfhGUPH4eyDfP4h; IDs below are its
finding numbers). Worked one action at a time. Order agreed with the owner 2026-11-23.

1–3. **Done, deployed** — polling error replies (C1), send check (C2), config robustness
   (C3, C12, C13). See the status snapshot (`0ba6c32`).
4. **Done, deployed** — log listings the parser skips (C4). See the status snapshot
   (`2cd494b`). Live confirmation pending: the first run where Funda reports matches.
5. **V1 — record the product direction** (owner's call, no code): CLAUDE.md says
   single-user, Future Vision below says multi-user, and the 2026-08 "pivot" isn't
   written down. If multi-user, C5, C7, C3/C12 and C11 move up.
6. **A listing without a URL is dropped silently** (found during C4). `scrape_funda`'s
   duplicate check skips it with no log line, after it has already been counted in
   `Page N: X listings`. **Done, deployed** (`25acd5e`, in `7aa804c`). It's now a parser
   skip (`no url`) in the C4 WARNING. If *every* listing lacks a URL while Funda
   reports matches (a renamed field), the scrape raises `ScrapeError` and alerts.
   Before, that read as a quiet day.
7. **C6 — test on Python 3.12**, which production runs. **Done, deployed** in `7aa804c`
   (tests, pins and docs only; the server's packages didn't change). The suite
   on 3.12.3 found one test that only worked on 3.13+ (`635972f`). The server's packages
   predated the M5 pins: APScheduler 3.11.2 and PyYAML 6.0.3 since 2026-03-19, never the
   pinned 3.10.4 and 6.0.1. The pins now match production (`e71a97f`). **Open (owner's
   choice):** how routine tests run on 3.12. See Known risks.
8. **C7 — test gaps**: a foreign chat id, token redaction, the six list commands,
   the `config.yaml` bootstrap. **Done 2026-11-23** (`58ec7b2`, tests only, in `main`):
   21 tests, 114 in total. Each was checked against a deliberate break in the code it
   covers.
9. **D1–D5 — operator docs**: README on empty areas, venv commands and hand edits to
   `config.yaml`; DEPLOYMENT clone path; CONTRIBUTING deploy without `pip install`.
   **Done 2026-11-23** (`839f94f`, `f42d7e9`, `b3bafbd`). The deploy command
   now runs `pip install`. It was first used for `7aa804c` and changed nothing, as
   expected.
10. **D8, D9 — rules outside the repo**: move binding ported rules into CONTRIBUTING;
    retire the old memory folder; the local `setup-wizard` branch's `PLAN.md` holds
    the server IP. **D9 done 2026-11-23:** CLAUDE.md's warning now says never to push
    `setup-wizard`, and why. **D8 is the owner's call** (which rules bind; retiring a
    memory folder on the owner's machine). The rules that exist only in assistant memory
    are: no magic-value sentinel returns; re-read the diff line by line; a theory isn't
    confirmed because the fix worked; amend plan and memory when a change is reverted;
    don't trust past commits or plan entries without re-checking.
11. **C5 — redact WhatsApp credentials from logs.** **Done, deployed** (`eff2cc6`,
    in `7aa804c`). Done ahead of V1 because it was small and logging-only.
    The CallMeBot `apikey` and `phone` are now redacted like the Telegram token. It was
    latent: the server's channels are `[telegram]` and no key is set.
12. **Hygiene**: C8–C20, D10–D16 as they come up.
    - **Done 2026-11-23, deployed in `7aa804c`:**
      - D10, D11: docstrings (`b83a091`).
      - C15: one bot-challenge check instead of two (`24312e2`; no behaviour change).
      - C18: pytest pinned (`dfabf68`).
      - D16: README (`e2d1aea`).
      - C19, local part: the 27 local branches merged into `dev` are deleted.
    - **Still open, the owner's call:**
      - C19 leftovers: `origin/fix/h2-apply`, `origin/fix/m3-thread-safety`, and
        `/root/funda-config.bak` on the server.
      - C20: the local `test_run.py` makes a real Funda request.
      - D15: the ethos file's bot-challenge line ("no intervention needed") predates
        the alert.
    - **Still open, need a design choice:**
      - C8 / D13: duplicated helpers and facts.
      - C9 / D12: lock coverage.
      - C10: unenforced input limits.
      - C11: `/run` and a scheduled run can overlap.
      - C14: repetitive add/remove handlers.
      - C16: `network-online.target`.
      - C17: HTML email escaping.
      - D14: `docs/*` branches aren't in the stated branch model.

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

- **Commands sometimes feel slow to answer** — the owner reports it happening often,
  e.g. 2026-11-20 15:19–15:20. Telegram shows only minutes, so the chat can't time it.
  The polling errors (L5) don't explain the 15:19 case, since none were logged
  15:14–15:22. A known contributor: `/run` blocks the polling loop while it scrapes and
  delivers (15:20:25 → 15:20:42+ that day, including about 9 s of photo retries), so
  commands sent meanwhile wait.
  **Measuring it:** each command logs `Command /x received Ns after sending` (deployed
  with L5, 2026-11-20 17:23). Run `grep "received" main.log` and compare slow ones with
  nearby `Polling error` warnings and `/run` scrapes. Samples so far: 3, all 0–3 s.
  **Lead (2026-11-23, not acted on — owner's choice):** the delay can also be on the
  reply side. A `/run` at 10:43 arrived in 1 s, but the bot took 10.15 s to send
  "Running scrape..." (received 10:43:02.001 → scrape started 10:43:12.155, no send
  error). That matches `_send`'s 10 s timeout. From the server, 30 connections to
  `api.telegram.org` per route: IPv4 0 failed (max 0.07 s), IPv6 4 hung (6 s cap).
  Python tries IPv6 first, and urllib3 silently falls back to the next address after
  a timeout: 10 s for a send, up to 35 s for a poll. Possible fixes: force IPv4 in
  `main.py`, prefer IPv4 in the server's `/etc/gai.conf`, or a shorter connect timeout.
  Falsifier: after forcing IPv4, slow `received` lines continue or the ~28/day
  `Polling error (network)` warnings don't drop.

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
  - *A partial parse* (Funda reports 5, 3 parse) is not a failure. Since 2026-11-23 it
    logs a `Skipped … listings while parsing` WARNING, but it doesn't alert.
  - *A dead process.* A bot that isn't running can't alert. systemd restarts it after a
    crash; a hang would go unnoticed. Closing that needs an outside dead-man's switch,
    which is a second moving part.
- **The test gate runs on a different Python than production.** Production runs 3.12.3
  and the local `venv` runs 3.14.3. A one-off check (2026-11-23) passed on 3.10.11,
  3.12.3 (with the server's exact packages) and 3.14.3. It found one test that only
  worked on 3.13+. Routine `pytest` still runs on 3.14 only.
