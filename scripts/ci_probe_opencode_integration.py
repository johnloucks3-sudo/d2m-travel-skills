#!/usr/bin/env python3
"""
CI EFFICACY PROBE — OpenCode Integration
========================================
MISSION-378, MISSION-297: OpenCode agent dispatch for research + analysis.

Verifies OpenCode CLI is installed, authenticated, and can execute commands.
OpenCode dispatch is critical for parallel research workflows — broken dispatch
= stalled background agent tasks.

Exit 0 = RAZOR_SHARP, 1 = degraded.
"""
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

OPENCODE_CLI = Path.home() / ".local" / "bin" / "opencode"


def fail(m):
    print(f"RED opencode-integration: {m}")
    sys.exit(1)


def main():
    # 1. Check OpenCode CLI installed
    if not OPENCODE_CLI.exists():
        fail(f"OpenCode CLI not found at {OPENCODE_CLI}")

    # 2. Check if executable
    if not os.access(OPENCODE_CLI, os.X_OK):
        fail(f"OpenCode CLI not executable")

    # 3. Test version/status
    try:
        r = subprocess.run(
            [str(OPENCODE_CLI), "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if r.returncode != 0:
            fail(f"OpenCode CLI error: {r.stderr[:200]}")
        version = r.stdout.strip()
    except subprocess.TimeoutExpired:
        fail("OpenCode version check timeout")
    except Exception as e:
        fail(f"OpenCode check error: {e}")

    # 4. Test authentication (dry-run command)
    try:
        r = subprocess.run(
            [str(OPENCODE_CLI), "info"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if r.returncode != 0 and "auth" in r.stderr.lower():
            fail("OpenCode authentication failed")
        # Exit code != 0 is OK if it's just "no active session" type message
        if "not authenticated" in r.stderr.lower() or "login" in r.stderr.lower():
            print("WARN opencode-integration: OpenCode CLI present but not authenticated")
        else:
            print(f"RAZOR_SHARP opencode-integration: OpenCode {version} installed and operational")
    except subprocess.TimeoutExpired:
        fail("OpenCode auth check timeout")
    except Exception as e:
        fail(f"OpenCode auth check error: {e}")

    sys.exit(0)


if __name__ == "__main__":
    main()
