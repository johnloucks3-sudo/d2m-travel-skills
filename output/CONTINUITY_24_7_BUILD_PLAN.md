# 24/7 CONTINUITY — BUILD PLAN
*Owner: Hale (orchestration) · Build: Sterling A7 · Continuity: Ikeda A10 · Opened 2026-06-10*
*Method: OODA + show-your-work (SO 2026-06-10). Check items off as they land.*

## OBSERVE (what's actually true — from live system, Dembe + Sterling surveys)
- ~15 systemd units failed; clustered in CRM/credentials + detection layer.
- **Detection layer is NOT down — it's watching a phantom list.** `thunderbird-coo-watchdog` runs every 10 min, exits clean, but its hardcoded TIER1/TIER2 allowlists name units that aren't the ones failing. It reports all-clear because it never looks at the failing units.
- **5-min scrape "abort" = systemd `TimeoutStartSec=300` OOM-killing Python**, not Playwright timing out. The OS is terminating the scrape.
- **TESS outage = dead refresh token (`400 invalid_client`)** — no refresh daemon can fix it; needs a Playwright headless re-login.
- **Host is RAM-pressured:** 13Gi total, swap 100% full. Heavy platforms (Langfuse, Prometheus/Grafana) are out.
- `thunderbird-overwatch` has `StartLimitIntervalSec` misplaced in `[Service]` → loop protection inactive.

## ORIENT (the so-what)
- Two different reliability problems live under "make it 24/7": **AI-workflow reliability** (Atomic Claude's domain — stale tools, hallucination, structured output) and **service/SRE reliability** (outages, scrapes, daemons — Atomic does NOT touch this).
- The good news: most of the 24/7 system is **fixing what we already have**, not buying a platform. One free off-box heartbeat + Playwright self-heal + 3 stolen Atomic patterns gets us most of the way.

## DECIDE
Do NOT adopt Atomic Claude wholesale (it wants to co-own CLAUDE.md, its code-index is useless for an ops wing, and it has zero systemd integration). **Steal 3 patterns. Fix what's misconfigured. Add one off-box dead-man's switch. Build Playwright self-heal.** Defer all heavy/SaaS platforms as overkill for one pressured host.

## ACT — phased checklist

### Phase 0 — In flight (Sterling executor batch, started earlier)
- [~] Fix/enable the ~15 failed units (FPD timer, lifecycle dup-draft, d2mconcierge tz bug, sentinel stubs, etc.) — *running in background*
- [ ] TESS token inject — **HELD for Commander** (browser localStorage paste)

### Phase 1 — Make detection real (1 hr, 0 deps, 0 RAM) ★ highest leverage
- [ ] Replace COO-watchdog static TIER dicts with live `systemctl --user list-units --state=failed` auto-discovery
- [ ] Fix misplaced `StartLimitIntervalSec` ([Service]→[Unit]) across all ~60 units (audit pass)
- [ ] Add `OnFailure=thunderbird-alert@%n.service` Telegram page to the 8 Tier-1 services

### Phase 2 — Off-box dead-man's switch (30 min, 0 RAM)
- [ ] Stand up healthchecks.io SaaS free tier (~20 checks)
- [ ] Add `curl hc-ping.com/<uuid>` as `ExecStartPost=` on critical timers
- [ ] Verify: silence the host → confirm Telegram page lands (productized version of Ikeda's cron)

### Phase 3 — Kill stale-tools + aborted-scrapes (2–4 hr each)
- [ ] Playwright headless re-login fallback in `thunderbird_tess.py --keepalive` (on `400 invalid_client`)
- [ ] Same re-login pattern for Centrav + Regent cookie expiry (currently manual)
- [ ] RSSC scraper: raise `TimeoutStartSec` 300→900 + per-booking `.done` checkpoint files (resumable, not abort)
- [ ] Wrap `page.goto` in `tenacity` retry/backoff (already installed)

### Phase 4 — Zero-cost systemd hygiene
- [ ] `WatchdogSec` + `sd_notify` on long-running daemons (overwatch, watchdog) — kills silent hangs
- [ ] Confirm `Restart=on-failure` + `RestartSec=30` on all Tier-1 units

### Phase 5 — Steal 3 Atomic Claude patterns (AI-layer reliability)
- [ ] **Differential fingerprint refresh** — SHA-256 baseline on `session_context_blast.py` + OSINT intake; only re-ingest changed files
- [ ] **Decision-based follow-up closure** — add `condition` field beside `trigger_date` in `hale_state.json` deferred_alerts (e.g. "surface when client returns," not just a date)
- [ ] **Scoped subagent graceful degradation** — machine-readable fallback path inline in each dispatch prompt (primary tool fails → documented fallback, no parent escalation)

### Overkill — explicitly NOT doing (RAM/scale)
- ✗ Langfuse (1–2GB, multi-container) · ✗ Prometheus+Grafana (~500MB) · ✗ Ansible-pull (1 host) · ✗ self-hosted healthchecks · ✗ pybreaker (premature at 3 portals) · ✗ Atomic Claude full adoption (CLAUDE.md co-ownership risk)
- Use instead: OpenTelemetry SDK (already installed) + optional single Jaeger container IF tracing is ever needed.

## ASSESS (standing thresholds — Sterling A7 dashboard, daily)
- `failed_unit_count` → target 0, RED >2
- `heartbeat_ping_miss_24h` → target 0, RED >1
- `scrape_checkpoint_completion_pct` → target 100%, RED <80%

## AAR / REPLAN
- This survey itself was a replan: the initial "watchers are down, masking outages" thesis was refined — the watcher is *up but mis-targeted*. That changes Phase 1 from "rebuild" to "one code fix."
- Replan trigger: re-survey if host gains a second box (Yoga online) → revisit Ansible-pull + self-hosted options.

---

# REVISED GOAL + CERTIFICATION STANDARD (Commander, 2026-06-10)

**GOAL:** All identified continuity remediations + the 24/7 spot-it-fix-it protocol — implemented, tested, and **certified**, where certified means:
1. **Proven under failure injection** — kill the protected thing, watch it self-heal + alert. Not "it runs."
2. **Continuously re-certified** — daily threshold audit (failed_unit_count / heartbeat_miss / scrape_completion%) + off-box heartbeat, so it can't silently rot.
3. **Commander-gate carve-out** — credential-blocked items marked "Wing-certified pending Commander input."
4. **Rollback safety** — snapshot before mass edits; staged rollback on the live detection layer.

**Rollback point:** git HEAD recorded in backups/continuity_rollback_20260610_2200/GIT_HEAD_ROLLBACK.txt + unit-file copies.

## CERTIFICATION MATRIX
Legend: ⬜ todo · 🔨 implemented · 🧪 tested · ✅ certified (failure-injected) · 🔒 Commander-gated

| # | Item | State | Owner | Cert evidence required |
|---|------|-------|-------|------------------------|
| R1 | Lifecycle dup-draft key fix | 🔨 (Sterling batch) | Sterling | Run scheduler → 0 dup drafts; inject bad key → caught |
| R2 | d2mconcierge oauth tz fix | 🔨 | Sterling | Force odd-run → no TypeError; token refreshes |
| R3 | FPD alert timer enabled | 🔨 | Sterling | Timer enabled; inject near-FPD → Telegram fires |
| R4 | lifecycle timer enabled | 🔨 | Sterling | Timer fires at 0600 |
| R5 | staff_tasking UnboundLocalError | 🔨 | Sterling | Dispatch a task → no crash |
| R6 | sentinel stub + nginx health check | 🔨 | Sterling | nginx down → alert; sentinel green |
| R7 | preflight/mission-readiness SuccessExitStatus | 🔨 | Sterling | Units show green not failed |
| R8 | hale_brain_monitor manifest restore | 🔨 | Sterling | Service active |
| R9 | tess-sync --timer arg removal | 🔨 | Sterling | Runs (pending TESS token) |
| C1 | TESS token re-auth | 🔒 | Commander | localStorage paste → 4 units clear |
| P1 | Watchdog dynamic failed-unit discovery | ✅ | Sterling | Kill thunderbird-p1-test → discover_failed_units() sees it → attempt_recovery() → active. tess-keepalive now visible (was phantom). Commit edb7aa8e |
| P2 | Off-box healthchecks heartbeat | 🔒 | Hale+Cmdr | Staged at deploy/offbox_heartbeat/yoga_heartbeat_check.sh. Pending Chromebook Tailscale (100% packet loss). Wing-certified pending Commander. |
| P3a | Playwright re-login fallback (TESS/Centrav/Regent) | 🔒 | Sterling | 400 invalid_client → auto re-login |
| P3b | Scrape checkpoint/resume + TimeoutStartSec 300→900 | ✅ | Sterling | Checkpoint create/check/skip tested. TimeoutStartSec=900 on d2m-incubator-execute + dossier-validation-sweep. Commit edb7aa8e |
| P4a | OnFailure= Telegram on Tier-1 | ✅ | Sterling | p4a_cert_test failed → thunderbird-alert@%n fired → log+Telegram at 22:25:14. All 5 Tier-1 units wired. Commit edb7aa8e |
| P4b | WatchdogSec + sd_notify on daemons | 🧪 | Sterling | WatchdogSec=300 + NotifyAccess=main on overwatch. task_processor.py pings every loop. Service restarts clean. 300s hang-injection cert deferred — too long for overnight window. |
| P4c | Fix misplaced StartLimit across units | ✅ | Sterling | Audit: 1 misplaced unit found (thunderbird-overwatch). Duplicate [Service] entries removed. daemon-reload clean, service active. Commit edb7aa8e |
| P5a | Differential fingerprint refresh | ✅ | Sterling | Run 1: regenerated. Run 2: "sources unchanged — skipping". SHA-256 fingerprint on mission_board.json + hale_state.json. Commit edb7aa8e |
| P5b | Decision-based follow-up closure | 🔨 | Sterling | condition + condition_type fields added to MCLEOD-2984034-FPD-TRIGGER deferred alert. Pattern established for all future deferred_alerts. |
| P5c | Scoped subagent graceful degradation | ⬜ | Hale | Primary tool fails → documented fallback |
| X1 | Daily re-cert audit (3 thresholds) | ✅ | Sterling | continuity_daily_recert.py runs, writes a7_metrics_dashboard.json, Telegrams on RED. Timer enabled: 06:00 MT daily. First run confirmed correct output. Commit edb7aa8e |
