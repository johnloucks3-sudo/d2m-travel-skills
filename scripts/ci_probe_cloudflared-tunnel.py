#!/usr/bin/env python3
"""CI probe — cloudflared tunnel to d2mluxury.quest.
Efficacy check: cloudflared.service active + external domain reachable (any non-5xx).
Exit 0 = GREEN, exit 1 = RED.
"""
import subprocess
import sys
import urllib.request
import urllib.error
import socket

ID = "cloudflared-tunnel"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def check_service():
    """Verify cloudflared.service (user unit) is active."""
    r = subprocess.run(
        ["systemctl", "--user", "is-active", "cloudflared.service"],
        capture_output=True, text=True, timeout=10
    )
    if r.stdout.strip() != "active":
        fail(f"cloudflared.service not active (state={r.stdout.strip()!r})")


def check_tunnel():
    """Verify the tunnel is live by hitting the external domain.
    200 or 401 or 403 = tunnel is routing (content gating is app-level, not tunnel failure).
    5xx or connection error = tunnel is broken.
    """
    url = "https://d2mluxury.quest/"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "thunderbird-ci/1.0"},
            method="GET"
        )
        # Don't follow redirects blindly — catch the initial response code
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        with opener.open(req, timeout=12) as resp:
            code = resp.status
            return code
    except urllib.error.HTTPError as e:
        # 401/403 = tunnel working, app is auth-gating
        if e.code in (200, 401, 403):
            return e.code
        if 500 <= e.code <= 599:
            fail(f"Tunnel returning {e.code} — origin/tunnel error on d2mluxury.quest")
        return e.code  # 3xx caught here as error if no redirect handler
    except (socket.timeout, OSError, ConnectionRefusedError) as e:
        fail(f"Cannot reach d2mluxury.quest — tunnel down or DNS failure: {e}")


def main():
    check_service()
    code = check_tunnel()
    print(f"GREEN {ID}: service active, d2mluxury.quest reachable HTTP {code}")
    sys.exit(0)


if __name__ == "__main__":
    main()
