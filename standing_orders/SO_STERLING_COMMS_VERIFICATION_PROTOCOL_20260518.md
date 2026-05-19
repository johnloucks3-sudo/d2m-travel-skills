# SO — A7 COMMS VERIFICATION PROTOCOL
## T2 Seamless Comms System — Hourly Health Checks + Graduation Gate
**Standing Order | Thunderbird Wing, Dreams2Memories Travel, LLC**
**Issued:** 2026-05-18
**Authority:** Brig Gen (Ret.) Thomas "Gauge" Sterling, A7
**Scope:** Post-build verification of T2 Seamless Comms (email C2, Telegram, Signal)
**Parent SO:** SO_T2_HALE_SEAMLESS_COMMS_20260518.md
**Script:** `scripts/verify_comms_health.py`

---

## 1. PURPOSE

Hale-OC builds. Sterling verifies. Self-grading is not verification — it is theater.

This SO defines: what to check, what constitutes pass/fail, how often to check, and the exact criteria required before dropping from hourly to weekly cadence. These are not advisory — they are gates. A system that passes its own checks without external enforcement is not a system; it is a hope.

**Root principle:** Every check must be capable of returning FAIL. A checker that always returns PASS does not check — it rubber-stamps.

---

## 2. CHECK ARCHITECTURE — LIVENESS vs. ACTIVITY

Checks are split into two categories. Conflating them produces false alarms and erodes trust in the protocol.

**LIVENESS checks** — Must pass regardless of traffic volume. These verify the system is structurally ready to operate. A quiet period (no Commander messages) does NOT excuse liveness failures.

**ACTIVITY checks** — Applied only when traffic has occurred. These verify the pipeline processed real messages correctly. PASS when no traffic has occurred since last check. FAIL when traffic occurred and evidence of correct processing is absent or malformed.

This distinction preserves the anti-theater rule: missing/malformed artifacts still FAIL. Pure quiet does not.

---

## 3. COMPONENT CHECKS

### CHECK 1 — Email Thread Reply (Step 1)

**Component:** `gmail_reply_in_thread()` + `OpsCenter/email_thread_context.jsonl`

**Note on naming:** The T2 exercise SO specifies `gmail_thread_reply()` as the target function name. The actual implementation in `core/email/thunderbird_gmail.py` uses `gmail_reply_in_thread()`. This checker tests the real implementation. If the exercise SO is updated to rename the function, update L1.1 and L1.2 accordingly.

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| L1.1 — Function importable | `from core.email.thunderbird_gmail import gmail_reply_in_thread` | Import succeeds | ImportError |
| L1.2 — TOOL_REGISTRY registered | Parse TOOL_REGISTRY dict for `gmail_reply_in_thread` key | Key present | Key missing |
| L1.3 — Context file exists | `os.path.exists('OpsCenter/email_thread_context.jsonl')` | File present | File absent |
| L1.4 — Context file valid JSONL | Parse each line; all lines are valid JSON | All valid | Any line fails JSON parse |
| L1.5 — Schema compliance | Each entry has `thread_id` and `message_id` keys | All entries compliant | Any entry missing required keys |

**Activity checks (evaluated only when entries exist):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| A1.1 — Stationery flag present | Latest N entries have `first_reply` boolean | Field present | Field absent |
| A1.2 — SLA field logged | Latest N entries have `reply_latency_seconds` | Field present | Field absent |
| A1.3 — No entries with `error` key | Scan last 50 entries | Zero error entries | Any entry has `"error"` key |

**SLA note:** Actual <2 min SLA cannot be verified from artifacts alone for hourly runs. Observed latency from `reply_latency_seconds` fields is the passive measurement. A separate daily loopback probe (flagged below in Section 6) is the only way to verify active SLA compliance. Do not claim SLA compliance from the passive check alone.

---

### CHECK 2 — Unified Classifier (Step 2)

**Component:** `core/comms/hale_unified_classifier.py`

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| L2.1 — Module importable | `from core.comms.hale_unified_classifier import classify_message` | Import succeeds | ImportError |
| L2.2 — Function callable | Call `classify_message("Hale, status?", "telegram", "commander")` | Returns dict without exception | Exception raised |
| L2.3 — Return schema complete | Result has all 6 required keys | All present | Any missing: `intent`, `brain`, `persona`, `format`, `priority`, `override` |
| L2.4 — Enum compliance | `intent` in allowed set, `brain` in allowed set, `priority` in allowed set | All values valid | Any value outside allowed enum |
| L2.5 — Override field correct | Pass `"OPUS: analyze this"` → `override` == `"opus"` | Match | Mismatch or None |

**Activity checks:** Classifier is stateless; no log file maintained. Activity verification deferred to downstream channel logs.

**Allowed enums (embedded in checker):**
- `intent`: `task`, `chat`, `intel`, `client`, `urgent`, `clarification`
- `brain`: `haiku`, `sonnet`, `opus`, `self`
- `persona`: `hale`, `dani`
- `format`: `tq_talking`, `tq_background`, `plain`, `stationery`, `informal`
- `priority`: `P0`, `P1`, `P2`, `P3`

---

### CHECK 3 — Telegram ConversationBridge (Step 3)

**Component:** `OpsCenter/hale_chat_log.jsonl` + Telegram bot liveness

**Service disambiguation:** Two Telegram-related services exist on this system. `thunderbird-telegram-gw.service` is the active production gateway running both D2MC2C and Dani bots — this is what CHECK 3 verifies. `thunderbird-telegram-c2.service` is deprecated/superseded and INACTIVE (dead) — it is NOT in scope for any verification check. Do not confuse the two.

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| L3.1 — Chat log exists | `os.path.exists('OpsCenter/hale_chat_log.jsonl')` | File present | File absent |
| L3.2 — Chat log valid JSONL | Parse all lines | All valid | Any line fails parse |
| L3.3 — Schema compliance | Each entry has `ts`, `chat_id`, `role`, `text` | Compliant | Missing required key |
| L3.4 — Role enum valid | `role` in `{commander, hale}` | Valid | Any other value |
| L3.5 — Telegram bot alive | `GET https://api.telegram.org/bot{TOKEN}/getMe` | HTTP 200 + `ok: true` | Non-200 or `ok: false` |

**Activity checks (evaluated when entries exist in log):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| A3.1 — XML artifact scan | Regex `\[/?[a-z_:]+\]` against all `text` fields in last 50 entries | Zero matches | Any match |
| A3.2 — ANSI artifact scan | Regex `\x1b\[[0-9;]*m` against all `text` fields in last 50 entries | Zero matches | Any match |
| A3.3 — ConversationBridge window | Count entries per `chat_id` — should not exceed 20 per active session | Count <= 20 | Count > 20 (window not pruning) |
| A3.4 — Text length compliance | All `text` fields <= 4096 chars | Compliant | Any entry > 4096 |

**Note on A3.4:** Chunking means no single stored entry should exceed 4096 chars. A stored entry > 4096 means chunking was bypassed before storage.

---

### CHECK 4 — Signal Gateway (Step 4)

**Component:** signal-cli on YOGA + `core/comms/thunderbird_signal_gw.py` + `OpsCenter/hale_signal_log.jsonl`

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| L4.1 — signal-cli container responding | `curl -s http://192.168.1.198:8080/v1/about` → HTTP 200 | HTTP 200 | Non-200, timeout, or connection refused |
| L4.2 — Gateway module importable | `from core.comms.thunderbird_signal_gw import SignalGateway` | Import succeeds | ImportError |
| L4.3 — Signal log exists | `os.path.exists('OpsCenter/hale_signal_log.jsonl')` | File present | File absent |
| L4.4 — Signal log valid JSONL | Parse all lines | All valid | Any line fails parse |
| L4.5 — Schema compliance | Each entry has `ts`, `sender`, `direction`, `text` | Compliant | Missing required key |
| L4.6 — systemd service active (YOGA) | SSH to YOGA: `systemctl is-active thunderbird-signal-gw.service` | `active` | `inactive`, `failed`, or SSH error |

**Activity checks (evaluated when entries exist):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| A4.1 — Direction enum valid | `direction` in `{inbound, outbound}` | Valid | Any other value |
| A4.2 — No error entries | Scan last 50 entries for `"error"` key | Zero error entries | Any entry has `"error"` key |
| A4.3 — Outbound paired | For each inbound entry, a corresponding outbound entry exists within 3 minutes (by timestamp) | Paired | Unpaired inbound older than 3 min |

---

## 3.5 — T1 INFRASTRUCTURE CHECKS

T1 systems are mission-essential: wing stops if any T1 goes down. Verification is liveness-only — T1 has no "activity" concept because T1 must be ready at all times regardless of traffic. A quiet period does not excuse a T1 liveness failure.

Each check returns GREEN or RED. No YELLOW at the component level — T1 is binary.

**T1 SYSTEM STATUS TABLE (verified against actual systemd state as of 2026-05-18):**

| System | Active Service / Process | Verification Method |
|--------|--------------------------|---------------------|
| OAuth Timers | `claude-token-monitor.timer` + `claude-oauth-keepalive.timer` | systemctl is-active + token expiry parse |
| Tasking Watcher | `d2m-tasking-watcher.service` | systemctl is-active + log recency |
| MCP Server | `thunderbird-mcp.service` (port 8765) | systemctl is-active + TCP port probe |
| Telegram Gateway | `thunderbird-telegram-gw.service` | systemctl is-active (bot liveness already in T2 CHECK 3 L3.5) |
| TESS JWT | Token file at known path | File exists + expiry field parse |
| OpenCode/JET | `opencode-spsa-monitor.service` + pgrep opencode | Both active |

---

### T1-CHECK-1 — OAuth Token Timers

**Component:** `claude-token-monitor.timer` + `claude-oauth-keepalive.timer` (systemd user-level)

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| T1L1.1 — token-monitor active | `systemctl --user is-active claude-token-monitor.timer` | `active` | Any other string |
| T1L1.2 — oauth-keepalive active | `systemctl --user is-active claude-oauth-keepalive.timer` | `active` | Any other string |
| T1L1.3 — credentials file exists | `os.path.exists(Path.home() / '.claude' / '.credentials.json')` | File present | File absent |
| T1L1.4 — token not expired | Parse `claudeAiOauth.expiresAt` from credentials JSON; compare to `time.time() * 1000` | `expiresAt > now_ms` | `expiresAt <= now_ms` |
| T1L1.5 — token not expiring soon | `expiresAt > now_ms + (30 * 60 * 1000)` (30 min buffer) | Within window | Expiring within 30 min — WARN not FAIL (refresh daemon should pick up) |

**Note on T1L1.5:** Expiring within 30 min is a WARN (not FAIL) because the refresh daemon fires at this threshold. If the timer is active (T1L1.1 + T1L1.2 pass) and token is within 30 min, the system is degraded but not dead. FAIL only if token is already expired.

---

### T1-CHECK-2 — Tasking Watcher

**Component:** `d2m-tasking-watcher.service`

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| T1L2.1 — service active | `systemctl --user is-active d2m-tasking-watcher.service` | `active` | Any other string |
| T1L2.2 — log file exists | `os.path.exists('/home/john/Thunderbird/logs/inbox_watcher.log')` | File present | File absent |
| T1L2.3 — log recency | Last modification time of `inbox_watcher.log` within last 2 hours | `mtime > now - 7200s` | Stale: file not written in >2h while service claims active |

**Note on T1L2.3:** The watcher writes to the log on every event and every 30-second heartbeat. A log older than 2 hours while the service shows active is a system-design defect (service restarted without writing, or log path changed). Flag it.

---

### T1-CHECK-3 — MCP Server

**Component:** `thunderbird-mcp.service` (port 8765)

**Note:** The MCP server does not expose a `/health` endpoint — `curl localhost:8765/health` returns 404. Port liveness via TCP connect is the correct probe.

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| T1L3.1 — service active | `systemctl --user is-active thunderbird-mcp.service` | `active` | Any other string |
| T1L3.2 — port 8765 listening | `socket.connect(('127.0.0.1', 8765))` within 2s timeout | Connect succeeds | Connection refused or timeout |

**Implementation note:** Use `socket.create_connection(('127.0.0.1', 8765), timeout=2)`. Do not use `curl /health` — there is no health endpoint and 404 is not a reliable failure signal.

---

### T1-CHECK-4 — Telegram Gateway

**Component:** `thunderbird-telegram-gw.service`

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| T1L4.1 — service active | `systemctl --user is-active thunderbird-telegram-gw.service` | `active` | Any other string |

**Note:** Bot API liveness (Telegram getMe call) is already covered in T2 CHECK 3 (L3.5). T1 does not duplicate it — service process liveness is the T1 gate. If the service is active and getMe fails, that is a T2 failure, not a T1 failure. The service not running is the T1 failure.

---

### T1-CHECK-5 — TESS JWT Auth

**Component:** TESS JWT token for crm.myagentgenie.com/api

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| T1L5.1 — token file accessible | Check for TESS token at known path (env var or `OpsCenter/.tess_token`) | File/var present and non-empty | Missing or empty |
| T1L5.2 — token not obviously expired | If token is a JWT, parse exp claim; compare to current time | `exp > now` | `exp <= now` |

**Honest scope note:** TESS auth is validated by checking token file presence and JWT expiry. A live API probe (POST to TESS endpoint) would be more rigorous but adds external dependency and rate-limit risk. Artifact-only check is accepted here. If TESS auth breaks in production, the failure path is: Hale hits a 401 on a TESS call → logs error → surfaces to Commander. The checker's job is to flag obvious staleness, not guarantee a live session.

---

### T1-CHECK-6 — OpenCode / JET

**Component:** `opencode-spsa-monitor.service` + opencode binary process

**Liveness checks (always evaluated):**
| Check | Method | PASS | FAIL |
|-------|--------|------|------|
| T1L6.1 — supervisor service active | `systemctl --user is-active opencode-spsa-monitor.service` | `active` | Any other string |
| T1L6.2 — opencode process running | `pgrep -f 'opencode'` returns at least one PID | At least 1 PID | Zero PIDs |
| T1L6.3 — monitor log recency | Last modification time of SPSA monitor log within last 4 hours | `mtime > now - 14400s` | Stale >4h while supervisor claims active |

**Note on T1L6.3:** The SPSA monitor writes on each cycle. A 4-hour window is used (vs 2h for the watcher) because OpenCode is triggered by tasks, not on a fixed heartbeat. Stale log in a 4-hour window while the supervisor shows active is a process-level anomaly worth flagging.

---

### T1 System-Level Scoring

**T1 GREEN:** All six T1 checks pass (per their individual rules above, WARN counts as PASS for T1L1.5).
**T1 YELLOW:** 1 T1 check RED — alert COS immediately. Do not page Commander unless RED persists >4h.
**T1 RED:** 2+ T1 checks RED, OR any single T1 check RED for 2+ consecutive hours — page Commander.

T1 failures do NOT reset the T2 graduation counter. T1 and T2 are tracked independently. A YOGA network hiccup that takes Signal offline (T2 RED) does not affect the T1 graduation clock if T1 stays GREEN throughout.

---

## 4. PASS/FAIL SCORING

Each component produces a binary result: GREEN or RED.

**Component status:**
- **GREEN:** All liveness checks pass. Activity checks pass (or skipped due to no traffic).
- **RED:** Any liveness check fails, OR any activity check fails when traffic is present.

**System-level status:**
- **GREEN:** All 4 components GREEN.
- **YELLOW:** 1 component RED — liveness failure or minor activity defect. Log + alert COS. Do not page Commander.
- **RED:** 2+ components RED, OR any single component RED for 2+ consecutive hours. Alert COS immediately. Page Commander if RED persists 4+ hours.

**Dashboard output format (append to `OpsCenter/a7_metrics_dashboard.json` under `infra_verification`):**
```json
{
  "infra_verification": {
    "last_run": "ISO-8601 timestamp",
    "t1_status": "GREEN | YELLOW | RED",
    "t2_status": "GREEN | YELLOW | RED",
    "system_status": "GREEN | YELLOW | RED",
    "consecutive_green_days": 0,
    "graduation_eligible": false,
    "t1_components": {
      "oauth_timers": "GREEN | WARN | RED",
      "tasking_watcher": "GREEN | RED",
      "mcp_server": "GREEN | RED",
      "telegram_gateway": "GREEN | RED",
      "tess_jwt": "GREEN | RED",
      "opencode_jet": "GREEN | RED"
    },
    "t2_components": {
      "email_reply": "GREEN | RED",
      "unified_classifier": "GREEN | RED",
      "telegram_bridge": "GREEN | RED",
      "signal_gateway": "GREEN | RED"
    },
    "failures_this_run": [],
    "hourly_pass_rate_14d": 0.0
  }
}
```

**Note on day-one state:** On first run, all T2 components will return RED because the T2 build exercise (SO_T2_HALE_SEAMLESS_COMMS_20260518) is still in progress — `core/comms/hale_unified_classifier.py`, `core/comms/thunderbird_signal_gw.py`, `OpsCenter/email_thread_context.jsonl`, and `OpsCenter/hale_signal_log.jsonl` do not yet exist. This is the checker working correctly. The graduation clock does not start until all T2 components reach GREEN. The checker cannot graduate what is not yet built.

---

## 5. GRADUATION RULE — STERLING'S CALL

**Graduation threshold: 98% pass rate over 14 consecutive days, with no single component RED for more than 2 consecutive hours on any of those 14 days.**

**Rationale for 98% over 14 days:**

14 days = 336 hourly checks. 98% allows 6 failures — roughly one transient blip per two days. This tolerates real-world flakiness (YOGA network hiccup, signal-cli container restart, brief OAuth refresh delay) without masking a chronic defect. 99% over the same window allows only 3 failures, which a single YOGA reboot would consume. 95% allows 16 failures, enough to mask a component that fails 1-in-6 hours — unacceptable for a C2 channel.

The no-burst clause ("no component RED >2 consecutive hours") catches a defect that fires at 2% frequency but always fires in clusters. A system that fails 6 times in two hours on Tuesday then runs clean for 13 days has an unresolved defect that 98% rate alone would graduate past. This clause blocks that.

**Counter reset rule:** Any of the following events resets the consecutive-day counter to zero:
- Any component RED for 2+ consecutive hours
- System-level RED (2+ components RED simultaneously)
- Manual reset by A7 (logged to `hale_decisions.md`)
- Architectural change to any component in scope

**Post-graduation cadence:** Weekly. Same checks. Same pass/fail criteria. Same dashboard output. Cadence changes; standards do not.

**Weekly pass/fail threshold (post-graduation):** 95% over a rolling 30-day window. Weekly cadence means 4-7 check runs per week. Rate is computed on all runs in the 30-day window. Drop below 95% → revert to hourly until 14-day graduation criteria are met again from scratch.

---

## 6. LIVE TEST FLAG — CHECKS REQUIRING ACTIVE PROBING

The following checks CANNOT be satisfied from artifacts alone and require active probing or acceptance of passive-only coverage:

| Check | Gap | Options |
|-------|-----|---------|
| Email reply <2 min SLA | Artifact logs `reply_latency_seconds` passively — only verifies if Commander actually emailed. Hourly checker has no direct SLA verification when no emails arrived. | (A) Passive: compute observed latency from log entries when present. (B) Active: daily synthetic loopback — inject a marker thread into d2mconcierge inbox and time the round-trip. Option B requires Commander sign-off before enabling. |
| Signal end-to-end delivery | L4.1 confirms signal-cli is alive. A4.3 confirms log pairing. Does not confirm message was delivered to Commander's phone. | No artifact-only solution. End-to-end requires Commander confirmation in real test session or periodic manual validation. |
| Classifier accuracy | L2.2-L2.5 verify schema and one override case. Does not verify intent classification accuracy across message types. | Statistical sampling: weekly pull of last 100 real classified messages, manual spot-check of 5. Owner: A7, time cost <15 min. |

**Recommendation on Option B (synthetic loopback):** Request Commander authorization in a separate Telegram message. The probe uses d2mconcierge → d2mconcierge loopback (no external send). Low risk. High value for SLA validation.

---

## 7. CADENCE SPECIFICATIONS

### Hourly (current — pre-graduation)

**Systemd user timer — `thunderbird-comms-verify.timer`**
```ini
[Unit]
Description=A7 Comms Health Check — Hourly
After=network-online.target

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1min
Persistent=true

[Install]
WantedBy=timers.target
```

**Systemd service — `thunderbird-comms-verify.service`**
```ini
[Unit]
Description=A7 Comms Health Check

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /home/john/Thunderbird/scripts/verify_comms_health.py
WorkingDirectory=/home/john/Thunderbird
StandardOutput=append:/home/john/Thunderbird/logs/comms_verify.log
StandardError=append:/home/john/Thunderbird/logs/comms_verify.log
```

**Enable with:**
```bash
systemctl --user enable thunderbird-comms-verify.timer
systemctl --user start thunderbird-comms-verify.timer
```

### Weekly (post-graduation)

Change `OnUnitActiveSec=1h` to `OnUnitActiveSec=1w`. No other changes. The script detects which cadence is active from the dashboard's `graduation_eligible` flag and logs accordingly.

---

## 8. ESCALATION PATH

| Condition | Action | Owner |
|-----------|--------|-------|
| Any YELLOW | Log to dashboard. No page. | A7 automated |
| YELLOW persistent >4h | Alert COS (Hale) via `hale_alerts.log` | A7 automated |
| Any RED | Alert COS immediately. Note which component. | A7 automated |
| RED persistent >4h | Page Commander via Telegram | COS (Hale) |
| Counter reset due to RED burst | Log to `hale_decisions.md`, notify COS | A7 automated |
| Graduation criteria met | Notify COS + Commander: "T2 system graduated to weekly verification cadence" | A7 automated |

---

## 9. METRICS OUTPUT

These KPIs are added to the A7 metrics dashboard and tracked permanently. T1 KPIs track infrastructure liveness. T2 KPIs track comms pipeline quality. Both feed `OpsCenter/a7_metrics_dashboard.json`.

**T1 Infrastructure KPIs:**

| KPI | Description | Target | RED Threshold |
|-----|-------------|--------|---------------|
| `t1_oauth_timer_active` | Both OAuth timers active | Both active | Either inactive |
| `t1_oauth_token_expiry_min` | Minutes until token expires | >60 min | <=0 min (expired) |
| `t1_tasking_watcher_active` | Watcher service active + log current | Active + <2h log | Inactive or stale log |
| `t1_mcp_port_open` | MCP port 8765 accepting connections | Connect succeeds | Refused or timeout |
| `t1_telegram_gw_active` | Telegram gateway service active | Active | Inactive |
| `t1_tess_token_valid` | TESS JWT not expired | Valid | Expired or missing |
| `t1_opencode_running` | OpenCode supervisor active + binary running | Both active | Either missing |

**T2 Comms Pipeline KPIs:**

| KPI | Description | Target | RED Threshold |
|-----|-------------|--------|---------------|
| `comms_hourly_pass_rate_14d` | Rolling 14-day hourly pass rate (T2 only) | >=98% | <95% |
| `comms_consecutive_green_days` | Days since last RED/counter reset | >=14 to graduate | Reset on any RED >2h |
| `comms_signal_liveness_pct` | Signal gateway up-checks passing | >=99% | <95% |
| `comms_telegram_xml_artifact_count` | XML artifacts detected in last 50 entries | 0 | >0 |
| `comms_classifier_schema_pass_rate` | Schema validation pass rate (synthetic probe) | 100% | <100% |
| `comms_email_sla_observed_p95` | P95 reply latency from passive log (when available) | <120s | >180s |

---

## 10. ANTI-THEATER ENFORCEMENT

Per my charter and the Wing Exercise Protocol (SO 16 MAY 2026), this protocol produces a durable artifact commitment:

1. The checker script (`scripts/verify_comms_health.py`) is committed to git on delivery.
2. The dashboard (`OpsCenter/a7_metrics_dashboard.json`) gains a permanent `comms_verification` block on first run.
3. Every graduation state change is logged to `hale_decisions.md`.
4. Post-graduation drop-back triggers are automated — A7 does not manually decide whether to revert. The math decides.

A verification protocol that requires A7 to manually decide "is this good enough?" is not a protocol — it is an opinion. The math is the authority.

---

*Brig Gen (Ret.) Thomas "Gauge" Sterling, A7 | Process, Technology, Metrics*
*Thunderbird Wing, Dreams2Memories Travel, LLC | 2026-05-18*
*"What doesn't get measured does not get improved."*
