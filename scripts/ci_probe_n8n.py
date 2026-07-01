#!/usr/bin/env python3
"""CI probe — n8n workflow automation service.
Efficacy check: service active + HTTP endpoint responds with 200.
Exit 0 = GREEN, exit 1 = RED.
"""
import subprocess
import sys
import socket
import urllib.request
import urllib.error

ID = "n8n"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def check_service():
    """Verify n8n.service is active (user unit)."""
    r = subprocess.run(
        ["systemctl", "--user", "is-active", "n8n.service"],
        capture_output=True, text=True, timeout=10
    )
    if r.stdout.strip() != "active":
        fail(f"n8n.service not active (state={r.stdout.strip()!r})")


def check_http():
    """Verify n8n HTTP endpoint actually responds."""
    # Try /healthz first, fall back to /
    for path in ["/healthz", "/"]:
        url = f"http://localhost:5678{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "thunderbird-ci/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                code = resp.status
                if code == 200:
                    return path, code
                # 404 on /healthz means endpoint missing — try next
        except urllib.error.HTTPError as e:
            if e.code not in (404, 405):
                fail(f"HTTP {e.code} on {url}")
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            fail(f"Cannot connect to n8n on port 5678: {e}")
    fail("n8n HTTP endpoint not reachable on /healthz or /")


def main():
    check_service()
    path, code = check_http()
    print(f"GREEN {ID}: service active, HTTP {code} on {path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
