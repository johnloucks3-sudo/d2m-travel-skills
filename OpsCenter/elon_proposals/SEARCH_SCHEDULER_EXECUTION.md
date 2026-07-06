# SEARCH SCHEDULER EXECUTION — Phase 1 Build Report
## Autonomous Search Capability Plan — Lifecycle-TP Scheduler Backbone
### Dreams2Memories Travel, LLC · Thunderbird Wing · 2026-07-06

---

## WHAT THIS IS — AND ISN'T

**This is NOT a second flight-search engine.** `scripts/daily_airfare_scan.py` (03:00 MT,
cron) + `scripts/fare_watch_amadeus.py` / `fare_watch_centrav.py` already run continuous
route-based fare-watching against `core/travel/data/fare_watches.json` — that system is
unchanged and untouched.

**This IS** the missing piece the plan (`docs/AUTONOMOUS_SEARCH_CAPABILITY_PLAN.md`,
Phase 1, lines 61-73) identified: a scheduler that fires a search tied to a specific
**client lifecycle touchpoint (TP) due date** — e.g. "Air Fare Watch Delivery due Jun 17"
→ fire Jun 3 (14-day lead) — rather than a fixed daily route check. It **reuses** the
existing Amadeus search function (`fare_watch_amadeus._search_flights`) rather than
reimplementing search, per the plan's own instruction not to build a second search
engine.

| | Existing (unchanged) | New (this build) |
|---|---|---|
| Trigger | Every day, 03:00 MT | N days before a specific TP due date, 06:00 MT |
| Scope | All routes in fare_watches.json | Per-client TP config in lifecycle_search_config.json |
| Purpose | Continuous price trendline / alert | One-shot delivery-prep search ahead of a client touchpoint |
| Search engine | Amadeus / Centrav | Same Amadeus function, imported directly |

---

## BUILT (all files new, none pre-existing)

| File | Purpose |
|---|---|
| `scripts/lifecycle_search_scheduler.py` | Scheduler backbone — loads config, computes trigger dates, fires flight search, writes queue + review log |
| `config/lifecycle_search_config.json` | Per-client TP search config. Seeded with real Kuklinski data from `docs/KUKLINSKI_LIFECYCLE_SCHEDULE.md` (not illustrative) |
| `search_queue/` | Output directory — raw+enriched-ready result per `{client}_{date}_{type}.json` |
| `hale_review_queue.md` | Append-mode log Hale reads; one row per fired search, status DONE/FLAGGED/FAIL |
| `deploy/lifecycle-search-scheduler.service` | systemd oneshot unit, `.venv/bin/python`, `User=john` |
| `deploy/lifecycle-search-scheduler.timer` | Fires daily at 06:00:00 MT (server local TZ confirmed `America/Denver`) |

**Config seed (real, not synthetic):**
- Kuklinski TP 1.5 "Air: Fare Watch Delivery" — due 2026-06-17, trigger 2026-06-03, routes RIC→PTY / RSW→FLL / MHT→FLL
- Kuklinski TP 2.3 "Air Booking Decision" — due 2026-07-17, trigger 2026-07-03, same routes

Phase 1 scope is **flights only** (per plan) — the scheduler skips any config entry
with `"type" != "flights"` even if `search_trigger: true`.

---

## T-10 ACCEPTANCE TEST — RESULTS

**Test method:** manual invocation with `--date` simulating each real trigger date
(today's actual date is 2026-07-06; both Kuklinski trigger dates are in the past, so
this validates trigger-matching logic, not unattended firing — see caveat below).

| Run | Date | Expected | Actual |
|---|---|---|---|
| 1 | `--date 2026-06-01` | no fire (not a trigger date) | ✅ `"fired": []` |
| 2 | `--date 2026-06-03` | fire TP 1.5 | ✅ Fired. Live Amadeus call succeeded (RIC-PTY $794.75pp, RSW-FLL $395.83pp, MHT-FLL $338.16pp, UA, 10 offers each). Queue file + review-log row written. |
| 3 | `--date 2026-07-03` | fire TP 2.3 | ✅ Fired. Queue file + review-log row written. |
| 4 (failure path) | `--date 2026-06-03` with `AMADEUS_CLIENT_SECRET` overridden to an invalid value | queue entry written with FAIL status, not a crash | ✅ `status: FAIL`, review-log row includes the actual error string (`401 Client Error: Unauthorized...`). Confirms the plan's observability requirement — a search that fails still produces a reviewable artifact, not a silent gap. |

**PASS criteria met**, verified by artifact inspection, not just clean exit:
- `search_queue/kuklinski_2026-06-03_flights.json` — real Amadeus offer data present
- `hale_review_queue.md` — rows present with timestamp, client, TP, status, file path

**Honest caveat on T-10:** the acceptance test as written ("scheduler fires without
prompting") requires the **unattended timer**, not a manual `--date` run. What's
verified today is the **trigger-matching and search-execution logic** end-to-end,
including the failure path. Unattended firing depends on the systemd timer being
installed — see below, not yet done (no passwordless sudo in this session).

---

## SYSTEMD INSTALL — STAGED, NOT INSTALLED

`sudo -n true` failed (`sudo: a password is required`) — no passwordless sudo available
in this session. Per the existing convention (`deploy/hale-daily-scan.timer` etc. are
also currently `disabled` in this environment), the unit files are staged in `deploy/`
and require a one-time manual install:

```bash
sudo cp deploy/lifecycle-search-scheduler.service deploy/lifecycle-search-scheduler.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lifecycle-search-scheduler.timer
```

This is a reversible action (standard systemd timer, same pattern as 5 other timers
already in `deploy/`) — flagging for Commander/Sterling to run once, not a gate.

---

## WHAT'S NOT BUILT (explicitly out of Phase 1 scope, per the plan)

- **Phase 2 — format/enrichment layer** (`search_formatter.py`, McLeod-standard fields:
  name/link/reviews/price-tiers). The raw Amadeus result already carries price, cabin,
  carrier, offer count — but not a booking link or review score. Not built this pass.
- **Phase 3 — morning brief integration** (surfacing `hale_review_queue.md` rows into
  `hale_brief.md`). The queue file exists and is append-only readable; wiring it into
  the brief generator is a follow-on.
- **Hotel / tour / dining searches** — plan explicitly scopes Phase 1 to flights only;
  hotel credentials (Hotelbeds) remain the Phase 4 gap, unchanged by this build.
- **Dedup guard for same-day reruns** — if the timer or a manual run fires twice on the
  same trigger date, the queue JSON is overwritten (deterministic filename, safe) but
  `hale_review_queue.md` gets a second row. Acceptable for a once-daily timer; worth a
  guard if Phase 3 adds more frequent runs.

---

## RECOMMENDATION

Ready for Phase 2 (format/enrichment) once Commander/Sterling confirms the timer
install command above. Phase 4 (Hotelbeds credentials) can proceed in parallel per the
plan — it does not block on this build.

---
*Filed by Claude Code (TALON) · Thunderbird Wing · 2026-07-06*
