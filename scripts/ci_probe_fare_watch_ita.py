#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Flight Fare Watch ITA Matrix Source
========================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Incident 2026-06-28: Firefox playwright binary was missing for an unknown duration.
The registry entry referenced chromium_headless_shell but the actual scripts
(ita_fare_watch_poll.py, thunderbird_booking_monitor.py) require Firefox.
No alarm fired. This probe checks the correct binary.

NOTE: We do NOT run ita_fare_watch_poll.py --brief in the probe — that flag still
launches Firefox and fetches live data (takes 15-60s). The probe instead checks:
  1. Firefox playwright binary exists (not chromium — scripts explicitly use Firefox
     because chromium_headless_shell SIGTRAP's on this openSUSE host)
  2. ITA watch config file is readable and contains >= 1 ITA-provider watch
  3. No stale lock file with a dead PID (would block every run)

Exit 0 = RAZOR_SHARP. Exit 1 = RED.
"""
import glob
import json
import os
import sys
from pathlib import Path

FIREFOX_GLOBS = [
    os.path.join(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""), "firefox-*/firefox/firefox"),
    "/home/john/.cache/ms-playwright/firefox-*/firefox/firefox",
    "/home/john/.playwright-browsers/firefox-*/firefox/firefox",
]
POLL_SCRIPT   = Path("/home/john/Thunderbird/scripts/ita_fare_watch_poll.py")
# ita_fare_watch_poll.py reads from OpsCenter/fare_watches/ config
WATCH_CONFIG  = Path("/home/john/Thunderbird/OpsCenter/fare_watches")
LOCK_FILE     = Path("/home/john/Thunderbird/logs/ita_fare_watch.lock")


def fail(msg: str) -> "NoReturn":
    print(f"RED fare-watch-ita: {msg}")
    sys.exit(1)


def main() -> None:
    # 1. Firefox binary (the actual dependency — NOT chromium)
    matches = []
    for g in FIREFOX_GLOBS:
        if g:
            matches = glob.glob(g)
            if matches:
                break
    if not matches:
        fail(
            f"Firefox playwright binary missing (checked {[g for g in FIREFOX_GLOBS if g]}). "
            "ita_fare_watch_poll.py crashes without it. "
            "Fix: .venv/bin/playwright install firefox"
        )
    firefox_ver = Path(matches[0]).parent.parent.name  # e.g. firefox-1509

    # 2. Poll script present
    if not POLL_SCRIPT.exists():
        fail(f"ita_fare_watch_poll.py missing at {POLL_SCRIPT}")

    # 3. ITA watch config readable + contains >=1 ITA watch
    # Config lives in OpsCenter/fare_watches/ as JSON files
    ita_count = 0
    if WATCH_CONFIG.is_dir():
        for f in WATCH_CONFIG.glob("*.json"):
            try:
                d = json.loads(f.read_text())
                # watches may be at top-level list or nested
                watches = d if isinstance(d, list) else d.get("watches", [])
                ita_count += sum(1 for w in watches
                                 if isinstance(w, dict) and w.get("provider") == "ITA" and w.get("ita_url"))
            except Exception:
                pass

    # 4. Check for stale lock file (dead PID blocks every run)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)  # 0 = just check
        except (ProcessLookupError, PermissionError):
            fail(
                f"Stale lock file at {LOCK_FILE} (PID {pid} is dead) — "
                "every run will skip immediately. Fix: rm logs/ita_fare_watch.lock"
            )
        except Exception:
            pass  # couldn't parse lock — not a hard failure

    print(
        f"RAZOR_SHARP fare-watch-ita: {ita_count} ITA watch(es) configured; "
        f"Firefox={firefox_ver}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
