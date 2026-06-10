# Lifecycle & Scan Subsystems — Consolidated Validation
## Independent audit (3 parallel agents) · Opus 4.8 · 2026-06-09

**Overall verdict: NOT UP TO STANDARDS across all three subsystems.**
The mandate is SCHEDULE → CONDUCT → DOCUMENT → CAPTURE. In the actually-running
code, lifecycle stops at SCHEDULE (and silently emits zero), air CONDUCTs but is
blind 12–26 days, and hotel/excursion never CONDUCT at all while emailing clients
that they will. The same four root causes recur in every subsystem — they are
architectural, not isolated bugs.

---

## SUBSYSTEM GRADES

| Subsystem | Verdict | Last actually worked |
|-----------|---------|----------------------|
| Lifecycle TP scheduler | NOT UP TO STANDARDS | 0 drafts created Jun 7/8/9 (silent) |
| Air / fare scan + alerts | NOT UP TO STANDARDS | 0/21 checked today; last price 2026-05-28 (~12–26d blind) |
| Hotel scans | NOT UP TO STANDARDS | never automated (dead Hotelbeds creds, no scheduler call) |
| Excursion scans | NOT UP TO STANDARDS | never — stub on every call; email promises research not done |
| Historical capture (all) | NOT UP TO STANDARDS | only flight fare-history has read-back; starved (25 rows) |

---

## FOUR CROSS-CUTTING ROOT CAUSES (fix once, not piecemeal)

### RC1 — Silent-zero failure (the incubator incident, recurring ×3, live now)
Every subsystem reports SUCCESS while doing nothing; no dead-man's-switch anywhere.
- Lifecycle: `lifecycle_scheduler.py` logs `drafts_created: 0`, exit 0, no alert. Telegram fires only on `errors`; "produced nothing" is never an error.
- Air: `fare_watch_centrav.py:120` pages only `if alerts`. Today 0/21 checked (Centrav auth dead), systemd green, zero pages. `thunderbird_centrav_search.py:671` `break`s on first auth fail → understates blindness 21×.
- Hotel/excursion: failure-by-absence — no scan runs, so nothing can error.

### RC2 — Disabled-better-code + competing stacks
The best-engineered implementation is disabled; the weakest runs in production.
- Lifecycle: 4 schedulers, 3 data sources. `d2m_lifecycle_scheduler.py` (stateful dedup, ARC auto-execute) and `lifecycle_calendar_engine.py` (reads `completed_tps`, skips paid) are DISABLED; the weakest (`lifecycle_scheduler.py`, no dedup, exact-date-only) runs.
- Air: 4 stacks. Production JSON path live-but-blind; SQLite daemon (`fare_watch_db.py`) better but never rewired ("Sterling's call", :23-26), frozen 2026-05-30; cruise + legacy sweep stacks dead/uninstalled.

### RC3 — Write-without-read history (the MISSION-172 discarded-votes pattern)
- Lifecycle: `logs/tp_alerts.jsonl` = 2.8 MB, **zero readers**; `arc_price_dispatcher.py` writes per-scan JSONs **no code reads**, and it's only reachable from the disabled scheduler.
- Hotel/excursion: no client/TP-keyed write at all. "What did we find for client X, TP Y, date Z?" is unanswerable.
- Air: only `fare_history.json` has a real read path (good) — but starved by broken scans; SQLite history frozen.

### RC4 — Committed live secrets (the D4 default-creds pattern) — SECURITY
- **LIVE @D2MC2C bot token committed:** `config/telegram_gw.env` `TELEGRAM_D2MC2C_TOKEN=875468…` matches live `bot_id 8754681793`. In git history.
- **Centrav session cookies committed:** `core/travel/data/centrav_session.json` git-tracked (expired 2026-05-28, low live-exposure, still wrong).

Plus: zero tests on the date-window math where the real bugs live; fare tests deleted (orphan `.pyc` only).

---

## PRIORITIZED FIX LIST (most dangerous / time-sensitive first)

**P0-SECURITY — rotate + uncommit secrets.**
`git rm --cached config/telegram_gw.env core/travel/data/centrav_session.json`,
add to `.gitignore`, **rotate the @D2MC2C bot token** (exposed in history).

**P0-OPS — universal dead-man's-switch.** Page Commander whenever any scan run
checks 0 items, errors, or hasn't succeeded in N hours; make systemd exit non-zero
on auth failure. Kills the silent-blindness class across all three at once.

**P1 — restore the live scans.**
- Lifecycle: `calculate_due_phases` fire on `due_date <= today AND scheduled AND not sent`; write phase → `sent` after draft (catch-up + idempotency in one); warn on "0 drafts but N due."
- Air: Centrav cookie auto-keepalive (mirror MISSION-166) + pre-flight session check that pages before the scan if dead; stop `break`-ing — mark each watch `auth_error`.

**P1 — completion model.** Lifecycle `TPStatus.COMPLETE` is defined but never set →
97 false OVERDUE alerts (TP 0.5 at −481 days) flooding `wing_comms.md` every 6h.
Read `completed_tps` from dossier frontmatter; exclude COMPLETE from actionable.

**P1 — POST_DEP date bug.** `thunderbird_tp_scheduler.py:351` uses `departure` not
`return_date` → "Welcome Home" fires while client is at sea. Route POST_DEP through
`return_date`; make missing `booking_date` a BLOCKED status, not an mtime guess (:286).

**P2 — collapse split-brain.** One scheduler + one source of truth (lifecycle); one
fare stack + one store (air). Retire/delete the disabled duplicates after migrating
their good dedup/completion logic. Delete `deploy/` sweep + `agents/thunderbird_fare_sweep.py`.

**P2 — wire CONDUCT→DOCUMENT→CAPTURE.** One `scan_results` store keyed
`(client_id, tp_id, category, scan_date, source, results_json)` with a read API
(`--history --client X --tp 4.2`), modeled on `fare_watch_db.py`. Wire air/hotel/
excursion scans into it; prove the read path is exercised.

**P2 — hotel/excursion honesty.** Until a real scan path is wired (hotel = Bedsonline
Playwright since Hotelbeds API creds are empty; excursion = the live `/tour-price`
GetYourGuide scraper, not the credential-less `thunderbird_excursions` stub), label
TP_5/TP_6 emails as manual-research prompts — stop promising research the system
never performs.

**P2 — alert dedup + $0 guard (air).** Add `last_alert_state`/`last_alerted_at`;
suppress re-fire unless state changes. Skip watches with `current_price_pp == 0`
(9 active) — `0 < alert_below` reads as a false price drop on first real fetch.

**P3 — tests.** Unit-test the date-window math (`generate_schedule`,
`calculate_due_phases`, POST_DEP) with fixtures; restore fare-check tests.

---

*Audited by 3 parallel agents (read-only) + Opus synthesis, 2026-06-09. All
entrypoints run clean — failures are logical/architectural, not crashes, which is
exactly why they went unnoticed.*
