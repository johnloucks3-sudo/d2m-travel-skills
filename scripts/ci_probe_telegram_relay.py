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

2026-07-07 GAP CLOSED — getMe-only was blind to a real incident: llmtrim
proxy instability caused 253 "Read timed out" errors + 12 full service
restarts on the gateway in one morning, disrupting the Commander directly
via Telegram phone notifications, while this probe reported "ok": true
throughout because getMe (a single instant request) succeeds regardless
of the long-poll connection's actual stability. Commander: "unacceptable
error rate... unacceptable lack of HALE/STAFF involvement... I am the one
who has to be annoyed." Root cause fixed in config/telegram_gw.env
(proxy bypass) — this probe now also checks recent restart count and
error rate via journalctl so the NEXT incident like this pages Whetstone/
Sterling instead of only reaching the Commander's phone.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = "/home/john/Thunderbird"
ENV_FILE = f"{ROOT}/.env"
BOTS = {"D2MC2C": "TELEGRAM_BOT_TOKEN", "Dani": "TELEGRAM_CHANNELS_BOT_TOKEN"}
GATEWAY_UNIT = "thunderbird-telegram-gw.service"
RESTART_THRESHOLD_1H = 2   # >2 restarts in 1h = real instability, not a one-off
ERROR_THRESHOLD_1H = 20    # >20 read-timeout/error lines in 1h = crash-loop-adjacent


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


def _check_gateway_stability() -> dict:
    """Real connection-stability check, not just identity. getMe succeeding
    tells you the bot token is valid — it says nothing about whether the
    long-poll loop is crash-looping. Check the last hour of journal for the
    actual failure signature (repeated timeouts / restarts)."""
    try:
        out = subprocess.run(
            ["journalctl", "--user", "-u", GATEWAY_UNIT, "--since", "1 hour ago", "--no-pager"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception as e:
        return {"checked": False, "error": str(e)[:150]}

    error_count = out.count("Read timed out") + out.count("ERROR")
    restart_count = out.count("Started Thunderbird Telegram Gateway")

    stable = error_count <= ERROR_THRESHOLD_1H and restart_count <= RESTART_THRESHOLD_1H
    return {
        "checked": True,
        "stable": stable,
        "error_count_1h": error_count,
        "restart_count_1h": restart_count,
        "thresholds": {"error": ERROR_THRESHOLD_1H, "restart": RESTART_THRESHOLD_1H},
    }


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

    stability = _check_gateway_stability()
    if stability.get("checked") and not stability.get("stable", True):
        all_ok = False

    print(json.dumps({
        "probe": "telegram-relay",
        "bots": results,
        "gateway_stability": stability,
        "ok": all_ok,
    }, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
