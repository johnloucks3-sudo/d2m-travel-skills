# DURABLE SCHEDULING — Thunderbird Wing
## Audit · Standard · Timer Registry
**Version:** 1.0  
**Date:** 2026-06-11  
**Mission:** MISSION-092 (MISSION-SCHEDULING-DURABLE)  
**Author:** Claude Code (Sonnet 4.6) · Hale COS review  

---

## 1. EXECUTIVE SUMMARY

**The durable scheduling standard already exists.** The Thunderbird Wing runs 105 active systemd --user timers. The session-only CronCreate jobs that created MISSION-092 (June 1/4 dates) are expired and no active fragile jobs remain. This document codifies the existing standard, identifies the gaps, and registers all scheduling-relevant timers as a persistent reference.

**Key findings:**
- Zero active session-only scheduled jobs (`.claude/scheduled_tasks.json` does not exist; the lock PID is the current session only)
- The original jobs (IDs 2affb392, 85e42493, 8dfece25 — Furlow/Nichols/Ely-Darrow dining June 1; McLeod gate June 4) fired or expired — all past
- The wing lifecycle pipeline IS durable: five chained systemd timers from 05:30 MT through 07:30 MT
- Three actionable gaps remain (see §5)

---

## 2. WHAT HAPPENED — THE ORIGINAL PROBLEM

MISSION-092 was created 2026-05-31 to replace in-session CronCreate jobs. Those jobs used Claude Code's session-local scheduling (`.claude/scheduled_tasks.lock`) — when the session ends, the jobs vanish. The specific jobs were:

| Job ID | Client | Action | Date | Status |
|--------|--------|--------|------|--------|
| 2affb392 | Furlow | Dining reminder | June 1, 2026 | EXPIRED |
| 85e42493 | Ely-Darrow | Dining reminder | June 1, 2026 | EXPIRED |
| 8dfece25 | Nichols | Dining reminder | June 1, 2026 | EXPIRED |
| (McLeod gate) | McLeod | Itinerary gate | June 4, 2026 | EXPIRED |

**These jobs no longer exist.** Forward-looking: any new per-client one-time actions must use systemd --user timers, not session-local scheduling. The pattern below governs.

---

## 3. THE DURABLE STANDARD — systemd --user timers

### 3.1 Why systemd --user

- **Survives session exit.** Timers persist across Claude Code session boundaries, reboots (via `enable`), and idle/wake cycles.
- **`Persistent=true` catches up.** If the machine is off at the scheduled time, the service fires on next boot — no silent miss.
- **Monitorable.** `systemctl --user list-timers` shows the full fleet, next fire times, and last-ran times at a glance.
- **Standard on yoga.** 105 timers already running; the Wing has full operational familiarity.

### 3.2 Canonical Timer Template

```ini
# /home/john/.config/systemd/user/<name>.timer
[Unit]
Description=<Human-readable description>
Requires=<name>.service

[Timer]
OnCalendar=<schedule>           # e.g. *-*-* 06:00:00 America/Denver
Persistent=true                 # REQUIRED — catch up on missed fires
RandomizedDelaySec=30           # Optional: spread load if many timers share a wall-clock time

[Install]
WantedBy=timers.target
```

```ini
# /home/john/.config/systemd/user/<name>.service
[Unit]
Description=<Human-readable description>
After=network.target

[Service]
Type=oneshot
# MANDATORY: use the venv Python, not /usr/bin/python3
ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/<path/to/script>.py
WorkingDirectory=/home/john/Thunderbird
StandardOutput=append:/home/john/Thunderbird/logs/<name>.log
StandardError=append:/home/john/Thunderbird/logs/<name>.log
# Optional: allow non-zero exit without marking service failed (for health checks)
# SuccessExitStatus=1

[Install]
WantedBy=default.target
```

**Enable and start:**
```bash
systemctl --user daemon-reload
systemctl --user enable --now <name>.timer
systemctl --user status <name>.timer
```

### 3.3 Python Interpreter Standard

**MANDATORY:** All wing service files must use the venv Python:
```
/home/john/Thunderbird/.venv/bin/python3
```
NOT `/usr/bin/python3`. The venv carries all installed dependencies (Gmail API, Anthropic client, requests, etc.). System Python will fail on imports.

### 3.4 Headless Claude Dispatch from a Timer

When a timer needs to spawn a Claude task (rather than running pure Python), use:

**Preferred: `OpsCenter/dispatch_claude.py`** (the Wing's foolproof wrapper)
```bash
ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/OpsCenter/dispatch_claude.py \
    --task "<task-name>" \
    --output /home/john/Thunderbird/output/<output>.md \
    --prompt "Do X. WRITE output to /home/john/Thunderbird/output/<output>.md" \
    --model sonnet
```

This wrapper:
1. Verifies `claude-token-monitor.timer`, `claude-oauth-keepalive.timer`, `thunderbird-watchdog.timer` are active
2. Strips stale `ANTHROPIC_API_KEY` (prevents OAuth preemption)
3. Loads MAX OAuth from `~/.claude/.credentials.json`
4. Uses `subprocess.Popen` with `start_new_session=True`
5. Redirects logs to `logs/<task>.log`
6. Returns JSON: `{"status":"SPAWNED","pid":...,"log_file":...,"output_file":...}`

**DO NOT** use bare `claude -p ...` in ExecStart — the shell environment carries a stale API key that preempts OAuth.

**Modern alternative (v2.1.142+):** `claude agents --bg -p "..."` — background session, resumable via `/resume <session_id>`. See `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` for full migration table.

### 3.5 One-Time / Per-Client Event Pattern

For one-time future actions (e.g., "remind about dining Jun 1"), use a systemd transient timer rather than a session-local job:

```bash
systemd-run --user --on-calendar="2026-09-18 06:00:00 America/Denver" \
    /home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/scripts/<script>.py
```

Or create a named `.timer`+`.service` pair, enable it, and `systemctl --user disable` after it fires (the service can self-disable on success).

---

## 4. LIFECYCLE PIPELINE — CURRENT STATE

The core lifecycle email pipeline runs as a chain of five systemd timers each morning. This is the primary Claude-driven workflow and IS fully durable.

```
05:30 MT  d2m-lifecycle.timer           → D2M/d2m_lifecycle_scheduler.py
                                          (DUPLICATE / CONFLICT — see §5.1)
          d2m-lifecycle-scheduler.timer → core/lifecycle/lifecycle_scheduler.py
                                          (ETB-003 CANONICAL — 06:00 MT / 12:00 UTC)

06:35 MT  lifecycle-calendar-engine.timer → scripts/lifecycle_calendar_engine.py
                                             *** DISABLED — see §5.2 ***

06:40 MT  thunderbird-flight-scan.timer → scripts/flight_scan_trigger.py
                                          (auto-registers fare watches at TP 1.2)

07:00 MT  hale-draft-engine.timer       → D2M/hale_draft_engine.py
                                          *** uses /usr/bin/python3 — see §5.3 ***

07:30 MT  thunderbird-dani-voice.timer  → scripts/dani_voice_draft.py
                                          (spawns headless Claude Sonnet via
                                           thunderbird_headless_spawn.spawn_headless_claude)

→ WF-17 gate → Commander sends
```

---

## 5. GAPS — THREE ITEMS TO RESOLVE

### 5.1 DUPLICATE LIFECYCLE TIMERS (d2m-lifecycle.timer vs d2m-lifecycle-scheduler.timer)

**Problem:** Two timers fire the lifecycle pipeline every morning.

| Timer | Schedule | Script | Status |
|-------|----------|--------|--------|
| `d2m-lifecycle.timer` | 05:30 MT daily | `D2M/d2m_lifecycle_scheduler.py` + `generate_wing_status.py` + `inbox_executor.py` | ENABLED + ACTIVE (fires 05:30 MT) |
| `d2m-lifecycle-scheduler.timer` | 06:00 MT / 12:00 UTC | `core/lifecycle/lifecycle_scheduler.py` | ENABLED + ACTIVE (ETB-003 canonical) |

The `d2m-lifecycle.service` file carries a comment `# DISABLED 2026-06-08 — interim notices eliminated` **but was never actually disabled in systemd.** A comment does not disable a unit; `systemctl --user disable d2m-lifecycle.timer` does.

**Recommendation:** Determine which scripts from `d2m-lifecycle.service` are still needed (`generate_wing_status.py` and `inbox_executor.py` may be independent of lifecycle scheduling). If `generate_wing_status.py` is still active: move it to its own standalone timer. Then: `systemctl --user disable d2m-lifecycle.timer` to match the June 8 intent.

**Risk:** Firing both schedulers daily may double-draft lifecycle emails. Confirm dedup in `state/lifecycle_scheduler_state.json` (it has a `fired_actions` ledger with `client:TP:ACTION:date` keys) before disabling.

### 5.2 lifecycle-calendar-engine.timer IS DISABLED (Gap in Lifecycle Chain)

**Problem:** `lifecycle-calendar-engine.timer` (06:35 MT, Persistent=true) is configured but **inactive dead**. Its service runs `scripts/lifecycle_calendar_engine.py --timer --horizon 30` — a 30-day forward-look that bridges the ETB-003 scheduler output to the draft engine inputs.

**Current effect:** The pipeline has a gap between `d2m-lifecycle-scheduler.timer` (06:00 MT) and `thunderbird-flight-scan.timer` (06:40 MT). If the calendar engine step is genuinely retired, document why and remove the unit files. If it is still needed, enable it:

```bash
systemctl --user enable --now lifecycle-calendar-engine.timer
```

**Recommendation:** Sterling (A7) to verify whether `lifecycle_calendar_engine.py` is still in the active workflow or was superseded by ETB-003. Enable or retire.

### 5.3 hale-draft-engine.service Uses System Python (Not Venv)

**Problem:** `hale-draft-engine.service` has:
```
ExecStart=/usr/bin/python3 /home/john/Thunderbird/D2M/hale_draft_engine.py
```

All other wing services use `/home/john/Thunderbird/.venv/bin/python3`. This is an inconsistency that will cause silent import failures if `hale_draft_engine.py` imports any wing dependency (requests, anthropic, google-auth, etc.).

**Recommendation:** Update the service file:
```ini
ExecStart=/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/D2M/hale_draft_engine.py
```

Then: `systemctl --user daemon-reload && systemctl --user restart hale-draft-engine.service`

### 5.4 (Technical Debt, Low Priority) dani_voice_draft.py Uses Legacy Spawn Pattern

`scripts/dani_voice_draft.py` imports `from thunderbird_headless_spawn import spawn_headless_claude` — the `subprocess.Popen` pattern. The `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md` v2.1 marks this DEPRECATED in favor of `claude agents --bg`. The script works today; migration to `dispatch_claude.py` or `claude agents --bg` is a technical debt item, not urgent.

---

## 6. TIMER REGISTRY

All scheduling-relevant systemd --user timers as of 2026-06-11. Grouped by function.

### 6.1 Lifecycle Pipeline (core client workflow)

| Timer | Schedule | Script | Status | Persistent | Notes |
|-------|----------|--------|--------|------------|-------|
| `d2m-lifecycle.timer` | 05:30 MT daily | `D2M/d2m_lifecycle_scheduler.py` + 2 others | ACTIVE | — | DUPLICATE — see §5.1 |
| `d2m-lifecycle-scheduler.timer` | 06:00 MT daily (12:00 UTC) | `core/lifecycle/lifecycle_scheduler.py` | ACTIVE | yes | ETB-003 CANONICAL |
| `lifecycle-calendar-engine.timer` | 06:35 MT daily | `scripts/lifecycle_calendar_engine.py` | DISABLED (inactive dead) | yes | Gap — see §5.2 |
| `thunderbird-flight-scan.timer` | 06:40 MT daily | `scripts/flight_scan_trigger.py` | ACTIVE | yes | Auto-registers fare watches at TP 1.2 |
| `hale-draft-engine.timer` | 07:00 MT daily | `D2M/hale_draft_engine.py` | ACTIVE | yes | Wrong python path — see §5.3 |
| `thunderbird-dani-voice.timer` | 07:30 MT daily | `scripts/dani_voice_draft.py` | ACTIVE | yes | Spawns headless Sonnet (legacy spawn) |
| `d2m-validation-report.timer` | Monthly 15th 13:00 UTC | `core/lifecycle/validation_report_generator.py` | ACTIVE | yes | ETB-004 |

### 6.2 Alerts & Watchers

| Timer | Schedule | Script | Status | Persistent | Notes |
|-------|----------|--------|--------|------------|-------|
| `tp-alert-engine.timer` | Every 6h (00/06/12/18 MDT) | `scripts/tp_alert_engine.py` | ACTIVE | yes | 14-day TP early warning; pure Python |
| `d2m-fpd-alert.timer` | 01:35 MT daily | `core/watchtower/thunderbird_fpd_alert.py` | ACTIVE | yes | FPD due-date alerts |
| `fpd-auto-update.timer` | Every 15 min | `scripts/fpd_auto_update.py` | ACTIVE | — | Real-time FPD status |
| `thunderbird-fare-watch.timer` | 08:00 MT daily | `scripts/fare_watch_centrav.py` | ACTIVE | yes | Centrav B2B fare polling |
| `d2m-ita-fare-watch.timer` | 05:30 MT daily | (ITA fare watch) | ACTIVE (no prior run) | — | |
| `dossier-validation-sweep.timer` | — | — | ACTIVE (no prior run) | — | |

### 6.3 Keepalive / Credential Refresh

| Timer | Schedule | Script | Status | Persistent | Notes |
|-------|----------|--------|--------|------------|-------|
| `keepalive-supervisor.timer` | Every ~25 min | `scripts/keepalive_supervisor.py` | ACTIVE | — | MISSION-211 meta-watchdog; LLM-free |
| `claude-oauth-keepalive.timer` | Every 90 min | — | ACTIVE | — | Claude MAX OAuth |
| `tess-token-keepalive.timer` | Every 90 min | — | ACTIVE | — | TESS JWT |
| `johnloucks3-oauth-keepalive.timer` | Every 90 min | — | ACTIVE | — | johnloucks3 Gmail |
| `d2mconcierge-oauth-keepalive.timer` | Every 45 min | — | ACTIVE | — | d2mconcierge Gmail |
| `portal-keepalive.timer` | Every 3h | — | ACTIVE | — | Centrav + Regent portal |

### 6.4 Intel & Research

| Timer | Schedule | Script | Status | Notes |
|-------|----------|--------|--------|-------|
| `thunderbird-dembe-intel.timer` | 07:00 MT daily | — | ACTIVE | Dembe intel sweep |
| `d2m-intel-telegram.timer` | 01:00 MT daily | — | ACTIVE | Intel → Telegram |
| `d2m-x-osint.timer` | 02:00 MT daily | — | ACTIVE | X/Twitter OSINT |
| `thunderbird-innovation-scan.timer` | 01:45 MT daily | — | ACTIVE | Daily innovation scan |
| `thunderbird-innovation-scan-weekly.timer` | Sun 01:30 MT | — | ACTIVE | Weekly deep scan |
| `thunderbird-perx-intel.timer` | 02:00 MT / 14:00 MT | — | ACTIVE | Perx intel |

### 6.5 Communications & Briefs

| Timer | Schedule | Script | Status | Notes |
|-------|----------|--------|--------|-------|
| `thunderbird-daily-brief.timer` | 06:00 MT daily | — | ACTIVE | Morning brief generation |
| `thunderbird-eod-brief.timer` | 18:00 MT daily | — | ACTIVE | EOD brief |
| `thunderbird-1730-nomination.timer` | 17:30 MT daily | `agents/thunderbird_1730_nomination.py` | ACTIVE | Incubator nomination ping |
| `d2m-incubator-overnight-report.timer` | 06:30 MT daily | — | ACTIVE | Incubator digest |
| `d2m-incubator-execute.timer` | 18:30 MT | — | ACTIVE | Overnight incubator build |
| `thunderbird-inbox-sweep.timer` | Every 2h (20:00/18:00) | — | ACTIVE | Inbox sweep |
| `d2m-correspondence-sync.timer` | 06:00 MT daily | — | ACTIVE | Correspondence sync |

### 6.6 System Health & Watchdogs

| Timer | Schedule | Script | Status | Notes |
|-------|----------|--------|--------|-------|
| `thunderbird-watchdog.timer` | Every 10 min | — | ACTIVE | Infrastructure watchdog (prerequisite for headless spawn) |
| `thunderbird-commander-directive-sweep.timer` | Every 10 min | — | ACTIVE | Commander directive processing |
| `thunderbird-coo-watchdog.timer` | Every 10 min | — | ACTIVE | COO-layer watchdog |
| `thunderbird-sentinel.timer` | Every 5 min | — | ACTIVE | Sentinel health |
| `thunderbird-health-check.timer` | Every 30s | — | ACTIVE | Fast health ping |
| `thunderbird-autosave.timer` | Every 10 min | — | ACTIVE | Session autosave |
| `hale-cc-heartbeat.timer` | Every 10 min | — | ACTIVE | Hale CC heartbeat |
| `thunderbird-heartbeat.timer` | 06:00 MT daily | — | ACTIVE | Daily heartbeat |
| `thunderbird-boot-recovery.timer` | (post-boot) | — | ACTIVE | Boot recovery |
| `hale-incident-handler.timer` | Every 5 min | — | ACTIVE | Incident handling |

### 6.7 Data Sync & Memory

| Timer | Schedule | Script | Status | Notes |
|-------|----------|--------|--------|-------|
| `thunderbird-qdrant-reindex.timer` | 05:31 MT daily | — | ACTIVE | MISSION-125 Qdrant daily re-index |
| `d2m-drive-sync.timer` | 02:01 MT daily | — | ACTIVE | Google Drive sync |
| `thunderbird-drive-sync.timer` | 23:00 MT daily | — | ACTIVE | Drive sync (second) |
| `thunderbird-spsa-sheets-sync.timer` | 06:45 MT daily | — | ACTIVE | SPSA sheets |
| `thunderbird-spsa-intake.timer` | 06:30 MT / 18:00 MT | — | ACTIVE | SPSA intake |
| `thunderbird-tess-sync.timer` | 06:15 MT daily | — | ACTIVE | TESS sync |
| `d2m-booking-monitor.timer` | Every 30 min (06:30/18:30) | — | ACTIVE | Booking status monitor |
| `hale-chatlog-backup.timer` | Every hour | — | ACTIVE | Chat log backup |
| `thunderbird-evernote-backup.timer` | Weekly Mon 02:00 MT | — | ACTIVE | Evernote backup |
| `thunderbird-backup-verify.timer` | Weekly Mon 02:30 MT | — | ACTIVE | Backup verification |
| `thunderbird-monthly-archive.timer` | Monthly 1st 07:16 MT | — | ACTIVE | Monthly archive |

### 6.8 Dashboard & Monitoring

| Timer | Schedule | Script | Status | Notes |
|-------|----------|--------|--------|-------|
| `hale-dashboard-refresh.timer` | Every ~1 min | — | ACTIVE | Hale dashboard |
| `d2m-dashboard-refresh.timer` | Every hour (18:00) | — | ACTIVE | D2M dashboard |
| `thunderbird-blackboard-sync.timer` | Every 10 min | — | ACTIVE | Blackboard sync |
| `thunderbird-ai-metrics.timer` | (on-demand) | — | ACTIVE | AI metrics |
| `d2m-usage-monitor.timer` | Every ~20 min | — | ACTIVE | Token usage monitor |
| `d2m-daily-executor.timer` | Every 4h | — | ACTIVE | Daily executor |

### 6.9 Other Active Timers

| Timer | Schedule | Script | Status | Notes |
|-------|----------|--------|--------|-------|
| `hale-visual-synthesis.timer` | 05:30 MT daily | — | ACTIVE | Visual synthesis |
| `hale-daily-audit.timer` | 06:00 MT daily | — | ACTIVE | Daily audit |
| `hale-touchpoint-proposer.timer` | 06:00 MT daily | — | ACTIVE | TP proposals |
| `hale_brain_monitor.timer` | 18:00 MT daily | — | ACTIVE | Brain monitor |
| `hale-phase2-visuals.timer` | Sun 18:00 MT weekly | — | ACTIVE | Visual processing |
| `d2m-preflight-gate.timer` | 05:45 MT daily | — | ACTIVE | Pre-flight gate |
| `d2m-preflight.timer` | 06:50 MT daily | — | ACTIVE | Pre-flight checks |
| `d2m-power-harvest.timer` | 01:50 MT daily | — | ACTIVE | Power harvest |
| `d2m-sculptor-learn.timer` | 02:05 MT daily | — | ACTIVE | Sculptor learn |
| `d2m-sculptor-harvest.timer` | 20:13 MT daily | — | ACTIVE | Sculptor harvest |
| `d2m-inbox-cleanup.timer` | 02:30 MT daily | — | ACTIVE | Inbox cleanup |
| `d2m-voice-sync.timer` | 02:31 MT daily | — | ACTIVE | Voice sync |
| `d2m-airline-monitor.timer` | 01:40 MT daily | — | ACTIVE | Airline monitor |
| `d2m-factbook-refresh.timer` | Weekly Mon 01:30 MT | — | ACTIVE | Factbook refresh |
| `thunderbird-silversea-session.timer` | 05:07 MT daily | — | ACTIVE | Silversea session keepalive |
| `thunderbird-continuity-recert.timer` | 06:00 MT daily | — | ACTIVE | Continuity re-cert |
| `thunderbird-logrotate.timer` | 03:00 MT daily | — | ACTIVE | Log rotation |
| `thunderbird-war.timer` | Weekly Fri ~21:00 MT | — | ACTIVE | WAR report |
| `thunderbird-sentinel-nginx.timer` | Every ~30s | — | ACTIVE | Nginx sentinel |
| `d2m-email-intel.timer` | (active, running) | — | ACTIVE | Email intel |
| `d2m-dispatcher.timer` | Every ~2 min | — | ACTIVE | Task dispatcher |

---

## 7. WHAT STILL NEEDS SYSTEMD TIMERS

As of 2026-06-11, no active workflows are running as session-only jobs. The three items below require attention before creating NEW timers:

| Need | Type | Action |
|------|------|--------|
| Per-client one-off reminders (dining windows, FPD alerts beyond d2m-fpd-alert) | One-time or date-bounded | Use `systemd-run --user --on-calendar=...` pattern (§3.5) |
| McLeod FPD Jul 22 reminder (DEFERRED ALERT in hale_state.json) | One-time | Covered by d2m-fpd-alert.timer — verify it reads deferred_alerts |
| Any new T-position lifecycle trigger for Spencer, Loucks personal | Per-booking | Wire into ETB-003 canonical lifecycle_scheduler.py |

---

## 8. QUICK REFERENCE — COMMANDS

```bash
# View all wing timers (next fire, last ran)
systemctl --user list-timers --all --no-pager | grep -E "d2m|thunder|lifecycle|hale|tp-alert|keepalive|fpd"

# Check a specific timer
systemctl --user status <name>.timer

# Start/stop a timer manually
systemctl --user start <name>.timer
systemctl --user stop <name>.timer

# Enable (survive reboot) / disable
systemctl --user enable <name>.timer
systemctl --user disable <name>.timer

# Reload after editing unit files
systemctl --user daemon-reload

# Spawn headless Claude task (the safe wrapper)
/home/john/Thunderbird/.venv/bin/python3 /home/john/Thunderbird/OpsCenter/dispatch_claude.py \
    --task "my-task" --output /home/john/Thunderbird/output/result.md \
    --prompt "Do X and WRITE to /home/john/Thunderbird/output/result.md" --model sonnet

# Check keepalive health
cat /home/john/Thunderbird/OpsCenter/keepalive_health.json

# View lifecycle scheduler state (fired action dedup ledger)
cat /home/john/Thunderbird/state/lifecycle_scheduler_state.json | python3 -m json.tool | grep -A2 "fired_actions"
```

---

## 9. OPEN ITEMS FOR STERLING (A7)

| # | Item | Priority | Action |
|---|------|----------|--------|
| 1 | d2m-lifecycle.timer / d2m-lifecycle-scheduler.timer duplicate | P1 | Determine if generate_wing_status.py and inbox_executor.py need their own timers; then `systemctl --user disable d2m-lifecycle.timer` |
| 2 | lifecycle-calendar-engine.timer disabled | P2 | Confirm: still needed by workflow? If yes → `systemctl --user enable --now lifecycle-calendar-engine.timer`. If no → remove unit files. |
| 3 | hale-draft-engine.service python path | P2 | Change `/usr/bin/python3` → `/home/john/Thunderbird/.venv/bin/python3` in service file; daemon-reload |
| 4 | dani_voice_draft.py legacy spawn | P3 | Migrate from `thunderbird_headless_spawn.spawn_headless_claude` to `dispatch_claude.py` when convenient |

---

*MISSION-092 deliverable complete. Zero session-only jobs remain. Durable standard: systemd --user timers with Persistent=true. Full registry above. Three gaps logged for Sterling.*  
*— 17:52 MT*
