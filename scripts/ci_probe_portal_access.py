#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Cruise-line Portal Access
=============================================
Replaces `import camoufox` (library-present != portals-reachable). Reads the
live portal health written by scripts/portal_live_probe.py and REDs if the
result is stale or any CLIENT-AFFECTING portal is not alive. Portal access is
client-affecting: dead = no B2B quotes, no FPD/booking verification.
Exit 0 = healthy, 1 = degraded.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE = Path.home() / "Thunderbird" / "OpsCenter" / "state" / "portal_live_health.json"
STALE_HOURS = 3


def fail(m): print(f"RED portal-access: {m}"); sys.exit(1)


def main():
    if not STATE.exists():
        fail("no portal_live_health.json — live portal probe has never run")
    d = json.loads(STATE.read_text())
    try:
        age_h = (datetime.now(timezone.utc) -
                 datetime.fromisoformat(d["checked_at_utc"])).total_seconds() / 3600
    except Exception:
        age_h = (sys.float_info.max)
    if age_h > STALE_HOURS:
        fail(f"stale: portal health {age_h:.1f}h old (probe stopped running)")
    dead = [f"{n}={r.get('status')}" for n, r in d.get("results", {}).items()
            if r.get("client_affecting") and not r.get("alive")]
    if dead:
        fail("client-affecting portal(s) down: " + ", ".join(dead))
    print(f"RAZOR_SHARP portal-access: {d.get('portals_checked')} portals, "
          f"{d.get('failures')} failures, {age_h:.1f}h old")
    sys.exit(0)


if __name__ == "__main__":
    main()
