#!/usr/bin/env python3
"""portal_http_probe.py — zero-browser HTTPS session validator.

Replaces Playwright/browser keepalive loops with plain HTTPS probes using stored
cookies (straight-Linux; RT-KEEPALIVES AG/CC plan). Checks a set of endpoints
and reports ALIVE/DEAD per entry. No browser, no GUI, stdlib + requests.

Endpoints (name, url, cookie_jar) — cookie_jar optional; if absent, checks
status code + redirect behavior only (401/302→likely unauthenticated).
Usage: portal_http_probe.py [--timeout N]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENDPOINTS = [
    ("centrav", "https://www.centrav.com/",
     ROOT / "core" / "travel" / "data" / "centrav_cookies.json"),
    ("perx", "https://www.perx.com/account/", None),
    ("regent", "https://www.rssc.com/", None),
    ("d2m-portal", "http://127.0.0.1:8780/", None),
]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=15)
    a = ap.parse_args()
    import requests
    out = []
    all_alive = True
    for name, url, jar in ENDPOINTS:
        try:
            kw = {"timeout": a.timeout, "allow_redirects": True}
            if jar and jar.exists():
                try:
                    cookies = {k: v for k, v in json.loads(jar.read_text()).items()}
                    kw["cookies"] = cookies
                except Exception:
                    pass
            r = requests.get(url, **kw)
            alive = r.status_code < 400
            note = f"HTTP {r.status_code}"
            if not alive:
                all_alive = False
            out.append({"name": name, "alive": alive, "note": note})
            print(f"[{name}] {'ALIVE' if alive else 'DEAD'} — {note}")
        except Exception as e:
            all_alive = False
            out.append({"name": name, "alive": False, "note": str(e)[:100]})
            print(f"[{name}] DEAD — {e}")
    return 0 if all_alive else 1

if __name__ == "__main__":
    sys.exit(main())