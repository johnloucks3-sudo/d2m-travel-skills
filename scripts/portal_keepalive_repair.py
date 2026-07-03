#!/usr/bin/env python3
"""Auto-repair: Portal session refresh (Centrav, Regent, Silversea)."""
import subprocess, sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

def main():
    try:
        # Run portal keepalive refresh
        result = subprocess.run(
            ["/usr/bin/python3", str(ROOT / "scripts/portal_keepalive.py")],
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
