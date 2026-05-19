#!/usr/bin/env python3
"""
Telegram Bot Health Check — OC-YOGA-BUILD-001
Pings active bots via getMe, writes status to hale_state.json wing_health.telegram_bots.
Runs every 60 seconds via thunderbird-telegram-health.timer.
No LLM required.
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
HALE_STATE = ROOT / "hale_state.json"
ENV_FILE = ROOT / ".env"

BOTS = {
    "D2MC2C": "TELEGRAM_BOT_TOKEN",
    "Dani": "TELEGRAM_CHANNELS_BOT_TOKEN",
}

TELEGRAM_API = "https://api.telegram.org/bot{token}/getMe"


def _load_env() -> dict:
    """Load .env file into a dict. Environment vars take precedence."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    # Environment overrides file
    env.update({k: v for k, v in os.environ.items()})
    return env


def _ping_bot(token: str) -> dict:
    """Call getMe on a bot token. Returns status dict."""
    url = TELEGRAM_API.format(token=token)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ThunderbirdHealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("ok"):
                me = data.get("result", {})
                return {
                    "status": "LIVE",
                    "username": me.get("username", "unknown"),
                    "bot_id": me.get("id"),
                    "last_check": datetime.now().isoformat(),
                }
            return {"status": "DEAD", "error": "ok=false", "last_check": datetime.now().isoformat()}
    except urllib.error.HTTPError as e:
        return {"status": "DEAD", "error": f"HTTP {e.code}", "last_check": datetime.now().isoformat()}
    except Exception as e:
        return {"status": "DEAD", "error": str(e)[:120], "last_check": datetime.now().isoformat()}


def _load_hale_state() -> dict:
    try:
        return json.loads(HALE_STATE.read_text())
    except Exception:
        return {}


def _save_hale_state(state: dict):
    HALE_STATE.write_text(json.dumps(state, indent=2, default=str))


def run():
    env = _load_env()
    results = {}

    for bot_name, env_key in BOTS.items():
        token = env.get(env_key, "").strip()
        if not token:
            results[bot_name] = {
                "status": "UNKNOWN",
                "error": f"Token env var {env_key} not set",
                "last_check": datetime.now().isoformat(),
            }
            print(f"⚠️  {bot_name}: token not found ({env_key})")
            continue

        result = _ping_bot(token)
        results[bot_name] = result
        icon = "✅" if result["status"] == "LIVE" else "❌"
        print(f"{icon} {bot_name}: {result['status']} (@{result.get('username', 'n/a')})")

    results["last_health_check"] = datetime.now().isoformat()

    # Write to hale_state.json
    state = _load_hale_state()
    if "wing_health" not in state:
        state["wing_health"] = {}
    state["wing_health"]["telegram_bots"] = results
    state["wing_health"]["last_health_check"] = datetime.now().isoformat()
    if "_meta" not in state:
        state["_meta"] = {}
    state["_meta"]["last_updated"] = datetime.now().astimezone().isoformat()
    _save_hale_state(state)

    live_count = sum(1 for v in results.values() if isinstance(v, dict) and v.get("status") == "LIVE")
    total = len(BOTS)
    print(f"📊 Telegram health: {live_count}/{total} LIVE — written to hale_state.json")
    return results


if __name__ == "__main__":
    run()
