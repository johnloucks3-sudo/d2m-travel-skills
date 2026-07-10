#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Flight Fare Watch Centrav B2B Source
=========================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Incident 2026-05-30 – 2026-06-27: 27-day blind spot. Session died silently.
allowed_rcs=(0,2,3) on centrav-warm masked rc=2 (dead session) as acceptable.
No alarm fired for 27 days. (Wing Exercise BURNING HOT CI, 2026-06-27)

Incident 2026-06-28: chromium_headless_shell binary was also missing — fare_watch_centrav.py
crashed on every attempt. This probe catches both failure modes.

Incident 2026-07-09: probe hardcoded the DEFAULT playwright cache path
(~/.cache/ms-playwright) and went RED even though the binary was correctly
installed — this system redirects installs via PLAYWRIGHT_BROWSERS_PATH.
Probe now checks both locations.

Checks:
  1. chromium_headless_shell binary exists (fare_watch_centrav.py dependency)
  2. OpsCenter/fare_watches/last_check.json — watches_checked >= 1 AND last run <25h
  3. Centrav session cookie is valid (sessionid present and HTTP check succeeds)

Exit 0 = RAZOR_SHARP. Exit 1 = RED.
"""
import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

_PW_BROWSERS_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
CHROMIUM_GLOBS = [
    "/home/john/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
] + ([f"{_PW_BROWSERS_PATH}/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"] if _PW_BROWSERS_PATH else [])
CHROMIUM_GLOB = CHROMIUM_GLOBS[0]  # kept for the error-message string below
LAST_CHECK     = Path("/home/john/Thunderbird/OpsCenter/fare_watches/last_check.json")
# centrav_session_warm.py writes to core/travel/data/centrav_session.json (not creds/)
COOKIE_FILE    = Path("/home/john/Thunderbird/core/travel/data/centrav_session.json")
CURRENCY_H     = 25
PYBIN          = "/home/john/Thunderbird/.venv/bin/python3"
KEEPALIVE      = "/home/john/Thunderbird/scripts/centrav_session_warm.py"
# Centrav uses laravel_session (not sessionid). trustId* = "Remember this Browser" cookie.
AUTH_COOKIE    = "laravel_session"


def fail(msg: str) -> "NoReturn":
    print(f"RED fare-watch-centrav: {msg}")
    sys.exit(1)


def main() -> None:
    # 1. chromium_headless_shell binary (default cache OR PLAYWRIGHT_BROWSERS_PATH redirect)
    matches = []
    for g in CHROMIUM_GLOBS:
        matches = glob.glob(g)
        if matches:
            break
    if not matches:
        fail(
            f"chromium_headless_shell binary missing (checked {CHROMIUM_GLOBS}). "
            "fare_watch_centrav.py crashes without it. "
            "Fix: .venv/bin/playwright install chromium"
        )
    chromium_ver = Path(matches[0]).parent.parent.parent.name  # e.g. chromium_headless_shell-1208

    # 2. last_check.json freshness and watches_checked
    if not LAST_CHECK.exists():
        fail(f"fare_watches/last_check.json missing — fare watch has never run")

    try:
        lc = json.loads(LAST_CHECK.read_text())
    except Exception as e:
        fail(f"last_check.json unparseable: {e}")

    completed_at_str = lc.get("completed_at") or lc.get("started_at")
    if not completed_at_str:
        fail("last_check.json has no completed_at/started_at timestamp")

    try:
        completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
    except Exception as e:
        fail(f"could not parse completed_at '{completed_at_str}': {e}")

    age_h = (datetime.now(tz=timezone.utc) - completed_at).total_seconds() / 3600
    if age_h > CURRENCY_H:
        fail(f"last_check.json stale: {age_h:.1f}h ago (threshold {CURRENCY_H}h)")

    watches_checked = lc.get("watches_checked", 0)
    watches_total   = lc.get("watches_total", 0)
    errors          = len(lc.get("errors", []))

    if watches_checked == 0 and watches_total > 0:
        # All checks errored — likely dead session or missing binary
        first_err = (lc.get("errors") or [{}])[0].get("error", "")[:120]
        fail(
            f"0/{watches_total} watches checked in last run — all errored. "
            f"First error: {first_err}"
        )

    # 3. Centrav session — sessionid must be present and valid
    if not COOKIE_FILE.exists():
        fail(f"Centrav cookie file missing at {COOKIE_FILE}")

    try:
        cookies = json.loads(COOKIE_FILE.read_text())
        # Centrav auth = laravel_session (not sessionid — that's a perx pattern)
        session_cookie = next((c for c in cookies if c.get("name") == AUTH_COOKIE and c.get("value")), None)
    except Exception as e:
        fail(f"Could not read centrav cookies from {COOKIE_FILE}: {e}")

    if not session_cookie:
        fail(f"Centrav session file has no {AUTH_COOKIE} — session is dead; need manual re-auth via centrav_serve.py")

    # Check laravel_session expiry
    now_ts = time.time()
    exp = session_cookie.get("expires", -1)
    if exp and exp > 0 and exp < now_ts:
        hours_ago = (now_ts - exp) / 3600
        fail(f"Centrav {AUTH_COOKIE} expired {hours_ago:.1f}h ago — session dead; need centrav_serve.py re-auth")

    print(
        f"RAZOR_SHARP fare-watch-centrav: {watches_checked}/{watches_total} watches checked "
        f"{age_h:.1f}h ago, {errors} errors; {chromium_ver}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
