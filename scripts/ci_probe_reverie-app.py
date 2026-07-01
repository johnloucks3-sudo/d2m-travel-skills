#!/usr/bin/env python3
"""CI probe — Reverie application (API + frontend).
Efficacy check: BOTH reverie-api.service (port 8802) AND reverie-frontend.service (port 8888)
must be active and respond over HTTP.
Exit 0 = GREEN, exit 1 = RED.
"""
import subprocess
import sys
import urllib.request
import urllib.error
import socket

ID = "reverie-app"
API_PORT = 8802
FRONTEND_PORT = 8888
API_PATHS = ["/api/health", "/api/docs", "/", ]
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
            # Connection refused means port is not listening — keep trying paths? No, same port.
            fail(f"Cannot connect to port {port} — service not listening")
    fail(f"No path responded successfully on port {port} (tried: {paths})")


def main():
    errors = []

    # Check API service
    api_active = service_active("reverie-api.service")
    if not api_active:
        errors.append("reverie-api.service not active")

    # Check frontend service
    fe_active = service_active("reverie-frontend.service")
    if not fe_active:
        errors.append("reverie-frontend.service not active")

    if errors:
        fail("; ".join(errors))

    # Check API HTTP
    api_path, api_code = http_check(API_PORT, API_PATHS)

    # Check frontend HTTP
    fe_path, fe_code = http_check(FRONTEND_PORT, [FRONTEND_PATH])

    print(
        f"GREEN {ID}: API HTTP {api_code} on :{API_PORT}{api_path}; "
        f"frontend HTTP {fe_code} on :{FRONTEND_PORT}{fe_path}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
