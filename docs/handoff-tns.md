# Handoff — 2026-11-24

Branch: `dev` @ `5e09a3a` before this handoff, pushed to `origin/dev` together with it ·
deployed: `main` @ `0d943df` (verified on the server 2026-11-24 over read-only ssh:
`funda-bot` active, 0 WARNING/ERROR lines in `main.log` since the 14:44 restart).
Last commit: C11 recorded as won't do (`8e18515`).

## Pick up here next
- **Continue the decision round** with the open design-choice items in
  [WORKING_PLAN.md](WORKING_PLAN.md) "Review follow-ups", item 12: C16, then C17.
  As with C10 and C11, check the code and the server logs before offering options.
- **Confirm C4 and the `no url` skip live.** No run since their deploy had matches. On
  the first one that does, run `grep "Skipped" main.log`. The falsifier is in the
  WORKING_PLAN status snapshot (`2cd494b` entry).
