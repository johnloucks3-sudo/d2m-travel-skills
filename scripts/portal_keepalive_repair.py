#!/usr/bin/env python3
"""Auto-repair: Portal session refresh (Regent, Silversea, etc).

Centrav EXCLUDED (RT-CENTRAV-SPAWN 2026-08-09): this is the only remaining
live auto-trigger into portal_keepalive.py's chromium centrav path — fired by
repair_bot.py's auto-repair-trigger task whenever infra_bot hits 10
consecutive failures. Called portal_keepalive.py with no --portal filter,
i.e. refreshed ALL portals including centrav (chromium spawn) unconditionally.
Commander 2026-08-07: KILL all airfare session keep-alives except Skybird —
Centrav is on-demand re-auth only now.
"""
import subprocess, sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

def main():
    try:
        # Run portal keepalive refresh — EXCLUDE centrav (see module docstring)
        result = subprocess.run(
            ["/usr/bin/python3", str(ROOT / "scripts/portal_keepalive.py"), "--exclude", "centrav"],
            cwd=str(ROOT),
            timeout=120,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Portal keepalive repair: SUCCESS")
            return 0
        else:
            print(f"Portal keepalive repair: FAILED (rc={result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return 1
    except subprocess.TimeoutExpired:
        print("Portal keepalive repair: TIMEOUT")
        return 124
    except Exception as e:
        print(f"Portal keepalive repair: ERROR — {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
