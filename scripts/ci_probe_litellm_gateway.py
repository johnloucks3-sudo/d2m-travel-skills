#!/usr/bin/env python3
"""CI probe — LiteLLM gateway at localhost:4000."""
import sys, requests

try:
    r = requests.get("http://localhost:4000/health", timeout=5)
    # 401 = gateway up (auth required), 200 = open
    if r.status_code in (200, 401):
        print(f"OK: LiteLLM gateway alive ({r.status_code})")
        sys.exit(0)
    print(f"FAIL: unexpected status {r.status_code}")
    sys.exit(1)
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(2)
