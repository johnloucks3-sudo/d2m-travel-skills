#!/usr/bin/env python3
"""
chrome_cdp_health.py — Thunderbird Chrome CDP health check + watchdog.

Checks port 9222, restarts chrome-debug.service if down, updates hale_state.json.
Safe to call from systemd timer or on-demand.

Exit codes: 0=ONLINE, 1=RESTARTED (was down, service restarted), 2=FAILED
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

CDP_BASE = "http://127.0.0.1:9222"
SERVICE = "chrome-debug.service"
HALE_STATE = Path("/home/john/Thunderbird/hale_state.json")
TIMEOUT = 3


def _cdp_ok() -> bool:
    try:
        r = requests.get(f"{CDP_BASE}/json/version", timeout=TIMEOUT)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _get_tabs() -> list[dict]:
    try:
        r = requests.get(f"{CDP_BASE}/json", timeout=TIMEOUT)
        return r.json() if r.ok else []
    except requests.RequestException:
        return []


def _service_restart() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", SERVICE],
            capture_output=True, timeout=20,
        )
        return result.returncode == 0
    except Exception:
        return False


def _wait_for_cdp(attempts: int = 6, delay: float = 2.0) -> bool:
    import time
    for _ in range(attempts):
        if _cdp_ok():
            return True
        time.sleep(delay)
    return False


def _update_hale_state(status: str) -> None:
    if not HALE_STATE.exists():
        return
    try:
        state = json.loads(HALE_STATE.read_text(encoding="utf-8"))
        ts = datetime.now(timezone.utc).isoformat()
        # Update both locations where chrome status is stored
        if "system_health" in state:
            if status == "ONLINE":
                state["system_health"]["chrome_debug"] = f"ONLINE — port 9222 responding"
            else:
                state["system_health"]["chrome_debug"] = f"OFFLINE — port 9222 not responding"
        if "wing_health" in state:
            state["wing_health"]["chrome_debug_port_9222"] = status
            state["wing_health"]["last_health_check"] = ts
        state["_meta"]["last_updated"] = ts
        HALE_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"[chrome_cdp_health] hale_state update failed: {exc}", file=sys.stderr)


def main() -> int:
    if _cdp_ok():
        tabs = _get_tabs()
        tab_summary = f"{len(tabs)} tab(s): " + ", ".join(
            t.get("url", "?")[:60] for t in tabs[:3]
        )
        print(f"[chrome_cdp_health] ONLINE — Chrome 9222 responding. {tab_summary}")
        _update_hale_state("ONLINE")
        return 0

    # Port not responding — probe only, NO auto-restart
    # Auto-restart disabled 2026-06-27: was causing Chrome to spawn a visible window every 60s
    # (infra_bot RED loop → always DUE → restart every tick). Start chrome-debug manually when needed.
    print(f"[chrome_cdp_health] OFFLINE — port 9222 not responding (auto-restart disabled)")
    _update_hale_state("OFFLINE")
    return 2


if __name__ == "__main__":
    sys.exit(main())
