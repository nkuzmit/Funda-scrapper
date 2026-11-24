# Handoff — 2026-11-24 (evening)

Branch: `dev` @ `db922d1`, 2 ahead of `origin/dev` before this handoff (docs only) ·
deployed: `main` @ `7f422d7` (verified on the server 2026-11-24 over read-only ssh:
`git log`, `funda-bot` active; live checks are in the WORKING_PLAN status snapshot).
Last commit: WORKING_PLAN records the `7f422d7` deploy and its live checks (`7f4dc97`).

## Pick up here next
- **Push `dev`** (owner's approval): the deploy record, the merge and this handoff.
  All docs; no code is waiting to deploy.
- **Choose the next item.** Review follow-ups are all done or won't-do
  ([WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups"). Per "Future Vision",
  V1 is revisited once the remaining running topics are cleared. Those are:
  - the EmptyRef blind spot ("Known risks"), the last known path where a broken
    scrape reads as a quiet day. Recommended first. Diagnose before fixing: capture
    one live 0-match page (a single request) as a fixture.
  - slow command replies ("Open issues"). Inbound lag was 0–3 s on all 11 samples
    (main.log grep, 2026-11-24), so any delay is on the reply side, which fits the
    IPv6 lead.
- Passive: C4 / `no url` await a run with matches, and C16 awaits a reboot. Both
  falsifiers are in the status snapshot.

## Open question
- For the owner: process weight. On 2026-11-24 there were 31 commits, 12 of them
  merges, and the handoff was rewritten about 5 times. Decided 2026-11-24: the
  handoff is committed directly on `dev` (`.claude/commands/handoff.md`). Still
  open: write it once per session, commit other single-file docs changes straight
  to `dev` too, and keep one line per deploy in the status snapshot, with the detail
  in the item. That would need a CONTRIBUTING / CLAUDE.md change if agreed.
