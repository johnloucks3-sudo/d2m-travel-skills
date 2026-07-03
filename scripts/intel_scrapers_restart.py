#!/usr/bin/env python3
"""Auto-repair: Intel scrapers — restart connection pool and credential refresh."""
import subprocess, sys, json
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

def main():
    try:
        # Attempt to refresh all intel-related credentials and connections
        # This is a catch-all that re-runs the intel integrity check
        result = subprocess.run(
            ["/usr/bin/python3", str(ROOT / "scripts/silversea_cookie_refresh.py")],
            cwd=str(ROOT),
            timeout=120,
            capture_output=True,
            text=True
        )

        intel_ok = result.returncode == 0

        # Also try perx session refresh if it exists
        perx_script = ROOT / "scripts/perx_intel_monitor.py"
        if perx_script.exists():
            result2 = subprocess.run(
                ["/usr/bin/python3", str(perx_script)],
                cwd=str(ROOT),
                timeout=120,
                capture_output=True,
                text=True
            )
            intel_ok = intel_ok and (result2.returncode == 0)

        if intel_ok:
            print("Intel scrapers restart: SUCCESS")
            return 0
        else:
            print("Intel scrapers restart: PARTIAL (some scrapers failed)")
            return 1
    except subprocess.TimeoutExpired:
        print("Intel scrapers restart: TIMEOUT")
        return 124
    except Exception as e:
        print(f"Intel scrapers restart: ERROR — {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
