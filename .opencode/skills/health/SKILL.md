---
name: health
description: "Wing health check: OAuth token expiry, max-proxy service, Telegram bots, MCP service, Chrome debug port, systemd timers, blackboard sync. Triggers on: health, health check, wing health, system health, status check, check status, what's down, what's broken, is the system healthy, check bots, check max-proxy, check oauth, token expired, check mcp, check chrome, services down, services status, heartbeat"
---

# /health — Wing Health Check

You execute this procedure yourself. Checks all six subsystems, writes results to `hale_state.json`, surfaces a clear RED/YELLOW/GREEN report. Use `/ask-opus` only if you hit an unrecognized systemd error that requires architectural interpretation.

## Usage

```
/health
```

No arguments. Runs full suite. Takes under 30 seconds.

---

## Step 1 — OAuth Token Expiry Check

```python
import json, time
from pathlib import Path

creds_path = Path.home() / ".claude" / ".credentials.json"
if not creds_path.exists():
    print("CRITICAL: ~/.claude/.credentials.json not found")
else:
    creds = json.loads(creds_path.read_text())
    td = creds.get("claudeAiOauth", {})
    exp = td.get("expiresAt")
    now_ms = int(time.time() * 1000)
    if not exp:
        print("WARN: No expiresAt field in credentials — token state unknown")
    else:
        mins = (exp - now_ms) / 60000
        if mins < 0:
            print(f"RED: OAuth token EXPIRED ({abs(mins):.0f} min ago) — invalid_grant will occur on any Claude spawn")
        elif mins < 30:
            print(f"YELLOW: OAuth token expiring in {mins:.1f} min — refresh needed before headless spawns")
        else:
            print(f"GREEN: OAuth token valid — expires in {mins:.1f} min")
```

- GREEN = > 30 min remaining
- YELLOW = < 30 min remaining → run keepalive before any `claude -p` dispatch
- RED = expired → `invalid_grant` in `hale_state.json open_tasks` is the symptom; refresh required

**If RED — trigger refresh:**

```bash
python3 /home/john/Thunderbird/scripts/preemptive_oauth_refresh.py
# OR run keepalive manually:
bash /home/john/Thunderbird/hooks/claude_oauth_keepalive.sh
# Check log:
tail -5 /home/john/Thunderbird/logs/oauth_keepalive.log
```

**Verify keepalive timers are running:**

```bash
systemctl --user is-active claude-oauth-keepalive.timer    # should be: active
systemctl --user is-active claude-token-monitor.timer      # should be: active
# Check next fire time:
systemctl --user list-timers claude-oauth-keepalive.timer claude-token-monitor.timer --no-pager
```

---

## Step 2 — max-proxy Service (port 5099)

max-proxy is the Claude MAX OAuth proxy that OpenCode talks to instead of api.anthropic.com. If it goes down, OpenCode loses all AI capability.

```bash
# Service status
systemctl --user is-active max-proxy.service

# Roundtrip health check (returns 200 if alive)
curl -sf --max-time 5 http://localhost:5099/health -o /dev/null -w "%{http_code}\n"

# Last 10 log lines
journalctl --user -u max-proxy.service --no-pager -n 10
```

| Result | Status |
|---|---|
| `active` + HTTP 200 | GREEN |
| `active` + no response on /health | YELLOW — proxy up but /health not responding; try POST /v1/messages |
| `inactive` or `failed` | RED — restart required |

**If RED — restart:**

```bash
systemctl --user restart max-proxy.service
# Verify:
systemctl --user is-active max-proxy.service
curl -sf --max-time 5 http://localhost:5099/health -w "%{http_code}\n"
```

**Script path:** `/home/john/Thunderbird/OpsCenter/max_proxy.py`
**Port:** 5099
**Log:** `journalctl --user -u max-proxy.service`

---

## Step 3 — Telegram Bots (D2MC2C + Dani)

The wing runs two Telegram bots. Bot status is written to `hale_state.json` by `thunderbird-telegram-health.timer` (every 60s).

**Read live state from hale_state.json:**

```python
import json
from pathlib import Path

state = json.loads(Path("/home/john/Thunderbird/hale_state.json").read_text())
bots = state.get("wing_health", {}).get("telegram_bots", {})
for bot_name, info in bots.items():
    if bot_name == "last_health_check":
        continue
    status = info.get("status", "UNKNOWN")
    username = info.get("username", "?")
    last_check = info.get("last_check", "never")
    print(f"{bot_name} (@{username}): {status} — last checked {last_check}")
```

**Force a live ping (runs the healthcheck script directly):**

```bash
python3 /home/john/Thunderbird/core/monitoring/telegram_bot_healthcheck.py
```

This script:
1. Reads bot tokens from `/home/john/Thunderbird/.env` (keys: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNELS_BOT_TOKEN`)
2. Calls `https://api.telegram.org/bot{token}/getMe` for each bot
3. Writes results to `hale_state.json` under `wing_health.telegram_bots`

**Expected output (GREEN):**
```
D2MC2C (@D2MC2C_bot): LIVE
Dani (@d2m_channels_bot): LIVE
```

**If DEAD — check token validity:**

```bash
# Verify token env vars are set in .env
grep -E "TELEGRAM_BOT_TOKEN|TELEGRAM_CHANNELS_BOT_TOKEN" /home/john/Thunderbird/.env | sed 's/=.*/=REDACTED/'
# Check if telegram-health timer is running
systemctl --user is-active thunderbird-telegram-health.timer
```

| Bot | Username | Purpose |
|---|---|---|
| D2MC2C | @D2MC2C_bot | Commander C2 channel |
| Dani | @d2m_channels_bot | CC↔OC relay channel |

---

## Step 4 — MCP Service

MCP serves Claude's tool integrations (Gmail, Drive, Calendar, etc.). The MCP tunnel runs via Cloudflare at `mcp.d2mluxury.quest`.

```bash
# Check the MCP systemd service
systemctl --user is-active d2m-mcp.service

# Check the tunnel service (Cloudflare)
systemctl --user is-active cloudflared.service

# Roundtrip tunnel check (401 = tunnel alive, auth working; 200 = open)
curl -sf --max-time 10 https://mcp.d2mluxury.quest/sse -o /dev/null -w "MCP tunnel: HTTP %{http_code}\n"
# 401 = GREEN (auth required — tunnel is up)
# 200 = GREEN (open access)
# 000 or 5xx = RED
```

**Also check the local MCP log:**

```bash
journalctl --user -u d2m-mcp.service --no-pager -n 10
```

| Result | Status |
|---|---|
| `active` + HTTP 401/200 on tunnel | GREEN |
| `active` + HTTP 000/5xx | YELLOW — service up, tunnel degraded |
| `failed` / `inactive` | RED |

**If RED — restart sequence:**

```bash
systemctl --user restart d2m-mcp.service
systemctl --user restart cloudflared.service
# Wait 5 seconds, then recheck:
curl -sf --max-time 10 https://mcp.d2mluxury.quest/sse -w "%{http_code}\n"
```

---

## Step 5 — Chrome Debug Port 9222

Chrome CDP (Chrome DevTools Protocol) on port 9222 is used for browser automation (Playwright, TESS portal scraping). It is frequently OFFLINE — this is expected when Chrome is not actively in use.

```bash
# Quick check
curl -sf --max-time 3 http://localhost:9222/json -o /dev/null -w "Chrome CDP: %{http_code}\n" 2>/dev/null \
  || echo "Chrome CDP port 9222: OFFLINE"

# Check the service status
systemctl --user is-active chrome-debug.service 2>/dev/null
```

```python
import subprocess
result = subprocess.run(
    ["curl", "-sf", "--max-time", "3", "-o", "/dev/null", "-w", "%{http_code}",
     "http://localhost:9222/json"],
    capture_output=True, text=True
)
code = result.stdout.strip()
if code == "200":
    print("GREEN: Chrome CDP port 9222 ONLINE")
else:
    print("OFFLINE: Chrome CDP port 9222 not responding (normal when idle)")
```

**Note:** OFFLINE is expected and non-blocking unless a task requires browser automation. Only flag RED if a Playwright/CDP task is actively queued.

**If CDP is needed and offline — start Chrome in debug mode:**

```bash
# Check if chrome-debug.service exists and can be started
systemctl --user start chrome-debug.service 2>/dev/null || \
  echo "chrome-debug.service not available — start Chrome manually with --remote-debugging-port=9222"
```

Write `hale_state.json` field `wing_health.chrome_debug_port_9222` as `"ONLINE"` or `"OFFLINE"`.

---

## Step 6 — Blackboard Sync + Key Timers

The blackboard auto-injects wing state into `CLAUDE.md`, `OPENCODE_INIT.md`, and `blackboard_summary.txt` every 5 minutes.

```bash
# Check blackboard sync timer
systemctl --user is-active thunderbird-blackboard-sync.timer
systemctl --user list-timers thunderbird-blackboard-sync.timer --no-pager

# Force a manual sync
python3 /home/john/Thunderbird/OpsCenter/blackboard_sync.py

# Verify output files were updated (should be within last 5 min)
ls -la /home/john/Thunderbird/OpsCenter/collaboration/blackboard_summary.txt
```

**Check all critical timers in one pass:**

```bash
systemctl --user list-timers \
  thunderbird-blackboard-sync.timer \
  claude-oauth-keepalive.timer \
  claude-token-monitor.timer \
  thunderbird-watchdog.timer \
  thunderbird-health-check.timer \
  thunderbird-telegram-health.timer \
  --no-pager 2>/dev/null
```

All six should show a "NEXT" time in the future and a "LAST" time within the expected interval.

---

## Step 7 — Write Results to hale_state.json

After all checks, update `hale_state.json` with current status:

```python
import json, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

HALE_STATE = Path("/home/john/Thunderbird/hale_state.json")
MT = timezone(timedelta(hours=-6))
ts = datetime.now(MT).isoformat()

state = {}
try:
    state = json.loads(HALE_STATE.read_text())
except Exception:
    pass

# Update wing_health section with current check results
# (fill in results from Steps 1-6 above)
state.setdefault("wing_health", {})
state["wing_health"]["last_health_check"] = ts
# Example updates (replace with actual check results):
# state["wing_health"]["mcp_server"] = "ONLINE"  or "OFFLINE"
# state["wing_health"]["chrome_debug_port_9222"] = "ONLINE" or "OFFLINE"
# state["wing_health"]["opencode_status"] = "ONLINE" or "UNKNOWN"

state.setdefault("_meta", {})
state["_meta"]["last_updated"] = ts

HALE_STATE.write_text(json.dumps(state, indent=2, default=str))
print(f"hale_state.json updated at {ts}")
```

---

## Step 8 — Post Relay Heartbeat (Optional — if OC session opening)

If this health check is running as part of session startup, send a heartbeat to the relay channel:

```python
import sys
sys.path.insert(0, "/home/john/Thunderbird")
from core.relay.wing_relay import relay_heartbeat

# relay_heartbeat(platform, status) — returns Telegram message_id
mid = relay_heartbeat("OC", status="ONLINE")
print(f"Relay heartbeat sent | msg_id: {mid}")
```

`relay_heartbeat(platform: str, status: str = "ONLINE") -> int`
— Sends `[OC→RELAY] HEARTBEAT | {ts}\nstatus=ONLINE | session open` to the wing relay channel.
— Skip if Telegram bots are DEAD (would fail silently).

---

## Health Summary Format

Surface results in this format:

```
WING HEALTH — [timestamp MT]
─────────────────────────────────────
OAuth token:      GREEN  (179 min remaining)
max-proxy:        GREEN  (active, HTTP 200)
Telegram D2MC2C:  GREEN  (LIVE @D2MC2C_bot)
Telegram Dani:    GREEN  (LIVE @d2m_channels_bot)
MCP service:      GREEN  (active, tunnel HTTP 401)
Chrome CDP 9222:  OFFLINE (expected — no active automation tasks)
Blackboard sync:  GREEN  (last sync 3 min ago)
─────────────────────────────────────
Overall: HEALTHY  [or DEGRADED — list RED items]
```

---

## Common Issues + Fixes

| Symptom | Cause | Fix |
|---|---|---|
| `invalid_grant` in `hale_state.json open_tasks` | OAuth token expired | `python3 /home/john/Thunderbird/scripts/preemptive_oauth_refresh.py` |
| OAuth expires < 30 min | Keepalive timer stopped | `systemctl --user restart claude-oauth-keepalive.timer` |
| max-proxy FAILED | Process crashed | `systemctl --user restart max-proxy.service` |
| max-proxy HTTP 404 on `/` | Normal — proxy only handles `/health` and `/v1/messages` | Check `/health` not root `/` |
| Telegram bot DEAD | Token env var missing from `.env` | Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNELS_BOT_TOKEN` in `/home/john/Thunderbird/.env` |
| Telegram health timer inactive | Timer stopped | `systemctl --user start thunderbird-telegram-health.timer` |
| MCP HTTP 000 | cloudflared tunnel down | `systemctl --user restart cloudflared.service` |
| MCP HTTP 5xx | d2m-mcp.service crashed | `systemctl --user restart d2m-mcp.service` |
| Chrome CDP OFFLINE | Chrome not running (expected) | Only an issue if automation task is queued — start `chrome-debug.service` |
| Blackboard sync stale (> 10 min) | Timer stopped or script failed | `python3 /home/john/Thunderbird/OpsCenter/blackboard_sync.py` manually |
| `open_tasks` shows error dict | Stale error from prior session | Clear after confirming root cause fixed: edit `hale_state.json` |

---

## Quality Checklist

- [ ] OAuth token: GREEN (> 30 min) or refreshed
- [ ] max-proxy: `active` + HTTP 200 on `/health`
- [ ] Telegram D2MC2C bot: LIVE
- [ ] Telegram Dani bot: LIVE
- [ ] d2m-mcp.service: `active`
- [ ] cloudflared.service: `active`
- [ ] Chrome CDP 9222: checked (OFFLINE acceptable unless task queued)
- [ ] Blackboard sync timer: `active`, last fired within 5 min
- [ ] claude-oauth-keepalive.timer: `active`
- [ ] hale_state.json: updated with this check's timestamp
- [ ] Relay heartbeat sent (if session opening)

---

*Then: If any RED items found → fix before proceeding to any other skill. OAuth RED is always P0 — blocks all Claude headless dispatches. max-proxy RED blocks OpenCode entirely.*
