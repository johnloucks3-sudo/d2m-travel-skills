#!/usr/bin/env python3
"""
Qdrant Docker Watchdog — MISSION-126
====================================
A7 Sterling build. Detects an unhealthy or stopped Qdrant container,
restarts it, and alerts the Wing via the relay.

HEALTH PROBE: GET /collections  (NOT /health — Qdrant has no /health on
this build; /collections returns 200 when the vector DB is serving. See
MEMORY.md "Qdrant semantic memory".)

Container name is auto-detected from a candidate list so the watchdog
tracks whatever container is actually serving 6333, not a hard-coded name.
(Root cause of M-126: the systemd qdrant.service referenced
'thunderbird-qdrant' while the live container is 'qdrant'.)

Design:
  1. Probe http://localhost:6333/collections
  2. On failure → confirm with N retries (transient-blip guard)
  3. If still down → docker restart (or start if exited) the container
  4. Re-probe; alert Commander via relay_send on outcome
  5. Write status JSON for the AM brief / dashboard

Usage:
  python3 core/memory/qdrant_docker_watchdog.py            # one watchdog cycle
  python3 core/memory/qdrant_docker_watchdog.py --dry-run  # probe only, no restart
  python3 core/memory/qdrant_docker_watchdog.py --self-test # no docker, no alert

Exit codes: 0 healthy/recovered · 1 recovery failed · 2 probe-only unhealthy
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parent.parent.parent
RELAY_SCRIPT = THUNDERBIRD / "OpsCenter" / "relay_send.py"
STATUS_FILE = THUNDERBIRD / "OpsCenter" / "qdrant_watchdog_status.json"
LOG_FILE = THUNDERBIRD / "logs" / "qdrant_watchdog.log"

QDRANT_URL = "http://localhost:6333/collections"
# Candidate container names, in priority order. First one that exists wins.
CONTAINER_CANDIDATES = ["qdrant", "thunderbird-qdrant"]

PROBE_TIMEOUT = 8          # seconds per HTTP probe
CONFIRM_RETRIES = 3        # confirmations before declaring DOWN
CONFIRM_INTERVAL = 5       # seconds between confirmation probes
POST_RESTART_WAIT = 12     # seconds to let the container come up
POST_RESTART_PROBES = 5    # probes after restart before giving up


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    line = f"[{_now()}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def probe() -> bool:
    """Return True if Qdrant answers /collections with HTTP 200."""
    try:
        req = urllib.request.Request(QDRANT_URL, method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"probe failed: {e}")
        return False


def docker(*args: str, timeout: int = 60) -> tuple[int, str]:
    """Run a docker subcommand; return (returncode, combined output)."""
    try:
        p = subprocess.run(
            ["docker", *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "docker binary not found"
    except subprocess.TimeoutExpired:
        return 124, f"docker {' '.join(args)} timed out"


def find_container() -> str | None:
    """Find the qdrant container name (running or stopped)."""
    rc, out = docker("ps", "-a", "--format", "{{.Names}}")
    if rc != 0:
        log(f"docker ps failed: {out}")
        return None
    names = set(out.splitlines())
    for cand in CONTAINER_CANDIDATES:
        if cand in names:
            return cand
    return None


def container_running(name: str) -> bool:
    rc, out = docker("ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}")
    return rc == 0 and name in out.splitlines()


def restart_container(name: str) -> bool:
    """Restart a running container, or start a stopped one."""
    if container_running(name):
        log(f"restarting running container '{name}'")
        rc, out = docker("restart", name, timeout=90)
    else:
        log(f"starting stopped container '{name}'")
        rc, out = docker("start", name, timeout=90)
    if rc != 0:
        log(f"docker restart/start failed: {out}")
        return False
    return True


def relay_alert(message: str, to: str = "CC", priority: str = "normal") -> None:
    """Alert the Wing via relay_send.py (protected file — we only CALL it).

    CHANNEL DISCIPLINE (SO — D2MC2C = action-required only):
      to="CC"        → relay feed / D2M Channels — informational. Use for
                       successful self-heals and transient blips. NO Commander page.
      to="COMMANDER" → D2MC2C urgent page. Use ONLY when manual intervention
                       is actually required (no container, restart failed,
                       restarted-but-no-recovery).
    """
    if not RELAY_SCRIPT.exists():
        log(f"relay script missing, alert not sent: {message}")
        return
    try:
        subprocess.run(
            [sys.executable, str(RELAY_SCRIPT),
             "--from", "STERLING", "--to", to,
             "--priority", priority, message],
            timeout=20, capture_output=True, text=True,
        )
        log(f"relay alert sent [{to}/{priority}]: {message[:80]}")
    except Exception as e:
        log(f"relay alert failed: {e}")


def write_status(state: str, detail: dict) -> None:
    payload = {
        "service": "qdrant",
        "checked_at": _now(),
        "state": state,            # HEALTHY | RECOVERED | DOWN | UNKNOWN
        "probe_url": QDRANT_URL,
        **detail,
    }
    try:
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATUS_FILE.write_text(json.dumps(payload, indent=2))
    except Exception as e:
        log(f"status write failed: {e}")


def watchdog_cycle(dry_run: bool = False) -> int:
    # 1. First probe
    if probe():
        log("HEALTHY — Qdrant /collections returned 200")
        write_status("HEALTHY", {"action": "none"})
        return 0

    # 2. Confirm down (transient-blip guard)
    for i in range(CONFIRM_RETRIES):
        time.sleep(CONFIRM_INTERVAL)
        if probe():
            log(f"recovered on confirmation probe {i + 1} — transient blip")
            write_status("HEALTHY", {"action": "none", "note": "transient blip"})
            return 0
    log(f"DOWN confirmed after {CONFIRM_RETRIES} retries")

    if dry_run:
        log("dry-run: not restarting")
        write_status("DOWN", {"action": "dry-run, no restart"})
        return 2

    # 3. Locate + restart container
    name = find_container()
    if not name:
        msg = "🔴 Qdrant DOWN and no container found (candidates: " \
              + ", ".join(CONTAINER_CANDIDATES) + "). Manual intervention required."
        log(msg)
        relay_alert(msg, to="COMMANDER", priority="high")
        write_status("DOWN", {"action": "no container found",
                              "candidates": CONTAINER_CANDIDATES})
        return 1

    if not restart_container(name):
        msg = f"🔴 Qdrant DOWN — restart of container '{name}' FAILED. " \
              "Manual intervention required."
        log(msg)
        relay_alert(msg, to="COMMANDER", priority="high")
        write_status("DOWN", {"action": "restart failed", "container": name})
        return 1

    # 4. Re-probe after restart
    for i in range(POST_RESTART_PROBES):
        time.sleep(POST_RESTART_WAIT if i == 0 else CONFIRM_INTERVAL)
        if probe():
            msg = f"✅ Qdrant was DOWN — watchdog restarted container " \
                  f"'{name}' and it recovered (probe {i + 1})."
            log(msg)
            # Self-heal succeeded → informational only. NO Commander page.
            relay_alert(msg, to="CC", priority="low")
            write_status("RECOVERED", {"action": "restarted", "container": name,
                                       "recovery_probe": i + 1})
            return 0

    msg = f"🔴 Qdrant DOWN — restarted container '{name}' but it did NOT " \
          "recover. Manual intervention required."
    log(msg)
    relay_alert(msg, to="COMMANDER", priority="high")
    write_status("DOWN", {"action": "restarted, no recovery", "container": name})
    return 1


def self_test() -> int:
    """No docker, no alerts — exercise probe + status write only."""
    print("=== SELF TEST ===")
    healthy = probe()
    print(f"probe() → {'HEALTHY (200)' if healthy else 'NO RESPONSE'}")
    name = find_container()
    print(f"find_container() → {name or 'NONE'}")
    if name:
        print(f"container_running('{name}') → {container_running(name)}")
    write_status("HEALTHY" if healthy else "UNKNOWN",
                 {"action": "self-test", "container": name})
    print(f"status written → {STATUS_FILE}")
    return 0 if healthy else 2


def main() -> None:
    ap = argparse.ArgumentParser(description="Qdrant Docker watchdog (M-126)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Probe + confirm only; never restart")
    ap.add_argument("--self-test", action="store_true",
                    help="Probe + container discovery only; no restart, no alert")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    sys.exit(watchdog_cycle(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
