# Handoff — 2026-11-23

Branch: `dev`, pushed to `origin/dev` · deployed: `main` @ `7aa804c` (verified on the
server 2026-11-23 14:46; smoke test passed, including an owner `/run`). `dev` is ahead
by docs only, no deploy needed.
Last commit: WORKING_PLAN and this handoff record the `7aa804c` deploy.

## Pick up here next
- **Owner decisions, one at a time.** The deploy was decision 1 of 8 and is done.
  The rest are in [WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups":
  - item 7: how routine tests run on Python 3.12 (next)
  - item 5: V1, the product direction
  - item 10: D8, which memory-only rules bind
  - item 12: the C19 leftovers, C20, D15, then the items needing a design choice
- **Confirm C4 and the `no url` skip live.** On the first run where Funda reports
  matches, run `grep "Skipped" main.log`. The falsifier is in the WORKING_PLAN status
  snapshot (`2cd494b` entry).
