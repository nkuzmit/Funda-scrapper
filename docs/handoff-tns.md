# Handoff — 2026-11-24

Branch: `dev` @ `585bb82` before this handoff, 27 commits ahead of `origin/dev` (not
pushed) · deployed: `main` @ `7aa804c` (verified on the server 2026-11-24 over read-only
ssh: `funda-bot` active, 0 ERROR lines in `main.log` since the deploy).
Last commit: C9, list adds insert a missing key under the config lock (`124ad94`).

## Pick up here next
- **Start the session with the deploy** (the owner's plan, 2026-11-24). `dev` holds two
  code changes, C8 and C9, plus docs. Confirm with the owner before each outward
  step:
  1. Push `dev`.
  2. Merge `dev` → `main` and push.
  3. Deploy and run the smoke test: [CONTRIBUTING.md](../CONTRIBUTING.md) "Deploy",
     then [DEPLOYMENT.md](DEPLOYMENT.md) "Smoke test".
  4. Record the deploy in the WORKING_PLAN status snapshot, with the live evidence.

  Neither change alters behaviour that can be seen. C8's falsifier: a `/set…` change
  is lost after a restart. C9's falsifier: a list add fails or replies wrongly.
- **Continue the decision round** with the open design-choice items in
  [WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups", item 12: C10 (waiting on the
  owner, see below), then C11, C16, C17.
- **Confirm C4 and the `no url` skip live.** None of the runs since the deploy had
  matches. On the first one that does, run `grep "Skipped" main.log`. The falsifier is
  in the WORKING_PLAN status snapshot (`2cd494b` entry).

## Open question
- **C10, unchecked inputs: A, B or C?** The owner decides. The analysis and the options
  are under C10 in WORKING_PLAN "Review follow-ups", item 12.
