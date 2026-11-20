# CLAUDE.md

Guidance for Claude Code working in this repo. Keep it short; link, don't restate.

## What this is

A personal bot that watches funda.nl for new for-sale listings and pushes matches to
Telegram (and optionally email / WhatsApp). Python, single-user, deployed on a Linux
VPS as a systemd service. Design ethos: **AK-47** — simple, robust, no overengineering
(see `.github/instructions/instruction.instructions.md`, the single home for that text).

Before adding complexity — an abstraction, a framework, a second service — ask:
*"would this break on an AK-47?"* If it needs careful maintenance to keep working,
it's probably wrong. **Equal partners**: discuss trade-offs rather than just
implementing. Raise the cost once, then proceed; don't decide silently for the user.

## Commands

```bash
venv/Scripts/python -m pytest -q     # tests (venv Python, not system)
venv/Scripts/python main.py          # run the bot locally
```

## Conventions

- **venv Python only** — system Python (also 3.14.x) lacks the deps.
- **Test before commit**; `pytest` green is the gate.
- **Branch model is 3-tier**: `feat/*`|`fix/*` → `dev` → `main`. `main` is the deploy
  trunk (**never commit directly**); `dev` is integration (**never accumulate
  speculative work there either**); cut a branch for anything multi-file or uncertain.
  Full workflow in [CONTRIBUTING.md](CONTRIBUTING.md).
- **One concern per commit.** Code, docs, deps, config — separate commits. The commit
  body says what changed *and what didn't*.
- Secrets in `.env`; live config in `config.yaml` (gitignored). Never commit either.

## How we work together

- **Don't speculate, assume, or guess.** If a claim can be checked against the live
  code, `main.log`, or the running service, check it before asserting it. Prefer facts
  from the running system over prior-session memory that hasn't been re-verified.
  *The scraper is this project's cautionary tale*: it depends on Funda's undocumented
  Nuxt payload. Until 2026-11 every failure returned an empty list, so a wrong assumption
  about payload shape was indistinguishable from a quiet day on the market — and a
  shape change that zeroes the match count too still is.
- **Follow existing conventions and patterns.** If something looks like it should
  change, raise it as a discussion before editing.
- **Read the whole file before editing it** — not just the relevant function.

## Codebase review

When the user says **"please review"**: review the codebase *and* documentation and give
feedback on how to improve it. Look for inconsistencies, errors, and things that could
be simplified. Check structure, organisation, and readability of code; check that docs
are clear, complete, and current. Give specific examples. Be thorough — skip no folder,
file, or comment. Be respectful and constructive.

(Distinct from the `/code-review` skill, which reviews a *diff* for bugs.)

## Before proposing a fix to a regression

Answer all four in plain text, in the response, first:

1. **What runtime data confirms the failure?** A `main.log` excerpt,
   `journalctl -u funda-bot`, `systemctl status funda-bot`, a live `/run`, or a saved
   copy of the page that failed to parse. *Not* "the user said it broke".
2. **What past decision or doc claim is the fix based on?** Cite the commit or doc line.
3. **Have those conditions been re-verified now?** Yes / No.
4. **What would prove this fix wrong?** State the falsifier before shipping.

**If (3) is "no" or (4) is "I don't know" — diagnose, don't fix.**

## Anti-pattern triggers — pause and verify

Treat each of these as a data-collection request, not a fix request:

- "It was working last week" / "we had a good version before"
- "The bot went quiet" — quiet is still ambiguous; check `main.log` for
  `Scrape failed:` / `Error in scrape_and_notify` (the reason follows: `bot-challenge`,
  `Nuxt payload not found`, `HTTP error`, `Parsed 0 listings but Funda reports`, …) and,
  in pre-2026-11-20 logs, `0 listings (total available: N)` with N > 0
- "Funda must have changed their site" — verify against a saved page first
- "Just change the User-Agent" / "just bump the timeout" — that's masking, not fixing
- "We tried X already and it didn't work" — re-verify under current conditions
- "The doc says X but the code does Y" — both are suspect until checked against runtime

## What NOT to do

- **Don't merge or deploy the `setup-wizard` branch as-is** — it carries a wiped
  `config.yaml`, predates the H1 no-areas fix, and needs reconciliation with H2's
  bootstrap logic. See [docs/WORKING_PLAN.md](docs/WORKING_PLAN.md).
- **Don't hammer funda.nl while testing** — repeated rapid requests trigger the
  bot-challenge page and rate-limit the VPS IP.
- Don't use system Python; don't commit `.env`, `config.yaml`, `seen_listings.db`,
  or `*.log`.

## Stale-doc audit rule

Each fact has exactly one home. When you change behaviour or status, update the doc
that owns that fact **in the same session** — never let two docs state it:

- Sprint status / backlog → [docs/WORKING_PLAN.md](docs/WORKING_PLAN.md)
- Deploy command + workflow → [CONTRIBUTING.md](CONTRIBUTING.md)
- Deploy runbook / smoke test → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- Session handoff → `docs/handoff-tns.md` (overwrite each session; delete if no carryover)

If a handoff or sprint claim contradicts `docs/WORKING_PLAN.md`, fix WORKING_PLAN.md —
don't restate it elsewhere.

**This also fires when work is marked complete** — "good job", "ship it", "looks good",
or a named milestone. Audit `docs/` for stale file paths and line references, dated
entries now superseded, "current state" claims that no longer match runtime, count
totals, and contradictions between files. Don't ask whether to do it — do it, then
summarise what changed. If deployed behaviour and a doc disagree, **both are wrong**;
fix both.
