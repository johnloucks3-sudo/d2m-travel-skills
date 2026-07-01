#!/usr/bin/env python3
"""CI EFFICACY PROBE — Infisical (self-hosted secrets manager).
GREEN = container up AND HTTP/health served on :8899. RED otherwise.
"""
import sys, urllib.request

PORT = 8899
# Infisical exposes /api/status; fall back to root.
ENDPOINTS = [f"http://localhost:{PORT}/api/status", f"http://localhost:{PORT}/"]


def fail(m):
    print(f"RED infisical: {m}")
    sys.exit(1)


def main():
    last = ""
    for url in ENDPOINTS:
        try:
            r = urllib.request.urlopen(url, timeout=8)
            print(f"GREEN infisical: HTTP {r.status} on {url.split(str(PORT))[-1] or '/'}")
            sys.exit(0)
        except Exception as e:
            last = str(e)
            if "HTTP Error" in last:  # app up, endpoint just auth/404
                print(f"GREEN infisical: app up on :{PORT} ({last[:40]})")
                sys.exit(0)
            continue
    if "refused" in last.lower() or "timed out" in last.lower():
        fail(f"not reachable on :{PORT} — stack down? ({last[:60]})")
    fail(last[:80])


if __name__ == "__main__":
    main()
