# Funda Bot — Master Plan

## Progress

```
Phase 1: Easy wins ........... ✅ shipped (main)
Phase 2: Deploy to Hetzner ... ✅ shipped (main)
Phase 3: Telegram commands ... ✅ shipped (main)
Phase 4: Setup wizard ........ 🚧 on setup-wizard branch (unmerged)
Phase 5: Post-audit backlog .. ⏳ in progress (one branch per fix)
```

---

## Phases 1–3 ✅ (live on main)

- Startup scrape, systemd deployment, README deploy section
- Telegram command interface (`BackgroundScheduler` frees the main thread for the polling loop)
- Live filter editing via commands, written back to `config.yaml`

Deploy (run on the Hetzner server):

```bash
git pull origin main && systemctl restart funda-bot
systemctl status funda-bot      # is it running?
journalctl -u funda-bot -f      # live system logs
tail -f main.log                # app logs
```

---

## Phase 4: Setup wizard 🚧 (branch: `setup-wizard`, not merged)

Guided 6-step first-run config (areas → price → bedrooms → labels → days → keywords),
triggered when `filters.areas` is empty or via `/setup`.

> ⚠️ The branch also carries an emptied `config.yaml` (reset for testing). **Do not deploy
> it as-is.** Merge only after the empty-config is restored; the no-areas startup flood it
> exposed is already fixed on main (H1 below).

---

## Phase 5: Diagnostic backlog (2026-06-25 audit)

Worked one branch per item, branched off `main`.

**Done & shipped to main:**
- ✅ Photos restored — Funda moved listing media to the `tiara-media` backend
- ✅ Telegram token redacted from logs *(rotate the old token via @BotFather — it was exposed)*
- ✅ Skip scrape when no areas configured (no more all-NL flood / seen-DB poisoning)

**Open (priority order):**
- [ ] **H2 — config split** *(NEXT)*: `config.yaml` is git-tracked **and** runtime-written, so `git pull` deploys conflict once a filter is changed via Telegram. Split a tracked default from a gitignored runtime config.
- [ ] **M1 — input validation**: `int()` in commands/wizard crashes silently on bad input; reply with a usage error instead.
- [ ] **M2 — `/setlabel` case**: stores raw-case args while the wizard upper-cases → silent no-match. Normalise case.
- [ ] **M3 — thread safety**: shared `config` dict mutated across the poll thread + scheduler thread with no lock.
- [ ] **M4 — scraper resilience**: tied to Funda's Nuxt payload + `facebookexternalhit` UA; add payload-fixture tests so structure changes fail a test instead of silently returning nothing.
- [ ] **M5 — pin deps**: `requirements.txt` is unpinned (running on Python 3.14.3).
- [ ] **L1 — dead dirs**: delete empty `src/controllers`, `src/routes`, `src/services`.
- [ ] **L2 — energy label**: `.get('energy_label', 'N/A')` returns `"None"` when the key is present-but-None.
- [ ] **L3 — scheduler**: `schedule_scrapes` swallows a failed `.start()`; surface it instead.

---

## Long-term ideas

- **"Request viewing" CTA** — inline Telegram button to contact the listing agent (investigate whether Funda exposes a contact endpoint first).
- **Multi-user** — currently single-user by design; lightest path is one bot instance per person. Full multi-tenant is out of scope.
