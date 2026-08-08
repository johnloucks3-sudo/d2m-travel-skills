#!/usr/bin/env python3
"""
Thunderbird Health Check — YOGA Service Monitor
=================================================
Monitors all systemd services on YOGA (primary server). Sends Gmail alerts
on failure, recovery "all clear" when services come back.

Runs via cron every 5 minutes:
  */5 * * * * ~/Thunderbird/.venv/bin/python3 ~/Thunderbird/deploy/health_check.py >> ~/Thunderbird/logs/health_check.log 2>&1
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent for gmail helper
sys.path.insert(0, str(Path(__file__).parent.parent))

STATE_FILE = Path(__file__).parent.parent / "logs" / "health_state.json"
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

SERVICES = [
    "thunderbird-mcp.service",
    "thunderbird-api.service",
    "cloudflared.service",
    "d2m-scheduler.service",
]
# CORRECTION (2026-08-08, War Room RT-ALERT-MCP-TUNNEL-SCHEDULER, AG-verified
# against live systemd state): the prior SERVICES list watched
# thunderbird-tunnel.service and thunderbird-scheduler.service — both were
# INTENTIONALLY disabled the same day (found + fixed live: thunderbird-tunnel
# was a duplicate cloudflared process running the SAME tunnel ID as
# cloudflared.service simultaneously; thunderbird-scheduler lost a lock race
# to d2m-scheduler.service on every single boot, wasting CPU/memory for
# nothing). The 2026-08-07 F-3 correction above already caught the same
# class of confusion once (thunderbird-mcp.service vs d2m-mcp.service) — this
# is the SAME recurring failure mode: a monitor watching a name instead of
# re-verifying which unit is actually live. check_service() below is fixed
# to check is-enabled alongside is-active for exactly this reason.
# CORRECTION (2026-08-07, PROPOSAL-20260807-thunderbird-mcp F-3): the prior
# 2026-07-30 note below claimed d2m-mcp.service "is already a symlink alias to
# thunderbird-mcp.service." That was never verified and is FALSE — inode check
# proved they are two independent, byte-identical unit files that both bound
# port 8765 and mutually SIGKILLed each other (~34h crash loop). d2m-mcp.service
# is now stopped/disabled/masked; thunderbird-mcp.service is canonical. This
# monitor now watches the real unit.
# Original note (2026-07-30, partially wrong, kept for record): d2m-api.service
# / d2m-scheduler.service are dead duplicate unit files left over from the
# 2026-04-06 d2m-* -> thunderbird-* rename — same ExecStart, disabled, never
# the ones actually running. thunderbird-api.service / thunderbird-scheduler.service
# are the live units. Watching the old names produced two permanent false
# "FAILED" entries. d2m-api/d2m-scheduler status was NOT independently
# reverified during this fix — same false-alias claim may apply, flagged for
# follow-up, not confirmed either way.

OWNER_EMAIL = "johnloucks3@gmail.com"
ALERT_INTERVAL_MINUTES = 30  # re-alert every 30 min if still down


def _user_systemd_env() -> dict:
    """Build environment with XDG_RUNTIME_DIR for systemctl --user from cron."""
    import os
    env = os.environ.copy()
    uid = str(os.getuid())
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{uid}/bus")
    return env


def check_service(name: str) -> bool:
    """Return True if service is healthy: active, OR intentionally disabled.

    A disabled unit is not a failure — it's a decision. Checking is-active
    alone (the old behavior) alerts forever on any unit someone correctly
    turned off (confirmed live 2026-08-08: thunderbird-tunnel.service and
    thunderbird-scheduler.service both false-alerted this way after being
    deliberately disabled the same day). Only a unit that's ENABLED (expected
    to be running) and NOT active is a real failure."""
    try:
        active = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True, text=True, timeout=10,
            env=_user_systemd_env(),
        ).stdout.strip()
        if active == "active":
            return True
        enabled = subprocess.run(
            ["systemctl", "--user", "is-enabled", name],
            capture_output=True, text=True, timeout=10,
            env=_user_systemd_env(),
        ).stdout.strip()
        if enabled in ("disabled", "masked"):
            return True  # intentionally off — not a failure
        return False
    except Exception:
        return False


def check_tunnel_roundtrip() -> bool:
    """Quick check that the tunnel is reachable."""
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10", "-o", "/dev/null",
             "-w", "%{http_code}", "https://mcp.d2mluxury.quest/sse"],
            capture_output=True, text=True, timeout=15,
        )
        # 401 is the documented LIVE state — nginx auth_basic challenge
        # (docs/D2MLUXURY_SUBDOMAIN_AUDIT_20260716.md), not a failure.
        return result.stdout.strip() in ("200", "301", "302", "307", "401")
    except Exception:
        return False


def check_api_roundtrip() -> bool:
    """Quick check that the REST API responds."""
    try:
        result = subprocess.run(
            ["curl", "-sf", "--max-time", "10", "-o", "/dev/null",
             "-w", "%{http_code}", "https://api.d2mluxury.quest/docs"],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip() == "200"
    except Exception:
        return False


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"failures": {}, "last_alert": None, "healthy": True}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def send_alert(subject: str, body: str):
    """Send alert via Gmail API."""
    try:
        from thunderbird_gmail import _get_gmail_service
        from email.mime.text import MIMEText
        import base64

        service = _get_gmail_service()
        msg = MIMEText(body)
        msg["to"] = OWNER_EMAIL
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        print(f"  Alert sent: {subject}")
    except Exception as e:
        print(f"  ALERT SEND FAILED: {e}")


def main():
    now = datetime.now()
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Health check running...")

    state = load_state()
    results = {}

    # Check all services
    for svc in SERVICES:
        ok = check_service(svc)
        results[svc] = ok
        status = "OK" if ok else "FAILED"
        print(f"  {svc}: {status}")

    # Check tunnel roundtrip
    tunnel_ok = check_tunnel_roundtrip()
    results["tunnel_roundtrip"] = tunnel_ok
    print(f"  tunnel_roundtrip: {'OK' if tunnel_ok else 'FAILED'}")

    # Check API roundtrip
    api_ok = check_api_roundtrip()
    results["api_roundtrip"] = api_ok
    print(f"  api_roundtrip: {'OK' if api_ok else 'FAILED'}")

    # Determine failures
    failures = {k: v for k, v in results.items() if not v}
    was_healthy = state.get("healthy", True)

    if failures:
        state["healthy"] = False
        state["failures"] = {k: now.isoformat() for k in failures}

        # Decide whether to send alert
        last_alert = state.get("last_alert")
        should_alert = False

        if was_healthy:
            # First failure — always alert
            should_alert = True
        elif last_alert:
            # Re-alert every 30 minutes
            last_dt = datetime.fromisoformat(last_alert)
            if (now - last_dt).total_seconds() >= ALERT_INTERVAL_MINUTES * 60:
                should_alert = True
        else:
            should_alert = True

        if should_alert:
            failed_list = "\n".join(f"  - {k}" for k in failures)
            send_alert(
                f"[THUNDERBIRD] Service Alert — {len(failures)} check(s) FAILED",
                f"Health check at {now.strftime('%Y-%m-%d %H:%M')} detected failures:\n\n"
                f"{failed_list}\n\n"
                f"Machine: YOGA (192.168.1.198)\n"
                f"Action: Check systemctl --user status on YOGA\n"
            )
            state["last_alert"] = now.isoformat()
    else:
        # All healthy
        if not was_healthy:
            # Was broken, now recovered — send all-clear
            send_alert(
                "[THUNDERBIRD] All Clear — Services Recovered",
                f"All services healthy as of {now.strftime('%Y-%m-%d %H:%M')}.\n\n"
                f"Machine: YOGA (192.168.1.198)\n"
            )
        state["healthy"] = True
        state["failures"] = {}
        state["last_alert"] = None

    save_state(state)
    print(f"  Overall: {'HEALTHY' if not failures else 'DEGRADED'}")


if __name__ == "__main__":
    main()
