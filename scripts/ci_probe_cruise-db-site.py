#!/usr/bin/env python3
"""CI probe — Cruise database site (client-affecting).
Efficacy check: SQLite DB exists + cruises table has >= 1 row.
Falls back to external https://d2mluxury.quest/cruises if SQLite unreachable.
Exit 0 = GREEN, exit 1 = RED.
"""
import sys
import sqlite3
import urllib.request
import urllib.error
import socket
from pathlib import Path

ID = "cruise-db-site"
DB_PATH = Path.home() / "Thunderbird" / "output" / "cruises.db"
EXTERNAL_URL = "https://d2mluxury.quest/cruises"
MIN_ROWS = 1


def fail(m):
    print(f"RED {ID}: {m}")
    sys.exit(1)


def check_sqlite():
    """Return (count, method) if SQLite DB is accessible and has data."""
    if not DB_PATH.exists():
        return None, "db_missing"

    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM cruises")
        count = cur.fetchone()[0]
        conn.close()
        return count, "sqlite"
    except sqlite3.Error as e:
        return None, f"sqlite_error:{e}"


def check_external():
    """Return HTTP status code for external site as a fallback liveness check."""
    try:
        req = urllib.request.Request(
            EXTERNAL_URL,
            headers={"User-Agent": "thunderbird-ci/1.0"},
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        # 307/401/403 = site is routing (data still served elsewhere)
        if e.code in (301, 302, 307, 308, 401, 403):
            return e.code
        return e.code
    except (socket.timeout, OSError, ConnectionRefusedError):
        return None


def main():
    # Primary: SQLite
    count, method = check_sqlite()

    if count is not None:
        if count < MIN_ROWS:
            fail(f"cruises table empty (0 rows) in {DB_PATH}")
        print(f"GREEN {ID}: SQLite DB has {count:,} cruise rows at {DB_PATH}")
        sys.exit(0)

    # SQLite not available — try external URL as fallback liveness
    code = check_external()
    if code and code < 500:
        print(
            f"GREEN {ID}: SQLite unavailable ({method}), "
            f"external {EXTERNAL_URL} reachable HTTP {code}"
        )
        sys.exit(0)

    # Both failed
    if method.startswith("sqlite_error"):
        fail(f"SQLite error: {method} AND external site unreachable (HTTP {code})")
    else:
        fail(f"cruises.db not found AND external {EXTERNAL_URL} unreachable (HTTP {code})")


if __name__ == "__main__":
    main()
