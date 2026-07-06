#!/usr/bin/env python3
"""Telegram Relay CI probe — closes a real monitoring gap found 2026-07-06.

Commander: "it is missing a whole batch of CI failures in Telegram relay
and other channels so it is false." Investigated: core/monitoring/
telegram_bot_healthcheck.py already runs every 60s and correctly detected
a real failure this morning (Dani bot DEAD, SSL handshake timeout) — but
that health check writes only to hale_state.json, completely disconnected
from the CI registry (config/ci_registry.json) and its REPLACE-threshold
doctrine (3 consecutive fails, 5/7d, etc). Real failures were being
detected and then going nowhere within the CI system. Telegram had ZERO
entries in the 51-skill registry.

This probe does a LIVE getMe check (not reading the cached hale_state.json
status, which can be stale between its own 60s cycles) on both bots and
exits non-zero if either is down — giving Telegram real CI coverage with
history tracking and auto-repair attempts, same as every other skill.
"""
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = "/home/john/Thunderbird"
ENV_FILE = f"{ROOT}/.env"
BOTS = {"D2MC2C": "TELEGRAM_BOT_TOKEN", "Dani": "TELEGRAM_CHANNELS_BOT_TOKEN"}


def _load_env() -> dict:
    env = {}
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update(os.environ)
    return env


def _ping_bot(token: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CI-Probe/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return {"ok": bool(data.get("ok")), "username": data.get("result", {}).get("username")}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


def main() -> int:
    env = _load_env()
    results = {}
    all_ok = True
    for bot_name, env_key in BOTS.items():
        token = env.get(env_key, "").strip()
        if not token:
            results[bot_name] = {"ok": False, "error": f"{env_key} not set"}
            all_ok = False
            continue
        r = _ping_bot(token)
        results[bot_name] = r
        if not r["ok"]:
            all_ok = False

    print(json.dumps({"probe": "telegram-relay", "bots": results, "ok": all_ok}, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
