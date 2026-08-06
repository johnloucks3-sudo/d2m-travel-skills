#!/usr/bin/env python3
"""
bsk_session_keepalive.py — AGGRESSIVE keepalive for logged-in browser sessions.

WHY THIS EXISTS (hard-won 2026-08-06, ATO-006-08):
  - Centrav `laravel_session` is httpOnly + ~2hr idle TTL; relogin is blocked by
    reCAPTCHA + email OTP; the Chrome cookie DB is v11/app-bound (no Local State key).
  - Headless relogin kept failing. The ONE reliable path = ride a HUMAN-authenticated
    browser tab (via bsk, browser-skill CLI) and touch an authenticated route
    aggressively enough to defeat the idle TTL — no cookie export, no decrypt, no CAPTCHA.
  - Design generalized to any logged-in portal via `portals.json` (Google Flights, TESS, etc.).

GROUND TRUTH (verified live on the Centrav session):
  - document.cookie exposes ONLY GA cookies; laravel_session + XSRF-TOKEN are httpOnly.
  - A passive GET / does NOT extend Laravel session TTL. An authenticated activity does.
  - The proven keepalive = re-run an authenticated action in the live tab every N minutes.

USAGE:
  python3 scripts/portal_keepalive.py --portal centrav --interval-min 20 --once
  python3 scripts/portal_keepalive.py --portal centrav --interval-min 20   # loop (for systemd)

Portals config: /home/john/Thunderbird/config/portals.json
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
PORTALS = ROOT / "config" / "portals.json"


def log(m: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {m}", flush=True)


def run_bsk(*args) -> str:
    bsk = str(Path("/home/john/.local/bin/bsk"))
    r = subprocess.run([bsk, *args], capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise RuntimeError(f"bsk {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def ensure_session(portal: dict, reuse: str = "") -> str:
    if reuse:
        return reuse
    out = run_bsk("session", "start").strip()
    run_bsk("navigate", "--session", out, portal["home_url"])
    time.sleep(2)
    return out


def alive(portal: dict, session: str) -> bool:
    """Cheap alive check: is the authenticated page still up, or did we bounce to login?"""
    try:
        snap = run_bsk("snapshot", "--session", session)
        for marker in portal["dead_markers"]:
            if marker.lower() in snap.lower():
                return False
        for marker in portal["alive_markers"]:
            if marker.lower() in snap.lower():
                return True
        # fallback: if we're on a login URL
        url = run_bsk("evaluate", "window.location.href", "--session", session).strip()
        if "login" in url.lower() or "trust" in url.lower():
            return False
        return True
    except Exception as e:
        log(f"  alive-check error: {e}")
        return False


def kick(portal: dict, session: str) -> bool:
    """Aggressive keepalive action: re-run the authenticated touch route in the live tab."""
    route = portal["keepalive_route"]
    try:
        run_bsk("navigate", "--session", session, route)
        time.sleep(portal.get("wait_s", 2))
        # If route is a form, we could re-submit; navigation alone to an authed route
        # generates the activity that refreshes Laravel's session TTL.
        return True
    except Exception as e:
        log(f"  kick error: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--portal", required=True, help="key in config/portals.json")
    ap.add_argument("--interval-min", type=int, default=20)
    ap.add_argument("--session", default="", help="reuse an existing bsk session id")
    ap.add_argument("--once", action="store_true", help="run one keepalive cycle then exit")
    args = ap.parse_args()

    if not PORTALS.exists():
        log(f"ERROR: {PORTALS} missing"); return 2
    portals = json.loads(PORTALS.read_text())
    portal = portals.get(args.portal)
    if not portal:
        log(f"ERROR: portal '{args.portal}' not in {PORTALS}"); return 2

    session = ensure_session(portal, args.session)
    log(f"[{portal['name']}] keepalive starting — interval={args.interval_min}m, session={session}")

    while True:
        try:
            if not alive(portal, session):
                log(f"[{portal['name']}] DEAD — session lost (login wall). STOPPING.")
                log("  HUMAN REQUIRED: log back in, then restart this timer.")
                # on death, stop — do not spam
                return 1
            ok = kick(portal, session)
            log(f"[{portal['name']}] kick {'OK' if ok else 'FAIL'} @ {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z")
        except Exception as e:
            log(f"[{portal['name']}] loop error (non-fatal): {e}")
        if args.once:
            return 0
        time.sleep(args.interval_min * 60)


if __name__ == "__main__":
    sys.exit(main())
