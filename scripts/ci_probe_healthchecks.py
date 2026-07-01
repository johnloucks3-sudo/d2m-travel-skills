#!/usr/bin/env python3
"""CI EFFICACY PROBE — Healthchecks.io (dead-man switch service).
GREEN = container up AND HTTP served on :8123. RED otherwise.
"""
import sys, urllib.request

PORT = 8123
URL = f"http://localhost:{PORT}/"


def fail(m):
    print(f"RED healthchecks: {m}")
    sys.exit(1)


def main():
    try:
        r = urllib.request.urlopen(URL, timeout=8)
        code = r.status
    except Exception as e:
        # Healthchecks redirects / returns 200 or 302 on root; a refused conn = down
        msg = str(e)
        if "Connection refused" in msg or "timed out" in msg:
            fail(f"not reachable on :{PORT} — container down? ({msg[:60]})")
        # Some responses (302/login) raise HTTPError but mean the app IS up
        if "HTTP Error" in msg:
            print(f"GREEN healthchecks: app up on :{PORT} ({msg[:40]})")
            sys.exit(0)
        fail(msg[:80])
    if code in (200, 301, 302):
        print(f"GREEN healthchecks: HTTP {code} on :{PORT}")
        sys.exit(0)
    fail(f"unexpected HTTP {code}")


if __name__ == "__main__":
    main()
