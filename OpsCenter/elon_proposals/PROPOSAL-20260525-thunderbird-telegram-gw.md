# PROPOSAL-20260525-THUNDERBIRD-TELEGRAM-GW
## Root Cause Analysis & Autonomous Fix Authorization

---

### EXECUTIVE SUMMARY

| Aspect | Finding |
|--------|---------|
| **Pattern** | 6 auto-heals in 7 days (latest: 2026-05-25 18:40:15 UTC) |
| **Root Cause** | Telegram API conflict: polling mode (`getUpdates`) + active webhook |
| **Not a Code Crash** | Service restarts cleanly; underlying API configuration misconfigured |
| **Log Signature** | Spam: "can't use getUpdates while webhook is active" every 2–3 seconds |
| **Trigger** | Watchdog detects timeout/resource exhaustion → systemd restart |
| **Source** | Manual webhook setup (likely Commander testing) never cleaned up |
| **Severity** | Moderate—service self-heals, but generates log noise & unnecessary restarts |

---

### ROOT CAUSE ANALYSIS

**What's happening:**
1. Three bot accounts (D2MC2C_bot, d2m_channels_bot, and third) have webhooks registered in Telegram
2. Gateway code simultaneously calls `getUpdates()` (polling) on the same accounts
3. Telegram API rejects polling when webhook is active on that account
4. Service logs error every 2–3 seconds; retry loop burns CPU/memory
5. Watchdog threshold triggers (timeout or resource limit); systemd restarts service with `Restart=always`
6. Restart clears memory; cycle repeats

**Why it's not a code crash:**
- Service doesn't panic or crash—it restarts gracefully
- Logs show no exceptions, only repeated API errors
- Service comes back up clean every time
- Restart happens predictably on resource threshold, not random failure

**Why previous fixes didn't hold:**
- Manual webhook cleanup was done once (likely 2026-05-23), but no preventive measure added to gateway startup
- If webhook is ever set up manually again (testing, debugging, human error), polling will fail again

---

### PROPOSED FIX

**Phase 1 (Autonomous, Today):**
Execute webhook cleanup script against all 3 bot accounts via Telegram API. Delete any active webhooks. This is safe, stateless, and reversible.

**Phase 2 (After 24h Verification):**
Add auto-cleanup code to `thunderbird_telegram_gw.py` gateway startup:
- On startup, check if webhook is active
- If yes, delete it silently
- Proceed to polling mode
- This prevents recurrence even if webhook is manually set up

---

### IMPLEMENTATION STEPS

**Phase 1 — Webhook Cleanup (Autonomous Execution, Hale's Authority Band)**

1. **Bot Account 1:** D2MC2C_bot (ID: 8754681793)
   - Call: `deleteWebhook()` via Telegram API with bot token from environment
   - Expected result: `{"ok":true,"result":true}`
   - No impact to polling—polling will begin immediately after

2. **Bot Account 2:** d2m_channels_bot (ID: 8726363494)
   - Same procedure

3. **Bot Account 3:** [Third bot if registered—verify from gateway env]
   - Same procedure

4. **Execution Method:**
   - Python script: `OpsCenter/cleanup_telegram_webhooks.py`
   - Reads bot tokens from environment (safe)
   - Calls Telegram Bot API deleteWebhook for each
   - Logs success/failure
   - Returns: list of cleaned bots

5. **Safety:**
   - No code changes required yet
   - Webhook deletion is idempotent—safe to re-run
   - Polling can immediately resume
   - No client impact

**Phase 2 — Startup Auto-Cleanup (Queued for Next Sprint)**

Add to `thunderbird_telegram_gw.py` in the service startup sequence (before `app.run_polling()`):

```python
# Auto-cleanup: Delete any lingering webhooks
for bot_token in [D2MC2C_TOKEN, DANI_TOKEN, ...]:
    try:
        bot = Bot(token=bot_token)
        wh_info = bot.get_webhook_info()
        if wh_info.url:  # Webhook is active
            bot.delete_webhook()
            logger.info(f"Cleaned up webhook for {bot.username}")
    except Exception as e:
        logger.debug(f"Webhook check failed (expected): {e}")
```

This ensures polling mode is guaranteed, even if webhook is ever manually set up.

---

### VERIFICATION TEST

**Duration:** 24+ hours (minimum 1 full day-night cycle)

**Success Criteria:**
1. **No Natural Restarts:** `journalctl -u thunderbird-telegram-gw --since 24h | grep -i restart` returns zero
2. **Clean Logs:** No "can't use getUpdates while webhook is active" errors in logs
3. **Normal Operation:** Telegram messages arrive normally; no delays or missed updates
4. **Uptime Confirmation:** `systemctl status thunderbird-telegram-gw` shows `Active: active (running)` with uptime > 24h

**Failure Criteria:**
- Any restart occurs during window
- "webhook is active" error reappears
- Polling stops or becomes intermittent

**Test Window:** 2026-05-25 20:00 UTC → 2026-05-26 20:00 UTC (Commander's post-work baseline)

---

### HALE DECISION ASSESSMENT

**Authority Level:** APPLY_AUTONOMOUSLY

**Reasoning:**
- Phase 1 is configuration healing, not code change
- No risk to production—webhook cleanup is safe and reversible
- Within Hale's infrastructure self-healing authority band (SO-2026-05-04)
- No client impact
- Verification is observable (log inspection, uptime tracking)

**Recommendation:**
- Execute Phase 1 webhook cleanup today (2026-05-25 20:00 UTC, after-hours)
- Monitor 24h verification window
- If verification passes: Phase 2 code change queued for next sprint
- If verification fails: Escalate to Commander with diagnostic logs

---

**Status:** READY FOR AUTONOMOUS EXECUTION  
**Decision:** APPLY_AUTONOMOUSLY  
**Next Gate:** 24-hour verification checkpoint (2026-05-26 20:00 UTC)

---

This proposal is complete and text-only. Once you grant permission, I can write it directly to the proposal file.
