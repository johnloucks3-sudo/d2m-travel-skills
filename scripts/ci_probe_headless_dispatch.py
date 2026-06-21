#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Headless AI Dispatch
========================================
Hardens `test -x claude && test -f creds` (a creds file can exist holding a
DEAD token). Verifies the claude binary is executable AND the OAuth token is
usable — not expired without a refresh token. Does NOT spawn a paid `claude -p`
call; checks token freshness only.
Exit 0 = healthy, 1 = degraded.
"""
import json
import os
import sys
import time
from pathlib import Path

CLAUDE = Path.home() / ".local" / "bin" / "claude"
CREDS  = Path.home() / ".claude" / ".credentials.json"


def fail(m): print(f"RED headless-dispatch: {m}"); sys.exit(1)


def main():
    if not (CLAUDE.exists() and os.access(CLAUDE, os.X_OK)):
        fail(f"claude binary missing/not executable at {CLAUDE}")
    if not CREDS.exists():
        fail("no ~/.claude/.credentials.json — cannot dispatch")
    try:
        o = json.loads(CREDS.read_text()).get("claudeAiOauth", {})
    except Exception as e:
        fail(f"credentials unreadable: {e}")
    exp = o.get("expiresAt")           # epoch ms
    has_refresh = bool(o.get("refreshToken"))
    if not o.get("accessToken"):
        fail("no accessToken in credentials")
    if exp is not None:
        hrs = (exp / 1000 - time.time()) / 3600
        if hrs < 0 and not has_refresh:
            fail(f"OAuth token expired {abs(hrs):.1f}h ago and no refreshToken — dispatch will fail")
        tail = f"token {'auto-refreshes' if has_refresh else f'valid {hrs:.1f}h'}"
    else:
        tail = "token present (no expiry field)"
    print(f"RAZOR_SHARP headless-dispatch: binary executable, {tail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
