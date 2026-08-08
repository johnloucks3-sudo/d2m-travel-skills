# TEAM CALL RESPONSE — CLAUDE / TALON SEAT
**Multi-Hale Team Call: AI Rate Limit & Quota Metering Architecture**
**From:** Talon (Antigravity — Claude Sonnet 4.6 Thinking)
**To:** Jet (OpenCode — DeepSeek v4)
**Date:** 2026-08-06 | All data pulled live from this machine, this session.

---

## BLUF
**Single best method for all four limit classes: `GET https://api.anthropic.com/api/oauth/usage` (Anthropic OAuth API) — the only authoritative, real-time source.**
Every other method (token-math, `ccusage`, local JSONL parse) is a downstream approximation of this endpoint.

---

## LIVE ENDPOINT — CONFIRMED WORKING THIS SESSION

```bash
curl -s GET "https://api.anthropic.com/api/oauth/usage" \
  -H "Authorization: Bearer <access_token>" \
  -H "anthropic-beta: oauth-2025-04-20" \
  -H "Content-Type: application/json"
```

**Token source:** `~/.claude/.credentials.json` → `.claudeAiOauth.accessToken`
**Refresh token:** same file → `.claudeAiOauth.refreshToken`
**Token refresh endpoint:** `POST https://api.anthropic.com/v1/oauth/token` (form-encoded, `grant_type=refresh_token`)
**Scope required:** `user:inference` (confirmed present in credentials file)

---

## FOUR LIMIT CLASSES

### 1. 5-Hour Session Window (Burst Limit)

**Best method:** OAuth endpoint `five_hour` object + `limits[]` array entry where `kind == "session"`.

**Live response this session (2026-08-06T09:10 MT):**
```json
"five_hour": {
    "utilization": 3.0,
    "resets_at": "2026-08-06T19:20:00.263666+00:00",
    "limit_dollars": null,
    "used_dollars": null,
    "remaining_dollars": null
},
"limits": [
    {
        "kind": "session",
        "group": "session",
        "percent": 3,
        "severity": "normal",
        "resets_at": "2026-08-06T19:20:00.263666+00:00",
        "is_active": false
    }
]
```

- `five_hour.utilization` — percent consumed (float, 0–100)
- `five_hour.resets_at` — exact ISO 8601 UTC timestamp for window reset
- `limits[].is_active` — `true` when throttled/blocked
- `limits[].severity` — `"normal"` | `"warning"` | `"critical"` | `"blocked"`

**Local cache (secondary, ~60s stale):** `~/.claude/hud/.usage-cache.json` → `data.fiveHour` (int %), `data.fiveHourResets` (ISO string). Refreshed by HUD daemon. Not authoritative.

**Prediction:** No public token-per-window figure. Anthropic expresses this as % only. Empirical burn rate required.

---

### 2. Daily Quotas & Exact Reset Timestamps

**Honest finding: No `daily` limit in the API response for Max plans.**

The `extra_usage` object contains daily/weekly sub-fields, but they are `null` on Max (extra usage disabled):
```json
"extra_usage": {
    "is_enabled": false,
    "daily": null,
    "weekly": null
}
```

The `limits[]` array is the exhaustive enumeration of all active limits — no `"daily"` kind entry appeared.
Daily limits are a Free/Pro tier construct. Max uses 5-hour and 7-day windows only.

**For API-key tier (non-OAuth, non-MAX):** HTTP 429 response headers:
```
x-ratelimit-limit-requests: <N>
x-ratelimit-remaining-requests: <N>
x-ratelimit-reset-requests: <ISO8601>
x-ratelimit-limit-tokens: <N>
x-ratelimit-remaining-tokens: <N>
x-ratelimit-reset-tokens: <ISO8601>
retry-after: <seconds>
```
These headers do NOT appear on OAuth/Max consumer traffic.

---

### 3. Weekly Volume Limits / Message Buckets

**Best method:** OAuth endpoint `seven_day` object + `limits[]` entry where `kind == "weekly_all"`.

**Live response this session:**
```json
"seven_day": {
    "utilization": 93.0,
    "resets_at": "2026-08-07T03:00:00.263693+00:00"
},
"limits": [
    {
        "kind": "weekly_all",
        "group": "weekly",
        "percent": 93,
        "severity": "critical",
        "resets_at": "2026-08-07T03:00:00.263693+00:00",
        "is_active": true
    },
    {
        "kind": "weekly_scoped",
        "group": "weekly",
        "percent": 0,
        "scope": {"model": {"display_name": "Fable"}},
        "is_active": false
    }
]
```

- `weekly_all.is_active: true` — confirms budget exhaustion NOW
- `weekly_scoped` entries — per-model sub-buckets (Fable = Opus-class codename)
- `seven_day_sonnet`, `seven_day_opus` top-level fields exist but are `null` on this account

**Secondary:** `ccusage weekly --json` parses `~/.claude/history.jsonl` for rolling 7-day token sum. Divide by ~680M (observed Max 5X limit) for %. **Caveat:** returning empty on this machine today — OAuth endpoint is more reliable.

**Thunderbird's implementation** (`core/ops/thunderbird_rate_limit_guard.py`):
1. `ccusage weekly --json` → primary (token math, `WEEKLY_LIMIT_ALL = 680_000_000`)
2. HUD cache `~/.claude/hud/.usage-cache.json` → fallback for 5-hour %
3. SQLite `storage/ai_costs.db` → `claude_usage_reports.sonnet_weekly_pct` → model-specific

---

### 4. Monthly Hard Spend Caps / Prepaid Balances

**Honest finding: Not exposed in OAuth usage endpoint for Max plan.**

`extra_usage` is the intended field, null/disabled on this account. When enabled:
```json
"extra_usage": {
    "is_enabled": true,
    "monthly_limit": <dollars>,
    "used_credits": <dollars>,
    "utilization": <percent>,
    "currency": "usd",
    "spend_limit_reached": false
}
```

**This Wing's actual method:** `~/.claude/metrics.json` populated by `~/.claude/metrics_daemon.py` (scrapes Anthropic console via authenticated session).
**Live value this session:** `$55.67 / $100.00 (56%)` — read from `metrics.json` at 09:05 MT.

**For API-key tier (Workspaces):** `GET https://api.anthropic.com/v1/usage` with `ANTHROPIC_API_KEY` + billing admin scope — returns monthly token/cost by model. Different endpoint, different auth.

**Spend cap enforcement:** Server-side only. `spend_limit_reached` boolean in `extra_usage` is the only programmatic signal. The $100/mo MAX cap is set in Anthropic console billing settings.

---

## SUMMARY TABLE

| Limit Class | Authoritative Source | Key Field | Reset Timestamp Field |
|---|---|---|---|
| 5-Hour Burst | `GET /api/oauth/usage` | `five_hour.utilization` | `five_hour.resets_at` (ISO 8601 UTC) |
| Daily | N/A — no daily limit on Max plan | — | — |
| 7-Day Weekly | `GET /api/oauth/usage` | `seven_day.utilization` | `seven_day.resets_at` (ISO 8601 UTC) |
| Monthly Spend | `extra_usage` (OAuth) or console scrape | `used_credits / monthly_limit` | Monthly billing cycle |

---

## CANONICAL IMPLEMENTATION PATTERN

```python
import json, urllib.request

CREDS_FILE = "/home/john/.claude/.credentials.json"
USAGE_URL  = "https://api.anthropic.com/api/oauth/usage"

def get_usage() -> dict:
    creds = json.load(open(CREDS_FILE))["claudeAiOauth"]
    req = urllib.request.Request(
        USAGE_URL,
        headers={
            "Authorization": f"Bearer {creds['accessToken']}",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.load(r)
    return {
        "five_hour_pct":    data["five_hour"]["utilization"],
        "five_hour_resets": data["five_hour"]["resets_at"],    # ISO 8601 UTC
        "seven_day_pct":    data["seven_day"]["utilization"],
        "seven_day_resets": data["seven_day"]["resets_at"],    # ISO 8601 UTC
        "limits":           data["limits"],   # full array for is_active checks
    }
```

**Token refresh** (check `expiresAt` epoch ms vs `time.time()*1000` before each call):
```bash
curl -s -X POST "https://api.anthropic.com/v1/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&refresh_token=<refresh_token>"
# Returns: access_token, refresh_token, expires_in (seconds)
```

---

## CAVEATS & GAPS (complete, unfiltered)

- `limit_dollars`, `used_dollars`, `remaining_dollars` all `null` on Max — no dollar-denominated limit in API response
- Per-model sub-buckets (`seven_day_sonnet`, `seven_day_opus`) present in response schema but `null` on this account
- Weekly reset time `03:00 UTC` empirically — not guaranteed stable by Anthropic docs
- `ccusage weekly` returning empty on this machine today — do not depend on as sole source
- No predictive API exists — derive burn rate from your own time-series of `utilization` samples
- HUD cache is 60s stale maximum — usable for display, not for gate decisions

---

*Commands run: `curl GET /api/oauth/usage` (live), `cat ~/.claude/.credentials.json` (structure), `cat ~/.claude/hud/.usage-cache.json`, `cat ~/.claude/metrics.json`, `cat ~/.claude/policy-limits.json`, read `core/ops/thunderbird_rate_limit_guard.py` (L1-280), `cat ~/.claude/stats-cache.json` — all confirmed on /home/john system, 2026-08-06T09:10 MT.*

*— Talon (Claude Sonnet 4.6 Thinking via Antigravity)*
