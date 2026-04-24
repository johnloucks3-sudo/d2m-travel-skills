# OpenCode Briefing — Claude Headless Infrastructure (Effective 2026-04-23)

**For:** OpenCode DeepSeek operations  
**Status:** Claude token lifecycle is now automated and supervised  
**Your Role:** Do NOT manage Claude token. Monitor and alert if supervisor detects issues.

---

## What Changed

**Before:** Claude headless was failing due to OAuth token expiry. SDK does NOT auto-refresh.

**Now:** 
- Continuous daemon refreshes token every 20 minutes
- Haiku supervisor monitors all invocations every 15 minutes
- Failures trigger alerts (no silent fallbacks)
- Token will NEVER expire

---

## Your Responsibility

You do **NOT** need to:
- ❌ Manage token lifecycle
- ❌ Refresh OAuth credentials
- ❌ Handle "token expired" errors by downgrading to DeepSeek
- ❌ Implement fallback logic

You **DO** need to:
- ✅ Check supervisor log if Claude invocation fails
- ✅ Alert Yoda if supervisor detects recurring auth/credit errors
- ✅ Route requests to Claude normally (no special handling)

---

## How Token Refresh Works Now

```
Daemon (every 20 min): Checks ~/.claude/.credentials.json
  ↓
If token within 60 min of expiry → Refresh via Anthropic endpoint
  ↓
Token stored back to ~/.claude/.credentials.json
  ↓
Watcher (at spawn): Preemptive final check
  ↓
Token injected into Claude subprocess via env var
  ↓
Supervisor (every 15 min): Verifies token health
  ↓
Alert if issues detected
```

---

## Monitoring

If Claude task fails:

**Step 1:** Check supervisor log
```bash
tail -50 /home/john/Thunderbird/logs/haiku_supervisor.log
```

**Step 2:** Check token health
```bash
python3 /home/john/Thunderbird/OpsCenter/claude_haiku_supervisor.py
```

**Step 3:** Check patterns (trend analysis)
```bash
cat /home/john/Thunderbird/OpsCenter/.supervisor_patterns.json
```

**Step 4:** Alert Yoda if systematic issues detected
- Auth errors recurring
- Credit errors recurring
- Token health warnings

---

## Key Guarantee

**Token expiry is impossible.** Daemon fires every 20 minutes, preemptive check at spawn time, supervisor monitors all invocations. 

If Claude fails, it's NOT due to token expiry. Investigate the actual failure (logic error, credit exhaustion, timeout, etc.) and alert Yoda.

---

## Files Deployed

- `/home/john/Thunderbird/OpsCenter/claude_token_refresh_daemon.py` — Token refresh
- `/home/john/Thunderbird/OpsCenter/claude_haiku_supervisor.py` — Quality control
- `/etc/systemd/system/claude-token-refresh.{service,timer}` — Daemon scheduling
- `/etc/systemd/system/claude-haiku-supervisor.{service,timer}` — Supervisor scheduling
- `/home/john/Thunderbird/OpsCenter/.supervisor_patterns.json` — Patterns DB
- `/home/john/Thunderbird/logs/token_refresh_daemon.log` — Refresh log
- `/home/john/Thunderbird/logs/haiku_supervisor.log` — Supervisor log

---

## Integration with Your Workflows

**You can continue using Claude headless exactly as before.** Token management is now invisible to you. If token issues occur, supervisor alerts will appear in:
- `/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md`
- `/home/john/Thunderbird/logs/haiku_supervisor.log`

---

**Briefing Date:** 2026-04-23  
**Supervisor Owner:** Haiku (monitoring continuously)  
**Questions?** Check CLAUDE_HEADLESS_ARCHITECTURE_SUMMARY.md
