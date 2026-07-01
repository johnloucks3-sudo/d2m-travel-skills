#!/usr/bin/env python3
"""CI probe — ttyd terminal-over-browser service.
Efficacy check: ttyd-terminal.service (or ttyd.service) active + HTTP port responds.
Port is discovered from the active unit's ExecStart, defaulting to 3100.
Exit 0 = GREEN, exit 1 = RED.
"""
import subprocess
import sys
import re
import urllib.request
import urllib.error
import socket

ID = "ttyd"
DEFAULT_PORT = 3100
PREFERRED_UNIT = "ttyd-terminal.service"
FALLBACK_UNIT = "ttyd.service"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def active_unit():
    """Return the name of whichever ttyd unit is active, or None."""
    for unit in (PREFERRED_UNIT, FALLBACK_UNIT):
        r = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True, text=True, timeout=10
        )
        if r.stdout.strip() == "active":
            return unit
    return None


def discover_port(unit_name):
    """Extract --port N from the unit's ExecStart line."""
    r = subprocess.run(
        ["systemctl", "--user", "show", unit_name, "--property=ExecStart"],
        capture_output=True, text=True, timeout=10
    )
    m = re.search(r"--port\s+(\d+)", r.stdout)
    if m:
        return int(m.group(1))
    return DEFAULT_PORT


def check_http(port):
    """Hit localhost:<port> — ttyd returns 200 or 401 when alive."""
    url = f"http://127.0.0.1:{port}/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "thunderbird-ci/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        if e.code in (200, 401, 403):
            return e.code
        fail(f"HTTP {e.code} on ttyd port {port}")
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        fail(f"Cannot connect to ttyd on port {port}: {e}")


def main():
    unit = active_unit()
    if unit is None:
        fail(f"Neither {PREFERRED_UNIT} nor {FALLBACK_UNIT} is active")

    port = discover_port(unit)
    code = check_http(port)
    print(f"GREEN {ID}: {unit} active, HTTP {code} on port {port}")
    sys.exit(0)


if __name__ == "__main__":
    main()
