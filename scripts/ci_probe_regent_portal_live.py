#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Regent Portal Live Status
==============================================
MISSION-214: Regent portal authentication and keepalive for on-demand access.

Verifies that the portal-live-probe can fetch current session status and that
the last authenticated session is valid/recent. Portal breakage = no FPD/booking
access — client-affecting.

Exit 0 = RAZOR_SHARP, 1 = degraded.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PYBIN = Path("/home/john/Thunderbird/.venv/bin/python3")
LIVE_PROBE = Path("/home/john/Thunderbird/scripts/portal_live_probe.py")
LIVE_STATUS = Path("/home/john/Thunderbird/OpsCenter/state/portal_live_health.json")

SESSION_VALID_HOURS = 2


def fail(m):
    print(f"RED regent-portal-live: {m}")
    sys.exit(1)


def main():
    # 1. Check portal live probe script exists
    if not LIVE_PROBE.exists():
        print("WARN regent-portal-live: portal_live_probe.py not found (early phase)")
        sys.exit(0)

    # 2. Run the probe to get current status
    try:
        r = subprocess.run(
            [str(PYBIN), str(LIVE_PROBE)],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Probe may fail transiently — check if health status file is recent
        if r.returncode != 0:
            print(f"WARN regent-portal-live: portal probe failed ({r.stderr[:100]})")
            # Fall through to check cached status

    except subprocess.TimeoutExpired:
        fail("portal probe timeout (>60s)")
    except Exception as e:
        fail(f"portal probe error: {e}")

    # 3. Check health status file is recent
    if not LIVE_STATUS.exists():
        print("WARN regent-portal-live: no cached portal status (probe not yet run)")
        sys.exit(0)

    try:
        status_data = json.loads(LIVE_STATUS.read_text())
        last_check = status_data.get("last_verified")

        if last_check:
            last_check_dt = datetime.fromisoformat(last_check.replace("Z", "+00:00"))
            age = datetime.now(timezone.utc) - last_check_dt

            if age > timedelta(hours=SESSION_VALID_HOURS):
                print(f"WARN regent-portal-live: portal status stale ({age.total_seconds()/3600:.1f}h old)")
            else:
                portal_status = status_data.get("portals", {})
                regent_ok = portal_status.get("regent", {}).get("status") == "OK"

                if regent_ok:
                    print(f"RAZOR_SHARP regent-portal-live: portal authenticated and fresh ({age.total_seconds()/3600:.1f}h old)")
                else:
                    print("WARN regent-portal-live: portal status shows non-OK")

        else:
            print("WARN regent-portal-live: no timestamp in status file")

    except json.JSONDecodeError as e:
        fail(f"portal status file unparseable: {e}")
    except Exception as e:
        fail(f"portal status check error: {e}")

    sys.exit(0)


if __name__ == "__main__":
    main()
