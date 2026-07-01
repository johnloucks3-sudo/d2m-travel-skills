"""
email_audit.py — SQLite audit trail for the Thunderbird email pipeline.

DB: core/email/email_audit.db  (gitignored — orchestrator adds to .gitignore)
Schema: email_events table with unique constraint on (message_id, action_taken)
        for the three irreversible actions, preventing duplicate mission-creates
        and duplicate sends.

Thread-safe: one connection per call, WAL journal mode.

Usage (module):
    from core.email.email_audit import record, already_done, history, stats

Usage (CLI):
    python3 core/email/email_audit.py --history <message_id>
    python3 core/email/email_audit.py --stats [--hours 24]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Repo-root anchor (runs as script from any cwd) ─────────────────────────
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parent.parent.parent   # core/email/email_audit.py → repo root
DB_PATH = _REPO_ROOT / "core" / "email" / "email_audit.db"

# Actions that MUST be unique per message_id (INSERT OR IGNORE guards these)
_UNIQUE_ACTIONS = frozenset({"mission_created", "reply_sent", "ack_sent"})

_DDL = """
CREATE TABLE IF NOT EXISTS email_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id     TEXT    NOT NULL,
    thread_id      TEXT,
    source         TEXT    NOT NULL,   -- sweep|ingest|inbox|dispatch|inbox-zero|n8n
    classified_as  TEXT,
    action_taken   TEXT,
    outcome        TEXT    DEFAULT 'ok',  -- ok|failed|skipped-duplicate
    detail         TEXT    DEFAULT '',
    ts             TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_msg
    ON email_events(message_id);

-- Unique index only on the three irreversible actions:
-- INSERT OR IGNORE will silently no-op on duplicates, so record() returns False.
CREATE UNIQUE INDEX IF NOT EXISTS idx_action_once
    ON email_events(message_id, action_taken)
    WHERE action_taken IN ('mission_created', 'reply_sent', 'ack_sent');
"""


def _connect() -> sqlite3.Connection:
    """Open a connection with WAL mode enabled. Caller must close."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.row_factory = sqlite3.Row
    con.executescript(_DDL)
    return con


def record(
    message_id: str,
    source: str,
    *,
    thread_id: str | None = None,
    classified_as: str | None = None,
    action_taken: str | None = None,
    outcome: str = "ok",
    detail: str = "",
) -> bool:
    """
    Insert an audit event.

    For action_taken in {mission_created, reply_sent, ack_sent}: uses
    INSERT OR IGNORE so duplicates are silently dropped.

    Returns True if the row was inserted, False if it was a suppressed duplicate.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    con = _connect()
    try:
        if action_taken in _UNIQUE_ACTIONS:
            cur = con.execute(
                """
                INSERT OR IGNORE INTO email_events
                    (message_id, thread_id, source, classified_as,
                     action_taken, outcome, detail, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, thread_id, source, classified_as,
                 action_taken, outcome, detail, ts),
            )
            con.commit()
            inserted = cur.rowcount == 1
        else:
            con.execute(
                """
                INSERT INTO email_events
                    (message_id, thread_id, source, classified_as,
                     action_taken, outcome, detail, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (message_id, thread_id, source, classified_as,
                 action_taken, outcome, detail, ts),
            )
            con.commit()
            inserted = True
        return inserted
    finally:
        con.close()


def already_done(message_id: str, action: str) -> bool:
    """
    Return True if (message_id, action) already exists in the audit trail.

    Fast path before the irreversible call. The real safety net is INSERT OR
    IGNORE in record(), but checking here avoids the trip to the DB layer
    inside mission-board or Gmail send when we can short-circuit early.
    """
    con = _connect()
    try:
        cur = con.execute(
            "SELECT 1 FROM email_events WHERE message_id=? AND action_taken=? LIMIT 1",
            (message_id, action),
        )
        return cur.fetchone() is not None
    finally:
        con.close()


def history(message_id: str) -> list[dict[str, Any]]:
    """Return all audit rows for a message_id, oldest first."""
    con = _connect()
    try:
        cur = con.execute(
            """
            SELECT id, message_id, thread_id, source, classified_as,
                   action_taken, outcome, detail, ts
            FROM email_events
            WHERE message_id = ?
            ORDER BY id ASC
            """,
            (message_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        con.close()


def stats(since_hours: float = 24) -> dict[str, Any]:
    """
    Return summary counts for the last since_hours hours.
    Counts by classified_as, action_taken, and outcome.
    """
    cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # SQLite datetime() is UTC; subtract hours via modifier
    con = _connect()
    try:
        by_class = {}
        for row in con.execute(
            """
            SELECT classified_as, COUNT(*) as n
            FROM email_events
            WHERE ts >= datetime(?, ?, ?)
            GROUP BY classified_as
            """,
            (cutoff, f"-{int(since_hours)} hours", "utc"),
        ):
            by_class[row["classified_as"] or "none"] = row["n"]

        by_action = {}
        for row in con.execute(
            """
            SELECT action_taken, COUNT(*) as n
            FROM email_events
            WHERE ts >= datetime(?, ?, ?)
            GROUP BY action_taken
            """,
            (cutoff, f"-{int(since_hours)} hours", "utc"),
        ):
            by_action[row["action_taken"] or "none"] = row["n"]

        by_outcome = {}
        for row in con.execute(
            """
            SELECT outcome, COUNT(*) as n
            FROM email_events
            WHERE ts >= datetime(?, ?, ?)
            GROUP BY outcome
            """,
            (cutoff, f"-{int(since_hours)} hours", "utc"),
        ):
            by_outcome[row["outcome"] or "none"] = row["n"]

        total = sum(by_outcome.values())
        return {
            "since_hours": since_hours,
            "total_events": total,
            "by_classified_as": by_class,
            "by_action_taken": by_action,
            "by_outcome": by_outcome,
        }
    finally:
        con.close()


# ── CLI ─────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Email audit trail — query the SQLite log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 core/email/email_audit.py --stats\n"
            "  python3 core/email/email_audit.py --stats --hours 48\n"
            "  python3 core/email/email_audit.py --history 18b4c3d2f1a0e5\n"
        ),
    )
    parser.add_argument("--history", metavar="MSG_ID",
                        help="Show all audit rows for a message_id")
    parser.add_argument("--stats", action="store_true",
                        help="Show aggregate stats")
    parser.add_argument("--hours", type=float, default=24,
                        help="Lookback window in hours for --stats (default: 24)")
    args = parser.parse_args()

    if args.history:
        rows = history(args.history)
        if not rows:
            print(f"No audit rows for message_id={args.history!r}")
        else:
            print(json.dumps(rows, indent=2))
        return

    if args.stats:
        result = stats(since_hours=args.hours)
        print(json.dumps(result, indent=2))
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    _cli()
