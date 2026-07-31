# Executive Summary: OAuth Coverage Gap & Rate-Limit Guard Sonnet Alert Audit

**Date:** 2026-07-31  
**Author:** HALE-AG (Antigravity Engine)  
**Deliverable Target:** `/home/john/Thunderbird/OpsCenter/tmp_specs/deliverables/gap_sonnet_result.md`

---

## 1. Thread A: 48-Hour OAuth Coverage Gap Investigation

### Scope & Methodology
Investigated whether `thunderbird-api.service` or `thunderbird-whatsapp-webhook.service` executed headless Claude calls or spent OAuth-metered tokens over the last 48 hours (`2026-07-29 12:00 UTC` to `2026-07-31 12:42 UTC`).

### Log Inspection Results
1. **`thunderbird-api.service` Log Check:**
   - **Command Executed:**
     ```bash
     journalctl --user -u thunderbird-api.service --since "2026-07-29 12:00" -o short-iso
     journalctl --user -u thunderbird-api.service --since "2026-07-29 12:00" -o short-iso | grep -iE "SMS|claude|dispatch|Engine"
     ```
   - **Grep Output:** Exit code `1` (0 matches).
   - **Code Audit:** In `api/thunderbird_api.py`, `_dispatch_sms_ai` (lines 1752–1850) is invoked asynchronously only when the `/sms/inbound` FastAPI route receives a request. When invoked, it executes `subprocess.run(["/home/john/.local/bin/claude", ...])` and logs `SMS AI reply sent to...`, `SMS Claude timeout for...`, or `SMS AI dispatch error...`.
   - **Log Finding:** Over the 48-hour window, zero requests touched `/sms/inbound`. Journal logs contain only standard FastAPI/MCP OpenAPI docs GET requests and unauthorized background probe requests. Zero headless Claude instances were dispatched.

2. **`thunderbird-whatsapp-webhook.service` Log Check:**
   - **Command Executed:**
     ```bash
     journalctl --user -u thunderbird-whatsapp-webhook.service --since "2026-07-29 12:00" -o short-iso
     ```
   - **Log Output:**
     ```text
     2026-07-29T12:29:53-06:00 yoga systemd[1528]: Starting Thunderbird WhatsApp Webhook — Commander inbound via wa.d2mluxury.quest...
     2026-07-29T12:29:57-06:00 yoga systemd[1528]: Started Thunderbird WhatsApp Webhook — Commander inbound via wa.d2mluxury.quest.
     -- Boot 31500af6caba493184e11afd16cc9b26 --
     2026-07-29T12:42:35-06:00 yoga systemd[1510]: Starting Thunderbird WhatsApp Webhook — Commander inbound via wa.d2mluxury.quest...
     2026-07-29T12:42:41-06:00 yoga systemd[1510]: Started Thunderbird WhatsApp Webhook — Commander inbound via wa.d2mluxury.quest.
     -- Boot 507318354e83493dbe37b9a5be09fe41 --
     2026-07-30T12:58:15-06:00 yoga systemd[1520]: Starting Thunderbird WhatsApp Webhook — Commander inbound via wa.d2mluxury.quest...
     2026-07-30T12:58:20-06:00 yoga systemd[1520]: Started Thunderbird WhatsApp Webhook — Commander inbound via wa.d2mluxury.quest.
     ```
   - **Code Audit:** In `OpsCenter/whatsapp_webhook.py`, `hale_claude_engine` (lines 91–116) executes `subprocess.run(["/home/john/.local/bin/claude", ...])` when inbound WhatsApp webhooks are received.
   - **Log Finding:** Journal output contains only systemd service startup lines across reboots. Zero webhook HTTP requests were received and zero Claude processes were executed.

### Thread A Definitive Verdict
Neither `thunderbird-api.service` nor `thunderbird-whatsapp-webhook.service` spent any OAuth-metered tokens in the last 48 hours.

---

## 2. Thread B: Rate-Limit Guard Bogus Sonnet Alert Diagnosis & Fix

### Step 3: Database & Telemetry Freshness Audit
- **Database Query Executed:**
  ```bash
  sqlite3 /home/john/Thunderbird/storage/ai_costs.db "SELECT ts, sonnet_weekly_pct FROM claude_usage_reports ORDER BY ts DESC LIMIT 10;"
  ```
- **Literal Query Output:**
  ```text
  2026-05-20T22:36:06.968625+00:00|88.0
  2026-05-20T22:19:39.125707+00:00|88.0
  2026-05-20T22:19:08.779377+00:00|88.0
  ```
- **Analysis:**
  - The newest row timestamp is `2026-05-20T22:36:06.968625+00:00` — **71 days old** (~1,718 hours).
  - Grep search across the entire repository for `INSERT.*claude_usage_reports` returned **zero matches**.
  - **Root Cause Confirmed:** No process writes to `claude_usage_reports`. `get_sonnet_weekly_pct()` had no timestamp freshness verification and unconditionally read the newest row, treating a 71-day-old frozen reading of `88.0%` as live quota telemetry.

### Step 4: Guard State Transitions & Flapping Analysis
- **State File Inspected:** `/home/john/Thunderbird/config/rate_guard_state.json`
- **Transitions Log:**
  - `2026-04-29T20:06:19Z`: `NORMAL -> ROLLBACK`
  - `2026-07-30T19:57:22Z`: `ROLLBACK -> CRIT`
  - `2026-07-31T05:35:30Z`: `CRIT -> STOP`
  - `2026-07-31T11:51:12Z`: `STOP -> CRIT`
- **Explanation:**
  At `11:51 UTC`, the 5-hour rolling usage dropped to `14.0%` (`GuardState.ROLLBACK`). However, because `_compute_target_state()` checked `sonnet_pct >= 85` (`SONNET_CRIT`) and `get_sonnet_weekly_pct()` returned the frozen `88.0%`, the Sonnet axis forced the overall target state to `CRIT`. This triggered a false state transition (`STOP -> CRIT`) and dispatched the alert to Telegram despite healthy 5-hour telemetry.

### Step 5: Telegram Feedback Loop Analysis
- **Code Audit:** Examined `OpsCenter/thunderbird_telegram_gw.py`.
- **Sender Validation Lines:**
  - Line 1884: `if bot_name in ("D2MC2C", "HaleD2M") and user_id != COMMANDER_ID: log.warning("[%s] Rejected non-Commander user_id=%d", bot_name, user_id); return`
  - Line 2382: `if user_id == COMMANDER_ID:`
  - `COMMANDER_ID` is hard-configured to `7554895206` (line 196).
- **Finding:** Telegram bot messages sent to the channel originate from the bot ID (`8754681793`). `thunderbird_telegram_gw.py` strictly drops any non-Commander sender. There is **no Telegram feedback loop**.

---

## 3. Code Fix Applied

Because the `claude_usage_reports` table data was confirmed stale (71 days old with no active writer), the fail-closed pattern was applied to `core/ops/thunderbird_rate_limit_guard.py`:

1. **Freshness Check added to `get_sonnet_weekly_pct()`:**
   - Checks row timestamp age against `datetime.now(timezone.utc)`.
   - If timestamp age > 24.0 hours, missing, or invalid, returns `None` (mirroring `get_weekly_pct()`).
2. **Updated `_compute_target_state()`:**
   - Parameter type updated to `sonnet_pct: Optional[float] = None`.
   - When `sonnet_pct is None`, `sonnet_state` evaluates to `GuardState.ROLLBACK` (neutral floor), preventing a dead sensor from forcing `CRIT` or `STOP`.
3. **Updated `_alert_message()`:**
   - When `sonnet_pct is None`, renders `Sonnet weekly: [UNKNOWN — telemetry unavailable]`.
4. **Unit Tests Added (`tests/test_rate_limit_guard_5h.py`):**
   - Added test for stale `get_sonnet_weekly_pct()` returning `None`.
   - Added test verifying `_compute_target_state(14.0, None, 14.0)` returns `GuardState.NORMAL`.

---

## 4. Mechanical Acceptance Verification

Executed all 3 mandatory acceptance commands:

```bash
git status --short api/thunderbird_api.py OpsCenter/whatsapp_webhook.py
python3 -m py_compile core/ops/thunderbird_rate_limit_guard.py
python3 -m pytest tests/test_rate_limit_guard_5h.py -q
```

### Literal Command Outputs
1. `git status --short api/thunderbird_api.py OpsCenter/whatsapp_webhook.py`:
   ```text
   (empty output — zero modifications to Thread A files)
   ```
2. `python3 -m py_compile core/ops/thunderbird_rate_limit_guard.py`:
   ```text
   (exited 0 — successful compilation)
   ```
3. `python3 -m pytest tests/test_rate_limit_guard_5h.py -q`:
   ```text
   ........                                                                 [100%]
   8 passed in 0.06s
   ```

---

## 5. Risk & Uncertainty Report

- **[Uncertainty: Low / Confidence: High]** `claude_usage_reports` table in `/home/john/Thunderbird/storage/ai_costs.db` appears to be a legacy schema artifact from May 2026. If a new usage collector is implemented in the future to write live Sonnet metrics to this table, `get_sonnet_weekly_pct()` will automatically accept readings newer than 24 hours while safely discarding stale ones.
