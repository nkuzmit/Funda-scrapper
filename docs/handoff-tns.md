# Handoff — 2026-11-23

Branch: `dev` @ `eb1016c` plus this handoff commit, 2 ahead of `origin/dev` before it
(docs only) · deployed: `main` @ `2cd494b` (verified on the server 2026-11-23; `dev`
is ahead by docs only, no deploy needed)
Last commit: WORKING_PLAN records review action 4 (C4) as deployed (`eb1016c`).

## Pick up here next
- **Confirm C4 live.** It's deployed, but no run with matches has happened since. On
  the first run where Funda reports matches, check `grep "Skipped" main.log`. The
  falsifier is written in the [WORKING_PLAN.md](WORKING_PLAN.md) status snapshot
  (`2cd494b` entry).
- **Then V1**: the next item in [WORKING_PLAN.md](WORKING_PLAN.md), "Review
  follow-ups". It's the owner's call (product direction), not a code change.

## Open question
- Add the two new ERROR signatures (`Telegram replied`, `Failed to send Telegram
  message`) to [DEPLOYMENT.md](DEPLOYMENT.md) smoke-test step 2? Proposed, not
  answered (owner).
- 26 local branches are merged into `dev` and not deleted, including this session's
  `fix/log-parse-skips` and `docs/c4-status`. Delete them? That's review C19, under
  "Hygiene" in WORKING_PLAN (owner).
