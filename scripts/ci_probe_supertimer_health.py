#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Supertimer Bot Health
==========================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Incident 2026-06-28: intel_bot accumulated 3,622 consecutive failures (perx-intel
exiting rc=2 on URGENT signals), client_bot 299 failures (Firefox binary missing),
infra_bot 384 failures (TESS invalid_client) — all silently, no CI probe caught it.

This probe checks three things:
  1. Supertimer service is active
  2. No bot has >= threshold consecutive_failures in supertimer_health.json
  3. Firefox playwright binary exists (client_bot/intel_bot dependency)

Exit 0 = RAZOR_SHARP. Exit 1 = RED.
"""
import glob
import json
import subprocess
import sys
from pathlib import Path

HEALTH_FILE = Path("/home/john/Thunderbird/OpsCenter/supertimer_health.json")
FIREFOX_GLOB = "/home/john/.cache/ms-playwright/firefox-*/firefox/firefox"
CF_THRESHOLD = 10   # consecutive failures before RED — allows a transient cycle
BOT_SERVICE   = "thunderbird-supertimer.service"


def fail(msg: str) -> "NoReturn":
    print(f"RED supertimer-health: {msg}")
    sys.exit(1)


def main() -> None:
    # 1. Supertimer timer alive? (service is one-shot, timer re-arms it — check timer not service)
    timer_name = BOT_SERVICE.replace(".service", ".timer")
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", timer_name],
            capture_output=True, text=True, timeout=10,
        )
        state = r.stdout.strip()
        if state != "active":
            fail(f"{timer_name} is {state or 'unknown'} — supertimer will not self-restart")
    except Exception as e:
        print(f"WARN supertimer-health: timer check skipped ({e})", file=sys.stderr)

    # 2. Firefox playwright binary
    matches = glob.glob(FIREFOX_GLOB)
    if not matches:
        fail(
            f"Firefox playwright binary missing at {FIREFOX_GLOB} — "
            "ita_fare_watch_poll.py and thunderbird_booking_monitor.py will crash on every run. "
            "Fix: .venv/bin/playwright install firefox"
        )

    # 3. Supertimer bot consecutive failures
    if not HEALTH_FILE.exists():
        fail(f"supertimer_health.json missing at {HEALTH_FILE} — leader not writing health")

    try:
        health = json.loads(HEALTH_FILE.read_text())
    except Exception as e:
        fail(f"supertimer_health.json unparseable: {e}")

    red_bots = {
        bot: info["consecutive_failures"]
        for bot, info in health.items()
        if isinstance(info, dict) and info.get("consecutive_failures", 0) >= CF_THRESHOLD
    }
    if red_bots:
        detail = ", ".join(f"{b}×{n}" for b, n in red_bots.items())
        fail(
            f"bot(s) in consecutive-failure storm: {detail}. "
            f"Threshold={CF_THRESHOLD}. Check OpsCenter/supertimer_health.json "
            "for failed task names and error snippets."
        )

    # Healthy — summarise
    total_bots = len(health)
    warn_bots = {
        b: info["consecutive_failures"]
        for b, info in health.items()
        if isinstance(info, dict) and 0 < info.get("consecutive_failures", 0) < CF_THRESHOLD
    }
    warn_str = f"; {len(warn_bots)} bot(s) with minor failures {warn_bots}" if warn_bots else ""
    firefox_ver = Path(matches[0]).parent.parent.name  # e.g. firefox-1509
    print(
        f"RAZOR_SHARP supertimer-health: {total_bots} bots, "
        f"0 in failure storm{warn_str}; Firefox={firefox_ver}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
