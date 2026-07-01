#!/usr/bin/env python3
"""CI probe — Reverie application (frontend-only).
Efficacy check: reverie-frontend.service active and responding on port 8888.

reverie-api.service RETIRED 2026-07-01 (verified-dead: cloudflared route
api-reverie:8802 pruned as dead 2026-06-22 per MISSION-259, venv deleted,
unit was in a 203/EXEC restart loop). Frontend serves static itinerary UI
independently. See hale_decisions.md 2026-07-01.

Exit 0 = GREEN, exit 1 = RED.
"""
import subprocess
import sys
import urllib.request
import urllib.error
import socket

ID = "reverie-app"
FRONTEND_PORT = 8888
FRONTEND_PATH = "/"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def service_active(unit):
    """Return True if the user service unit is active."""
    r = subprocess.run(
        ["systemctl", "--user", "is-active", unit],
        capture_output=True, text=True, timeout=10
    )
    return r.stdout.strip() == "active"


def http_check(port, paths):
    """Try each path in order. Return (path, status_code) on first success, or fail."""
    for path in paths:
        url = f"http://127.0.0.1:{port}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "thunderbird-ci/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                return path, resp.status
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404, 405, 422):
                # Server is responding — counts as alive
                return path, e.code
            if 500 <= e.code <= 599:
                fail(f"HTTP {e.code} on port {port}{path} — server error")
        except (ConnectionRefusedError, socket.timeout, OSError):
            fail(f"Cannot connect to port {port} — service not listening")
    fail(f"No path responded successfully on port {port} (tried: {paths})")


def main():
    if not service_active("reverie-frontend.service"):
        fail("reverie-frontend.service not active")

    fe_path, fe_code = http_check(FRONTEND_PORT, [FRONTEND_PATH])

    print(f"GREEN {ID}: frontend HTTP {fe_code} on :{FRONTEND_PORT}{fe_path} (api retired 2026-07-01)")
    sys.exit(0)


if __name__ == "__main__":
    main()
