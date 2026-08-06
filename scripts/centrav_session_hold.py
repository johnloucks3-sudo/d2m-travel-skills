#!/usr/bin/env python3
"""
centrav_session_hold.py — hold ONE long-lived bsk session for Centrav scans.

WHY (AG ruling 2026-08-06, ATO-006-08): fresh bsk sessions hit Centrav's
"error report id" page because server-side session state isn't initialized in
a new context. A single keepalive-owned session + a heartbeat every 180s
defeats the ~5min bsk idle-reap AND keeps the authenticated state warm.

Usage:
  python3 scripts/centrav_session_hold.py           # foreground (systemd oneshot/service)
  python3 scripts/centrav_session_hold.py --once     # one heartbeat then exit

Runs continuously: pings the session every 180s. Writes the live session id
to core/travel/data/centrav_session_hold.json so scanners reuse it.

Exit codes: 0 = healthy heartbeat, 2 = session died (needs human re-login).
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BSK = "/home/john/.local/bin/bsk"
ROOT = Path("/home/john/Thunderbird")
STATE = ROOT / "core" / "travel" / "data" / "centrav_session_hold.json"
HEARTBEAT_S = 180


def log(m: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {m}", flush=True)


def run_bsk(*args, timeout=30) -> str:
    r = subprocess.run([BSK, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200])
    return r.stdout


def ensure_session() -> str:
    """Reuse the held session if alive, else start a fresh one and warm it."""
    sid = ""
    try:
        if STATE.exists():
            d = json.loads(STATE.read_text())
            sid = d.get("session", "")
    except Exception:
        pass
    if sid:
        try:
            run_bsk("evaluate", "1", "--session", sid, timeout=15)
            return sid
        except Exception:
            log(f"held session {sid} dead — starting fresh")
    sid = run_bsk("session", "start").strip()
    log(f"new session {sid}")
    # warm: navigate to Centrav so server-side state initializes
    try:
        run_bsk("navigate", "--session", sid, "https://www.centrav.com/fares", timeout=45)
    except Exception as e:
        log(f"warm nav warning: {e}")
    time.sleep(3)
    STATE.write_text(json.dumps({"session": sid, "held_since": datetime.now(timezone.utc).isoformat()}))
    return sid


def heartbeat(sid: str) -> bool:
    """Lightweight ping that keeps the session alive + warm."""
    try:
        run_bsk("evaluate", "1", "--session", sid, timeout=15)
        # a real page touch prevents server-side session expiry
        run_bsk("evaluate", "document.visibilityState", "--session", sid, timeout=15)
        return True
    except Exception as e:
        log(f"heartbeat failed: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--session", default="", help="pin an explicit session id")
    args = ap.parse_args()

    sid = args.session or ensure_session()
    STATE.write_text(json.dumps({"session": sid, "held_since": datetime.now(timezone.utc).isoformat()}))

    if args.once:
        ok = heartbeat(sid)
        log(f"heartbeat {'OK' if ok else 'FAIL'} on {sid}")
        return 0 if ok else 2

    log(f"holding session {sid} — heartbeat every {HEARTBEAT_S}s")
    while True:
        time.sleep(HEARTBEAT_S)
        if not heartbeat(sid):
            log(f"session {sid} lost — restarting fresh")
            sid = ensure_session()
            STATE.write_text(json.dumps({"session": sid, "held_since": datetime.now(timezone.utc).isoformat()}))


if __name__ == "__main__":
    sys.exit(main())
