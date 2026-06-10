🦅 **Telegram Gateway Restart Loop — Root Cause & Proposal**

**Incident Summary:**
- Service restarting 3x/day (21 crashes in 7 days)
- Cause: Exception isolation missing in message dispatch threads — when Claude spawn fails, thread crashes propagate up and cause systemd restart
- Impact: Critical comms channel (D2MC2C) degraded but masked by auto-restart

**Proposal Details:**
- **Type:** code_diff (4 targeted exception-handling patches)
- **Scope:** bot_poll_loop, handle_message, relay_poll_loop, startup health check
- **Risk:** LOW — exception handlers only add robustness
- **Verification:** Observable via logs + systemctl (no restart loop for 24h)

**Hale Decision:** `APPLY_AUTONOMOUSLY` — I've authored a complete proposal at:
```
/home/john/Thunderbird/OpsCenter/elon_proposals/PROPOSAL-20260609-thunderbird-telegram-gw.md
```

The fix is surgical (50 lines, 3 try-except blocks), low-risk isolation. Ready for Hale to implement when bandwidth allows.
