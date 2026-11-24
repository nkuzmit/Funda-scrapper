# Handoff — 2026-11-24

Branch: `dev`, 19 commits ahead of `origin/dev` (not pushed; the owner asked to push at
the end of the decision round) · deployed: `main` @ `7aa804c` (verified on the server
2026-11-24: `funda-bot` active, 0 ERROR lines since the deploy).
Last commit: this handoff and WORKING_PLAN's date.

## Pick up here next
- **Push `dev`** once the owner closes the decision round. It holds a code change (C8),
  so a deploy follows on the owner's go: [CONTRIBUTING.md](../CONTRIBUTING.md) "Deploy",
  then the smoke test in [DEPLOYMENT.md](DEPLOYMENT.md).
- **Decision round, item 8c onward.** The remaining design-choice items are in
  [WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups", item 12. 8c (C9 lock coverage
  together with C14 repetitive handlers) is waiting on the owner: A fix C9 only
  (recommended), B fix both with a helper, C fix the doc claim only.
- **Confirm C4 and the `no url` skip live.** The 16 runs since the deploy all had
  `total available: 0`. On the first run with matches, `grep "Skipped" main.log`. The
  falsifier is in the WORKING_PLAN status snapshot (`2cd494b` entry).
