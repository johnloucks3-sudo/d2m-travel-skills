#!/usr/bin/env python3
"""CI probe — Qdrant vector database (Docker-based).
Efficacy check: GET /collections returns 200 AND includes collection 'thunderbird_memories'.
NOTE: qdrant.service is a Docker oneshot (docker start qdrant) — systemctl shows
      inactive/dead in normal operation. Probe the container directly via HTTP.
Exit 0 = GREEN, exit 1 = RED.
"""
import sys
import json
import urllib.request
import urllib.error
import socket

ID = "qdrant"
QDRANT_URL = "http://localhost:6333"
REQUIRED_COLLECTION = "thunderbird_memories"


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def main():
    url = f"{QDRANT_URL}/collections"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "thunderbird-ci/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.status
            if code != 200:
                fail(f"GET /collections returned HTTP {code} (expected 200)")
            try:
                data = json.loads(resp.read().decode())
            except json.JSONDecodeError as e:
                fail(f"Cannot parse /collections response: {e}")
    except urllib.error.HTTPError as e:
        fail(f"HTTP {e.code} on {url}")
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        fail(f"Cannot connect to Qdrant on port 6333 — container likely down: {e}")

    # Verify required collection is present
    status = data.get("status", "")
    collections = data.get("result", {}).get("collections", [])
    names = [c.get("name", "") for c in collections]

    if REQUIRED_COLLECTION not in names:
        fail(
            f"Collection '{REQUIRED_COLLECTION}' not found; "
            f"present collections: {names or '(none)'}"
        )

    print(
        f"GREEN {ID}: Qdrant HTTP 200, status={status!r}, "
        f"collection '{REQUIRED_COLLECTION}' present ({len(names)} total)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
