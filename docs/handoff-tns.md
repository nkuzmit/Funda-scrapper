# Handoff — 2026-11-23

Branch: `dev`, pushed to `origin/dev` · deployed: `main` @ `2cd494b` (verified on the
server 2026-11-23). `dev` is ahead **with code**: review follow-ups 6, 7, 11 and the
hygiene batch in item 12 (scraper, notifier, `requirements.txt`). Nothing changed in
`main.py`.
Last commit: this handoff, after hygiene batch 1 was recorded in WORKING_PLAN.

## Pick up here next
- **Deploy `dev` → `main`: needs the owner's approval.** Workflow and command:
  [CONTRIBUTING.md](../CONTRIBUTING.md). This is the first deploy with the new
  `pip install` step. It should change nothing, because the pins now equal the
  server's packages. After the deploy, run the smoke test in
  [DEPLOYMENT.md](DEPLOYMENT.md).
- **Confirm C4 and item 6 live.** On the first run where Funda reports matches,
  run `grep "Skipped" main.log`. The falsifier is in the
  [WORKING_PLAN.md](WORKING_PLAN.md) status snapshot (`2cd494b` entry).

## Open question
- The owner's decisions, all in [WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups":
  - item 5 (V1, product direction)
  - item 7 (how routine tests run on Python 3.12)
  - item 10 (D8, which memory-only rules bind)
  - item 12 (the C19 leftovers, C20, D15)
