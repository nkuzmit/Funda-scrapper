# Handoff — 2026-11-24

Branch: `dev` @ `585bb82` before this handoff, 27 commits ahead of `origin/dev` (not
pushed) · deployed: `main` @ `7aa804c` (verified on the server 2026-11-24 over read-only
ssh: `funda-bot` active, 0 ERROR lines in `main.log` since the deploy).
Last commit: C9, list adds insert a missing key under the config lock (`124ad94`).

## Pick up here next
- **Push `dev`, then deploy, on the owner's go.** The owner asked to push at the end of
  the decision round. `dev` holds two code changes, C8 and C9, so a deploy follows:
  [CONTRIBUTING.md](../CONTRIBUTING.md) "Deploy", then the smoke test in
  [DEPLOYMENT.md](DEPLOYMENT.md).
- **Continue the decision round** with the open design-choice items in
  [WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups", item 12: C10 (waiting on the
  owner, see below), then C11, C16, C17.
- **Confirm C4 and the `no url` skip live.** None of the runs since the deploy had
  matches. On the first one that does, run `grep "Skipped" main.log`. The falsifier is
  in the WORKING_PLAN status snapshot (`2cd494b` entry).

## Open question
- **C10, unchecked inputs: A, B or C?** The owner decides. The analysis and the options
  are under C10 in WORKING_PLAN "Review follow-ups", item 12.
