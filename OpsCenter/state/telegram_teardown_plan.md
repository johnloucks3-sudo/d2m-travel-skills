# Telegram Teardown Plan — Read-Only Assessment
**Prepared:** 2026-07-30 20:58 MT · Read-only investigation. No units disabled, nothing deleted, no source modified.

---

## 0. CORRECTION TO THE TASK PREMISE — READ THIS FIRST

The brief states Telegram "is DEAD — d2m-telegram.service is inactive, the bot is not
running." That is only half true. There are **two separate Telegram bot processes** in
this repo and they are in opposite states:

| Unit | Role | State | Ground truth |
|---|---|---|---|
| `d2m-telegram.service` | Legacy "COS + Dani, 145 tools" bot (`thunderbird_telegram.py`) | disabled / inactive | Confirmed dead. |
| `thunderbird-telegram-gw.service` | Current gateway — **D2MC2C (P0 C2) + Dani + Relay** (`OpsCenter/thunderbird_telegram_gw.py`) | **enabled / active (running)** | **PID 2024, up 7h56m at time of writing.** Processed real Commander messages as recently as **12:26 MT today** ("Get RID of thei farewatch message...", "Make the return May 30th...", "It's skybirdtravel.com..."). One `sendUpdates` API "Conflict" warning at 18:04 (a single transient event, not a recurring double-poll — only one Telegram process is running per `ps aux`), otherwise healthy poll loop. |

**Telegram is not dead. The legacy bot is dead; the live gateway that actually carries
Commander↔Hale traffic is up and was in use a few hours ago.** If Slack has genuinely
replaced it as C2, nobody has told `thunderbird-telegram-gw.service` — it's still armed
and answering. Teardown of "Telegram" needs to name *which* process it means. Tearing
down `d2m-telegram.service` costs nothing (already dead). Tearing down
`thunderbird-telegram-gw.service` turns off a channel that was in active two-way use
today — confirm with the Commander before that step, don't fold it silently into a
"dead code cleanup."

---

## 1. Systemd unit inventory (Telegram-related)

| Unit | Enabled | Active | Notes |
|---|---|---|---|
| `thunderbird-telegram-gw.service` | **enabled** | **active (running)** | The live gateway. PID 2024, started 12:58 MT today. Handles D2MC2C/P0-C2, Dani (client), and OC↔CC Relay in one process, 3 poll threads. |
| `thunderbird-telegram-health.timer` | **enabled** | **active** | Fires every 60s. See §4 — false-green. |
| `thunderbird-telegram-health.service` | static (triggered by timer) | inactive between runs | `core/monitoring/telegram_bot_healthcheck.py` |
| `d2m-telegram.service` | disabled | inactive | Legacy bot. Confirmed dead, matches the brief. |
| `goose-telegram.service` | disabled | inactive | |
| `thunderbird-telegram-c2.service` | disabled | inactive | |
| `d2m-brief-telegram.service` / `.timer` | disabled/static | inactive | |
| `d2m-intel-telegram.service` / `.timer` | disabled/static | inactive | |

`.env` also carries a second bot token (`TELEGRAM_CHANNELS_BOT_TOKEN`, the "Dani" bot)
that `thunderbird-telegram-gw.service` also polls — same liveness story as above.

---

## 2. File classification — 127 unique files, 133 send call-sites

(`tests/no_direct_sends_baseline.json["telegram"]` has 133 line entries; 127 distinct
files, since a few files call Telegram from more than one place.)

**LIVE** — reachable today from an *enabled* systemd unit (service enabled, or its
matching `.timer` enabled): **47**
**DORMANT** — a matching unit exists but is disabled: **29**
**DEAD** — no systemd unit anywhere references the file: **51**

Methodology caveat: classification is by systemd `ExecStart` basename match (service
name, and service-name↔timer-name convention). It does **not** catch cron, manual
invocation, or import-only reachability. One correction found by checking imports:
`OpsCenter/task_processor.py` (LIVE, via `thunderbird-overwatch.service`) imports
`core/communication/thunderbird_telegram.py` — which I'd classified DORMANT because
its own standalone unit (`d2m-telegram.service`) is dead. **Reclassify
`core/communication/thunderbird_telegram.py` as LIVE-via-import.** I did not do a full
import-graph sweep of the other 50 DEAD files for the same pattern — treat DEAD as
"no direct unit trigger found," not "provably unreachable," before deleting any of
them.

<details>
<summary>LIVE (47) — full list</summary>

```
OpsCenter/dispatcher.py
OpsCenter/hale_incident_router.py
OpsCenter/red_star_scanner.py
OpsCenter/slot_router/dispatcher.py
OpsCenter/task_processor.py
OpsCenter/thunderbird_coo_watchdog.py
api/thunderbird_power_harvest.py
backups/continuity_rollback_20260610_2200/thunderbird_coo_watchdog.py
core/booking/thunderbird_booking_monitor.py
core/dossier/dossier_validation_sweep.py
core/intel/thunderbird_incubator.py
core/lifecycle/lifecycle_scheduler.py
core/ops/lead_receiver.py
core/ops/supplier_rate_drift.py
core/ops/thunderbird_ai_metrics_dashboard.py
core/ops/touchpoint_execute.py
core/scheduling/thunderbird_scheduler.py
core/visual_synthesis/dashboard_app/server.py
core/watchtower/thunderbird_backup_verify.py
scripts/anti_theater_audit.py
scripts/blackboard_conflict_resolver.py
scripts/commander_context_restore.py
scripts/commission_watch.py
scripts/continuity_daily_recert.py
scripts/credential_expiry_forecast.py
scripts/cruise_excursion_scan.py
scripts/cruise_quote_scanner.py
scripts/dembe_intel_sweep.py
scripts/disk_pressure.py
scripts/dossier_freshness.py
scripts/fare_watch_alert.py
scripts/fdp_reconcile.py
scripts/fetch_perx_sailings.py
scripts/fetch_vtg_ticker.py
scripts/hale_decision_log_rollup.py
scripts/lessons_implementation_tracker.py
scripts/loucks_united_hard_alert.py
scripts/mission_board_promoter.py
scripts/perx_intel_monitor.py
scripts/poe_points_check.py
scripts/post_trip_followup.py
scripts/preflight_gate.py
scripts/supplier_promo_scan.py
scripts/supplier_rate_drift.py
scripts/tool_trim_audit.py
scripts/touchpoint_execute.py
scripts/weather_disruption_monitor.py
core/communication/thunderbird_telegram.py   (reclassified — see caveat above)
```
</details>

<details>
<summary>DORMANT (29) — full list</summary>

```
OpsCenter/harlan_cost_monitor.py
OpsCenter/loucks_guinea_pig_notifier.py
OpsCenter/opscenter_test_harness.py
OpsCenter/wing_heartbeat.py
agents/thunderbird_morning_briefing.py
agents/thunderbird_star_protocol.py
api/thunderbird_preflight.py
core/booking/thunderbird_pdf_ingest.py
core/communication/telegram_c2.py
core/communication/thunderbird_brief_telegram.py
core/email/thunderbird_dani_email.py
core/email/thunderbird_inbox_cleanup_daily.py
core/intel/thunderbird_intel_digest.py
core/intel/thunderbird_intel_telegram.py
core/ops/thunderbird_usage_monitor.py
core/watchtower/fpd_alert.py
core/watchtower/thunderbird_fpd_alert.py
intel/thunderbird_zfold_test.py
ops/commander_updates_enhanced.py
scripts/airline_schedule_monitor.py
scripts/centrav_session_warm.py
scripts/daily_mission_executor.py
scripts/fare_watch_amadeus.py
scripts/portal_keepalive.py
scripts/portal_live_probe.py
scripts/silversea_cookie_refresh.py
scripts/systemd_alert_send.py
scripts/timer_self_audit.py
```
</details>

<details>
<summary>DEAD (51) — full list</summary>

```
OpsCenter/_retired/pinecone_ingest.py
OpsCenter/claude_code_audit.py
OpsCenter/hale_handshake.py
OpsCenter/hale_scan_wrapper.py
OpsCenter/hale_telegram_reporter.py
OpsCenter/master_system_audit.py
OpsCenter/mission_health_check.py
OpsCenter/nexus.py
OpsCenter/persona_task_watcher.py
OpsCenter/priority3_lifecycle.py
OpsCenter/priority4_visuals.py
OpsCenter/relay_send.py
OpsCenter/safe_cli_gate.py
OpsCenter/spsa_telegram_c2.py
OpsCenter/telegram_async_agent.py
OpsCenter/telegram_health_check.py
agents/thunderbird_channels_server.py
agents/thunderbird_payment_alerts.py
api/thunderbird_outside_agents.py
app/lead_pipeline.py
core/ai_infra/thunderbird_switchblade.py
core/booking/thunderbird_concierge_monitor.py
core/client/thunderbird_followup_reminders.py
core/comms/wing_page.py
core/communication/thunderbird_sms.py
core/communication/thunderbird_sms_monitor.py
core/email/thunderbird_commander_inbox.py
core/email/thunderbird_gmail.py
core/intel/thunderbird_fb_cruise_digest.py
core/ops/confirmed_auto_execute.py
core/ops/hale_tier_staging_engine.py
core/ops/thunderbird_credential_health.py
core/ops/thunderbird_oauth_self_heal.py
core/ops/thunderbird_rate_limit_guard.py
core/watchtower/git_commit_alert.py
intel/daily_search/elon_adopt_pipeline.py
intel/daily_search/elon_daily_synthesis.py
scripts/amadeus_fare_watch.py
scripts/centrav_session_relogin.py
scripts/check_deps.py
scripts/competitive_intel_weekly_scan.py
scripts/dani_grace_persona_test.py
scripts/fare_watch_centrav.py
scripts/fare_watch_cruise_scanner.py
scripts/fare_watch_deadman.py
scripts/fare_watch_failover_poll.py
scripts/inbox_executor.py
scripts/loucks_excursion_watch.py
scripts/tess_fare_watch_autoregister.py
scripts/trinity_monitor.py
scripts/web_lead_draft_worker.py
```
</details>

---

## 3. SAFETY-CRITICAL — WOULD BREAK IF TELEGRAM WERE TORN DOWN

`core/comms/emergency_text_notify.py` and `core/comms/wing_sms.py` do **not** chain
through Telegram at all — no reference to it in either file. They are SMS-only paths
and are unaffected by any Telegram change.

**The real exposure is the opposite direction.** `core/comms/commander_channel.py`
(dated 2026-07-29, "THE SINGLE OUTBOUND GATE TO THE COMMANDER," written in response to
duplicate FPD alerts landing 13 minutes apart) is the sanctioned `notify()` API. Its
`_deliver()` transports are **Email (authoritative) + Slack (additive)** — no Telegram
branch exists in the canonical path at all. Its own docstring says: *"Before this
module, 44 files called `messages().send()` directly and 140 could send Telegram.
Exactly 2 used the canonical sender."* That migration has clearly not reached most of
the fleet yet.

I spot-checked the 17 LIVE files whose names suggest money, credentials, or
client-critical dates. **15 of 17 call `https://api.telegram.org/bot{token}/sendMessage`
directly via raw `urllib.request`, with zero alternate channel (no `notify()`, no
`commander_channel`, no `wing_sms`, no `send_wing_email`, no Slack) and the send is
wrapped in a bare try/except that only does `logging.warning()` on failure** — no
retry, no raise, no fallback:

```
scripts/credential_expiry_forecast.py    TELEGRAM-ONLY  (credential expiry — safety-critical)
scripts/fdp_reconcile.py                 TELEGRAM-ONLY  (money — First Payment Deposit reconcile)
core/watchtower/thunderbird_backup_verify.py   TELEGRAM-ONLY  (backup verification)
scripts/loucks_united_hard_alert.py      TELEGRAM-ONLY  (client-critical airline alert)
scripts/fare_watch_alert.py              TELEGRAM-ONLY
scripts/commission_watch.py              TELEGRAM-ONLY  (money)
core/ops/supplier_rate_drift.py          TELEGRAM-ONLY
scripts/dossier_freshness.py             TELEGRAM-ONLY
scripts/post_trip_followup.py            TELEGRAM-ONLY
scripts/weather_disruption_monitor.py    TELEGRAM-ONLY  (client-critical)
scripts/cruise_excursion_scan.py         TELEGRAM-ONLY
core/booking/thunderbird_booking_monitor.py    TELEGRAM-ONLY
OpsCenter/hale_incident_router.py        TELEGRAM-ONLY  (system-down escalation)
OpsCenter/thunderbird_coo_watchdog.py    TELEGRAM-ONLY  (system-down watchdog)
core/dossier/dossier_validation_sweep.py TELEGRAM-ONLY
```
The 2 exceptions checked (`OpsCenter/red_star_scanner.py`,
`core/lifecycle/lifecycle_scheduler.py`) do have a real Gmail path alongside Telegram.

**What "tear down Telegram" would mean for these 15:** the push side (`sendMessage`)
doesn't depend on `thunderbird-telegram-gw.service` being up — it's a direct outbound
POST using the bot token, independent of any local process. So these don't break from
stopping the gateway service. They **do** break, silently, if the bot token is revoked
or `.env` entries are pulled as part of "decommissioning Telegram" — and because none
of them raise on failure, nothing will page anyone when `fdp_reconcile.py` or
`credential_expiry_forecast.py` goes quiet. **These 15 must be migrated to
`commander_channel.notify()` (or at minimum given an email fallback) before any token
revocation or credential removal step** — not after.

I did not exhaustively check the other 32 LIVE files or the 29 DORMANT + 51 DEAD files
for the same pattern; the 15 above are the ones whose names imply money/safety
consequences and were verified. A full sweep for `api.telegram.org` + bare except with
no alt channel across all 127 files is the natural next investigation before deletion.

---

## 4. ROOT CAUSE — the false-green health check

`thunderbird-telegram-health.timer` (enabled, fires every 60s) triggers
`thunderbird-telegram-health.service` (oneshot) → runs
`core/monitoring/telegram_bot_healthcheck.py`.

That script does exactly one thing per bot: call Telegram's own `getMe` REST endpoint
with the bot token from `.env`, and report `LIVE` if Telegram's servers say the token
is valid. **It never once checks a local systemd unit, a local process, a PID file, a
log heartbeat, or anything else that would tell it whether *our* listener
(`d2m-telegram.service` or `thunderbird-telegram-gw.service`) is actually running.**
`getMe` answers "does this bot account exist and is the token not revoked" — a
property of Telegram's servers, not ours. A bot token stays valid indefinitely
regardless of whether any of our processes ever poll it. That's why the health check
reported green the entire time `d2m-telegram.service` sat disabled: it was never
looking at `d2m-telegram.service` in the first place. It's not "watching the timer
instead of the service" (the brief's hypothesis) — it's watching a **third-party
credential-validity signal** instead of any local liveness signal at all. The result
(`wing_health.telegram_bots` in `hale_state.json`) says LIVE/DEAD per bot token, and
nothing downstream can distinguish "our gateway is actually polling and answering" from
"the token still works."

**Same-shape check across other health/watchdog timers** — I sampled 7 others:

| Unit | Checks local process/service? | Pattern |
|---|---|---|
| `thunderbird-watchdog.service` (`opscenter_watchdog.py`) | **Yes** — calls `systemctl --user is-active` per named unit and can `restart`/`reset-failed` | Correct pattern. |
| `qdrant-watchdog.service` | Partial — probes `localhost:<qdrant-port>` directly | Correlates with local liveness (unreachable port ⇒ container down), even though it isn't a `systemctl` check. Reasonable. |
| `hale-credential-check.service` | No API/service probe found in the paths grepped | Different domain (OAuth token files), not directly comparable. |
| `router-health-daemon.service`, `thunderbird-canary-monitor.service`, `thunderbird-oversight-canary.service`, `thunderbird-restart-flap-detector.service` | Not checked in depth (time-boxed) | Flag for a follow-up sweep — the same remote-API-as-proxy-for-local-liveness flaw is worth ruling out on any watchdog that calls out to a third-party endpoint rather than `systemctl is-active`. |

**Bottom line:** `telegram_bot_healthcheck.py` is the one confirmed instance of the
flaw; `opscenter_watchdog.py` shows the correct pattern already exists elsewhere in
the codebase, so fixing telegram's health check means matching that pattern
(`systemctl --user is-active thunderbird-telegram-gw.service`) rather than inventing a
new mechanism. I did not have time to fully audit the other four listed above — treat
them as unresolved, not clean.

---

## 5. Recommended phased teardown order

**Phase 0 — before touching anything (this order, not parallel):**
1. Confirm with the Commander whether "tear down Telegram" means the dead
   `d2m-telegram.service` only, or also the **live**
   `thunderbird-telegram-gw.service` that answered a message 8 hours ago. These are
   different blast radii.
2. Migrate the 15 TELEGRAM-ONLY safety/financial scripts (§3) onto
   `commander_channel.notify()` (or give them a minimal email fallback) and verify one
   real alert lands in the inbox from each before removing any Telegram credential.
3. Fix `core/monitoring/telegram_bot_healthcheck.py` to check
   `systemctl --user is-active thunderbird-telegram-gw.service` (mirroring
   `opscenter_watchdog.py`'s pattern) instead of — or in addition to — `getMe`, so the
   dashboard stops reporting green for a dead listener. Do this whether or not the
   rest of the teardown proceeds; it's a standalone bug fix.

**Phase 1 — zero-risk cleanup (no live dependents):**
- Disable/remove the already-dead legacy units: `d2m-telegram.service`,
  `goose-telegram.service`, `thunderbird-telegram-c2.service`,
  `d2m-brief-telegram.service/.timer`, `d2m-intel-telegram.service/.timer`.
- Retire the 51 DEAD-classified files (after a spot-check for import-only reachability
  like the `thunderbird_telegram.py` case in §2 — don't assume DEAD means safe without
  that check).

**Phase 2 — DORMANT cleanup:**
- The 29 DORMANT files' units are already disabled; removing the files removes no
  running capability. Still worth a second look at `core/watchtower/fpd_alert.py` /
  `thunderbird_fpd_alert.py` — same "FPD" (deposit) domain as the LIVE
  `fdp_reconcile.py` in §3; confirm nothing re-enables these before deleting.

**Phase 3 — the live gateway, only after Phase 0 step 1 is answered:**
- If the decision is "yes, fully retire Telegram": stop and disable
  `thunderbird-telegram-gw.service` and `thunderbird-telegram-health.timer`, revoke
  `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHANNELS_BOT_TOKEN` last (only after Phase 0 step 2
  is verified done — revoking the token is what actually silences the 15 TELEGRAM-ONLY
  scripts).
- If the decision is "Slack is primary but Telegram stays as a live backup channel for
  now": leave `thunderbird-telegram-gw.service` running, do Phases 0–2 only, and just
  fix the health check (Phase 0 step 3).

**Reclassify note for the LIVE-via-import file:** `core/communication/thunderbird_telegram.py`
is reachable through `OpsCenter/task_processor.py` (LIVE) even though its own unit is
dead — don't remove it as part of Phase 1/2 without checking `task_processor.py`'s call
path first.
