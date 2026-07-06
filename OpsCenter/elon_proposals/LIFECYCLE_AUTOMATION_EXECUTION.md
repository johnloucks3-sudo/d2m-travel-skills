# LIFECYCLE AUTOMATION — EXECUTION REPORT
**Date:** 2026-07-06
**Script:** `scripts/client_lifecycle_automation.py`
**Closes:** `docs/roadmap_status.md` § 6 "CLIENT LIFECYCLE AUTOMATION (NOT STARTED)" — the 10-touchpoint T-minus list under "Why This Matters" (lines 90-99).

## What was built
A standalone T-minus timeline engine implementing the 10 canonical touchpoints:

| ID | Touchpoint | Anchor | Offset | Owners | Critical |
|----|-----------|--------|--------|--------|----------|
| L1 | Anchor Date verification | embark | T-270 | COS | — |
| L2 | Insurance waiver | embark | T-270 | A9→A3 | 🔴 |
| L3 | Air routing audit | embark | T-150 | A2→A9 | 🔴 |
| L4 | Specialty dining | embark | T-120 | A2→A6→A3 | — |
| L5 | Final payment | FPD (or embark-90 estimate) | T-90 | A9→A3 | 🔴 |
| L6 | Itinerary generation | embark | T-21 | A2→A6→A3 | — |
| L7 | Embark calendar event | embark | T-0 | COS | — |
| L8 | Satisfaction check-in | disembark | T+1 | A3 | — |
| L9 | Welcome home | disembark | T+10 | A6→A3 | — |
| L10 | Future cruise offer | disembark | T+10 | A2→A6→A3 | — |

**Financial Hard-Source Rule applied:** L5 (Final payment) uses the dossier/portal-sourced FPD when supplied; only falls back to the generic embark-90d estimate when no real FPD is on file, and flags that entry `[ESTIMATED]` so it's never mistaken for a verified date.

**Scheduler wiring (per `docs/STAFF_TASKING_TIMER_SCHEMA.md`):**
- Appends task entries to `OpsCenter/staff_tasking_schedule.json` (same schema as the existing 35-TP `staff_tasking_timers_system.py`, namespaced `phase: "L"` / `touchpoint: L1..L10` so it never collides with the existing 0.x-5.x IDs).
- Posts task cards to `claude_inbox.md` for COS/A3/A6/A9-owned chains, and to `OpsCenter/collaboration/opencode_inbox.md` for A2-owned chains (first owner in the chain determines routing).
- Idempotent: `OpsCenter/lifecycle_automation_dedup.json` keys on `LIFECYCLE-{touchpoint}-{client}` so re-running never double-queues a task.

## Test — mock booking verification
Mock: `kuklinski_group_MOCK`, booking 2026-06-01, embark 2026-12-17, FPD 2026-08-15 (disembark defaulted to embark+7 = 2026-12-24).

```
2026-03-22  L1   Anchor Date verification     owners=COS
2026-03-22  L2   Insurance waiver             owners=A9→A3      🔴
2026-07-20  L3   Air routing audit            owners=A2→A9      🔴
2026-08-15  L5   Final payment                owners=A9→A3      🔴
2026-08-19  L4   Specialty dining             owners=A2→A6→A3
2026-11-26  L6   Itinerary generation         owners=A2→A6→A3
2026-12-17  L7   Embark calendar event        owners=COS
2026-12-25  L8   Satisfaction check-in        owners=A3
2027-01-03  L9   Welcome home                 owners=A6→A3
2027-01-03  L10  Future cruise offer          owners=A2→A6→A3
```

Verified independently: 2026-12-17 − 270d = 2026-03-22 ✓ · −150d = 2026-07-20 ✓ · −120d = 2026-08-19 ✓ · −21d = 2026-11-26 ✓ · disembark 2026-12-24 +1d = 2026-12-25 ✓ · +10d = 2027-01-03 ✓. L5 correctly took the supplied FPD (2026-08-15) rather than the embark-90 estimate (2026-09-18).

**Staging test:** ran `--test --stage` — all 10 tasks written to `staff_tasking_schedule.json` (total_tasks 2→12, critical_count 3) and inbox cards posted to `claude_inbox.md` (7 cards: L1,L2,L4,L5,L6,L7,L8,L9,L10 — all non-A2-first chains) and `opencode_inbox.md` (1 card: L3, A2-first). Re-run confirmed dedup: 0 staged, 10 skipped as already-queued, `total_tasks` unchanged at 12.

**Cleanup:** mock `kuklinski_group_MOCK` entries were stripped from `staff_tasking_schedule.json`, `lifecycle_automation_dedup.json`, `claude_inbox.md`, and `opencode_inbox.md` after the test — the two pre-existing real tasks (`TASK-1.4-kuklinski_group`, `TASK-1.4-westbrook_group`) were confirmed intact throughout.

## Usage
```bash
# Preview only
python3 scripts/client_lifecycle_automation.py --client <slug> --embark-date YYYY-MM-DD [--fpd YYYY-MM-DD] [--booking-date YYYY-MM-DD] [--disembark-date YYYY-MM-DD]

# Preview + stage into scheduler/inboxes
python3 scripts/client_lifecycle_automation.py --client <slug> --embark-date YYYY-MM-DD --fpd YYYY-MM-DD --stage

# Built-in mock test
python3 scripts/client_lifecycle_automation.py --test [--stage]
```

## Not yet wired (next steps, not in this task's scope)
- No systemd timer/cron entry created yet — this is a callable engine, not a daemon. Recommend a daily `ci_probe`-style wrapper (mirroring `scripts/ci_probe_lifecycle_tp.py`) that iterates active dossiers, pulls their anchor dates, and calls `compute_timeline()` + `stage_to_scheduler()` per client.
- Dossier-to-CLI bridge: this run took anchors as flags; a real daily run needs a small adapter reading `booking_date`/`embark_date`/`fpd`/`disembark_date` out of each client dossier (YAML frontmatter, same fields `thunderbird_tp_scheduler.py` already reads).
