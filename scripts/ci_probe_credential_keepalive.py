#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Credential & OAuth Keepalive
================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Replaces the old credential-keepalive health_probe (`test -f
keepalive_supervisor.py`), which only checked the supervisor SCRIPT existed.
The supervisor file can exist, its timer can fire, and credentials can still be
expired — as observed 2026-06-21 (perx/room_res expired 60h+ while the timer
ran 3h prior). Presence of the keeper proves nothing about whether credentials
are actually alive.

This probe checks EFFICACY: it runs the canonical credential health check and
goes RED if any CLIENT-AFFECTING credential is expired/missing/errored, or if
the supervising timer is dead. Expired client-affecting creds = no B2B quotes,
no portal access — the exact harm keepalive exists to prevent.

Exit 0 = RAZOR_SHARP. Exit 1 = degraded.
"""
import json
import subprocess
import sys

HEALTH = "/home/john/Thunderbird/scripts/credentials_health_check.py"
PYBIN  = "/home/john/Thunderbird/.venv/bin/python3"
DEAD   = {"expired", "missing", "error"}


def fail(msg: str) -> "NoReturn":
    print(f"RED credential-keepalive: {msg}")
    sys.exit(1)


def main() -> None:
    # 1. Supervising timer alive?
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", "keepalive-supervisor.timer"],
                           capture_output=True, text=True, timeout=10)
        if r.stdout.strip() != "active":
            fail(f"keepalive-supervisor.timer is {r.stdout.strip() or 'unknown'} (the keeper is down)")
    except Exception as e:
        # systemd not reachable from probe context — don't hard-fail on this alone
        print(f"WARN credential-keepalive: timer check skipped ({e})", file=sys.stderr)

    # 2. Are credentials actually fresh?
    try:
        r = subprocess.run([PYBIN, HEALTH, "--json", "--quiet"],
                           capture_output=True, text=True, timeout=50)
    except subprocess.TimeoutExpired:
        fail("credential health check timed out (>50s)")
    except Exception as e:
        fail(f"could not run credential health check: {e}")

    try:
        creds = json.loads(r.stdout).get("credentials", {})
    except Exception as e:
        fail(f"credential health output unparseable: {e}")

    if not creds:
        fail("credential health check returned no credentials")

    dead_client = [
        f"{name}={c.get('status')}"
        for name, c in creds.items()
        if c.get("client_affecting") and c.get("status") in DEAD
    ]
    if dead_client:
        fail("client-affecting credential(s) not alive: " + ", ".join(dead_client))

    # Healthy — report the tightest expiry for visibility
    soon = min(
        ((c.get("expires_in_hours"), n) for n, c in creds.items()
         if isinstance(c.get("expires_in_hours"), (int, float)) and c.get("expires_in_hours") != 9999),
        default=(None, None),
    )
    tail = f"; tightest: {soon[1]} in {soon[0]:.1f}h" if soon[0] is not None else ""
    print(f"RAZOR_SHARP credential-keepalive: {len(creds)} creds, all client-affecting alive{tail}")
    sys.exit(0)


if __name__ == "__main__":
    main()
