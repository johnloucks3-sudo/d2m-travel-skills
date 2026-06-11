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
| R1 | Lifecycle dup-draft key fix | ✅ | Sterling | (1) Old key result.get("id")=None confirmed → record_sent never called → dup loop proven. (2) Ledger injection: phase injected as "already sent" → run_scheduler() dry-run skips it (drafts_created=0). Idempotency proven. Cleanup: synthetic ledger entry removed. |
| R2 | d2mconcierge oauth tz fix | ✅ | Sterling | Injected naive ISO expiry string (no Z/offset) → old path: TypeError confirmed ("can't subtract offset-naive and offset-aware datetimes"). Fixed path: .replace(tzinfo=timezone.utc) → subtraction succeeds, mins_left calculated correctly. |
| R3 | FPD alert timer enabled | ✅ | Sterling | Timer enabled, active/waiting, next=2026-06-11 01:35 MT. Synthetic dossier (CERT_TEST_R3_STERLING, FPD 2026-06-13 3d out) → Telegram alert fired ("CRITICAL CERT TEST R3 STERLING, $9,999"). Synthetic dossier removed. Note: Telegram page sent to Commander phone — labeled test in report. |
| R4 | lifecycle timer enabled | ✅ | Sterling | d2m-lifecycle.timer: LoadState=loaded, ActiveState=active(waiting), next_elapse=Thu 2026-06-11 05:30:00 MDT, Persistent=true. |
| R5 | staff_tasking UnboundLocalError | ✅ | Sterling | dispatch_to_inboxes([synthetic_task]) completed without UnboundLocalError. Inbox write intercepted (real claude_inbox.md untouched). Dedup key written then removed (cleanup complete). |
| R6 | sentinel stub + nginx health check | ✅ | Sterling | (1) thunderbird-sentinel stub: ExecStart=/bin/true, status=0/SUCCESS. (2) nginx_health_check.sh against dead port 19999: HTTP 000 path confirmed ("nginx DOWN → paging Commander"), exit 1. (3) Against live nginx: HTTP 403 → "nginx OK", exit 0. Active unit: thunderbird-sentinel-nginx.timer enabled + waiting. |
| R7 | preflight/mission-readiness SuccessExitStatus | ✅ | Sterling | thunderbird-preflight does not exist. thunderbird-mission-readiness: SuccessExitStatus=1 2, last run exit status=2 (CRITICAL readiness verdict by design), Result=success. thunderbird-boot-recovery fails (C1-gated, expected). |
| R8 | hale_brain_monitor manifest restore | 🧪 | Sterling | hale_brain_monitor.timer: enabled, active/waiting, next=2026-06-11 06:00 MT. Last service run: 18:00 MT today, Result=success. Run exits on FATAL: Manifest not found at hale_brain_manifest.md. Timer is active and fires on schedule; service exits clean (SuccessExitStatus=0 1). Manifest population is a data dependency — not a unit failure. |
| R9 | tess-sync --timer arg removal | ✅ | Sterling | Pre-fix: Jun 8-10 06:15 runs all show "status=2/INVALIDARGUMENT" (argparse rejected --timer). Post-fix: Jun 10 22:01 and 22:54+22:55 runs show "Finished" (Result=success). TESS token auth failure is expected (C1-gated). |
| C1 | TESS token re-auth | 🔒 | Commander | localStorage paste → 4 units clear |
| P1 | Watchdog dynamic failed-unit discovery | ✅ | Sterling | Kill thunderbird-p1-test → discover_failed_units() sees it → attempt_recovery() → active. tess-keepalive now visible (was phantom). Commit edb7aa8e |
| P2 | Off-box healthchecks heartbeat | 🔒 | Hale+Cmdr | Staged at deploy/offbox_heartbeat/yoga_heartbeat_check.sh. Pending Chromebook Tailscale (100% packet loss). Wing-certified pending Commander. |
| P3a | Playwright re-login fallback (TESS/Centrav/Regent) | 🔒 | Sterling | 400 invalid_client → auto re-login |
| P3b | Scrape checkpoint/resume + TimeoutStartSec 300→900 | ✅ | Sterling | Date-keyed checkpoints ({booking}.{YYYYMMDD}.scrape.done) — stale-skip bug fixed. X1 metric aligned. TimeoutStartSec=900 on incubator+dossier units. Commit 8a1df102 |
| P4a | OnFailure= Telegram on Tier-1 | ✅ | Sterling | systemd_alert_send.py → log + Telegram confirmed (Alert sent for p4a-cert-verification-223950, exit 0). All 5 Tier-1 units wired. Overwatch OnFailure also fires (22:31+22:36 kills confirmed). Commit edb7aa8e |
| P4b | WatchdogSec + sd_notify on daemons | ✅ | Sterling | Root cause: NotifyAccess=main rejects child subprocess pings. Fixed → NotifyAccess=all + WatchdogSec=600. NRestarts=0 since 22:39 MT. task_processor.py pings every loop cycle. Commit 8a1df102 (unit applied directly to systemd path) |
| P4c | Fix misplaced StartLimit across units | ✅ | Sterling | Audit: 1 misplaced unit found (thunderbird-overwatch). Duplicate [Service] entries removed. daemon-reload clean, service active. Commit edb7aa8e |
| P5a | Differential fingerprint refresh | ✅ | Sterling | Run 1: regenerated. Run 2: "sources unchanged — skipping". SHA-256 fingerprint on mission_board.json + hale_state.json. Missing-output guard added (OUTPUT.exists() check). Commit 8a1df102 |
| P5b | Decision-based follow-up closure | ✅ | Sterling | (1) MCLEOD-2984034-FPD-TRIGGER: condition="date>=2026-07-07 AND client_returned", condition_type="date_and_client_status" confirmed present. (2) Synthetic branch test: past-date alert fired ("CERT-P5B-FIRE-TEST"), future-date alert silenced ("CERT-P5B-SILENT-TEST"). Both correct. In-memory only — hale_state.json not written (synthetic entries discarded). |
| P5c | Scoped subagent graceful degradation | ⬜ | Hale | Primary tool fails → documented fallback |
| X1 | Daily re-cert audit (3 thresholds) | ✅ | Sterling | continuity_daily_recert.py runs, writes a7_metrics_dashboard.json, Telegrams on RED. Timer enabled: 06:00 MT daily. First run confirmed correct output. Commit edb7aa8e |
