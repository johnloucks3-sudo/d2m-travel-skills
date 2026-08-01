"""
Claude Code (CC) Capacity Headroom Module.

Authoritative read path for CC utilization and reset windows:
1. Fresh HUD Cache (~/.claude/hud/.usage-cache.json, < 60s old) -> zero network.
2. Direct OAuth usage query (GET https://api.anthropic.com/api/oauth/usage).
3. Fallback local cache (OpsCenter/state/cc_capacity_cache.json).
4. Fail-soft UNKNOWN state.

NEVER writes to ~/.claude/.credentials.json or ~/.claude/hud/.usage-cache.json.
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

HUD_CACHE_PATH = Path("/home/john/.claude/hud/.usage-cache.json")
CREDENTIALS_PATH = Path("/home/john/.claude/.credentials.json")
LOCAL_CACHE_PATH = Path("/home/john/Thunderbird/OpsCenter/state/cc_capacity_cache.json")
OAUTH_USAGE_URL = "https://api.anthropic.com/api/oauth/usage"
HUD_CACHE_TTL_MS = 60_000  # 60 seconds
LOCAL_CACHE_TTL_SEC = 300   # 5 minutes


def _read_hud_cache() -> dict | None:
    if not HUD_CACHE_PATH.exists():
        return None
    try:
        with open(HUD_CACHE_PATH, "r", encoding="utf-8") as f:
            content = json.load(f)
        ts = content.get("timestamp", 0)
        now_ms = time.time() * 1000
        if (now_ms - ts) < HUD_CACHE_TTL_MS and not content.get("error", False):
            data = content.get("data", {})
            five_hr = data.get("fiveHour")
            seven_day = data.get("sevenDay")
            if five_hr is not None and seven_day is not None:
                return {
                    "five_hour_pct": float(five_hr),
                    "five_hour_resets_at": data.get("fiveHourResets"),
                    "seven_day_pct": float(seven_day),
                    "seven_day_resets_at": data.get("sevenDayResets"),
                    "source": "hud_cache",
                }
    except Exception:
        pass
    return None


def _fetch_oauth_capacity() -> dict | None:
    if not CREDENTIALS_PATH.exists():
        return None
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            creds = json.load(f)
        token = creds.get("claudeAiOauth", {}).get("accessToken")
        if not token:
            return None

        req = urllib.request.Request(
            OAUTH_USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                five_hr = data.get("five_hour", {})
                seven_day = data.get("seven_day", {})
                five_hr_pct = five_hr.get("utilization")
                seven_day_pct = seven_day.get("utilization")
                if five_hr_pct is not None and seven_day_pct is not None:
                    return {
                        "five_hour_pct": float(five_hr_pct),
                        "five_hour_resets_at": five_hr.get("resets_at"),
                        "seven_day_pct": float(seven_day_pct),
                        "seven_day_resets_at": seven_day.get("resets_at"),
                        "source": "oauth",
                    }
    except Exception:
        pass
    return None


def _read_local_cache() -> dict | None:
    if not LOCAL_CACHE_PATH.exists():
        return None
    try:
        with open(LOCAL_CACHE_PATH, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        ts = cache_data.get("timestamp", 0)
        if (time.time() - ts) < LOCAL_CACHE_TTL_SEC:
            return {
                "five_hour_pct": cache_data.get("five_hour_pct"),
                "five_hour_resets_at": cache_data.get("five_hour_resets_at"),
                "seven_day_pct": cache_data.get("seven_day_pct"),
                "seven_day_resets_at": cache_data.get("seven_day_resets_at"),
                "source": "local_cache",
            }
    except Exception:
        pass
    return None


def _write_local_cache(result: dict) -> None:
    try:
        LOCAL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        cache_content = {
            "timestamp": time.time(),
            "five_hour_pct": result.get("five_hour_pct"),
            "five_hour_resets_at": result.get("five_hour_resets_at"),
            "seven_day_pct": result.get("seven_day_pct"),
            "seven_day_resets_at": result.get("seven_day_resets_at"),
            "source": result.get("source"),
        }
        with open(LOCAL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache_content, f, indent=2)
    except Exception:
        pass


def get_cc_capacity() -> dict:
    """
    Get CC capacity telemetry from authoritative sources.
    Fails soft to 'unknown' if all sources fail.
    """
    # 1. Try HUD cache
    res = _read_hud_cache()

    # 2. Try direct OAuth if HUD cache missing/stale
    if res is None:
        res = _fetch_oauth_capacity()

    # 3. Try fallback local cache if OAuth failed
    if res is None:
        res = _read_local_cache()

    # If any source succeeded, write/update local cache and format response
    if res is not None:
        _write_local_cache(res)
        five_hr_pct = res.get("five_hour_pct")
        seven_day_pct = res.get("seven_day_pct")
        max_used = max(five_hr_pct, seven_day_pct)
        headroom_pct = max(0.0, round(100.0 - max_used, 1))

        if headroom_pct <= 0.0:
            status = "EXHAUSTED"
        elif headroom_pct <= 15.0:
            status = "LIMITED_WARN"
        else:
            status = "OK"

        return {
            "engine": "CC",
            "status": status,
            "ok": headroom_pct > 0.0,
            "headroom_pct": headroom_pct,
            "used_pct": round(max_used, 1),
            "five_hour_pct": five_hr_pct,
            "five_hour_resets_at": res.get("five_hour_resets_at"),
            "seven_day_pct": seven_day_pct,
            "seven_day_resets_at": res.get("seven_day_resets_at"),
            "source": res.get("source"),
            "reset_str": res.get("five_hour_resets_at"),
        }

    # 4. Fail-soft UNKNOWN response
    return {
        "engine": "CC",
        "status": "UNKNOWN",
        "ok": False,
        "headroom_pct": None,
        "used_pct": None,
        "five_hour_pct": None,
        "five_hour_resets_at": None,
        "seven_day_pct": None,
        "seven_day_resets_at": None,
        "source": "unknown",
        "reset_str": None,
        "error": "Unable to fetch capacity from HUD cache, OAuth endpoint, or local cache",
    }
