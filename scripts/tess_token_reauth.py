#!/usr/bin/env python3
"""Auto-repair: TESS token re-authentication."""
import json, subprocess, sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

def main():
    try:
        # Attempt to refresh TESS credentials via OAuth
        result = subprocess.run(
            ["/usr/bin/python3", str(ROOT / "scripts/tess_token_keepalive.py")],
            cwd=str(ROOT),
            timeout=60,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("TESS token re-auth: SUCCESS")
            return 0
        else:
            print(f"TESS token re-auth: FAILED (rc={result.returncode})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:200]}")
            return 1
    except subprocess.TimeoutExpired:
        print("TESS token re-auth: TIMEOUT")
        return 124
    except Exception as e:
        print(f"TESS token re-auth: ERROR — {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
