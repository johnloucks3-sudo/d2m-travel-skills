"""SQLite event store for the State Bridge daemon.

Persists session events and session records in WAL mode so the daemon and
session-startup hook can read/write concurrently without locking each other
out. The schema is intentionally narrow — every interesting state change
becomes an `events` row; long-lived session bookkeeping lives in `sessions`.

All public methods are safe to call from any process; each opens its own
short-lived connection. This keeps the API stateless and resilient to daemon
restarts.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

log = logging.getLogger(__name__)

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DEFAULT_DB_PATH = THUNDERBIRD_ROOT / "OpsCenter" / "state_bridge" / "state_bridge.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  entity_type TEXT,
  entity_key TEXT,
  summary TEXT,
  detail_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_type, entity_key);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  model TEXT,
  task_count INTEGER DEFAULT 0,
  open_issues TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
"""


def _utc_now_iso() -> str:
    """ISO-8601 UTC timestamp with seconds precision (matches sqlite datetime())."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class EventStore:
    """Thin SQLite wrapper. Connections are short-lived; WAL mode is set once."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        """Create schema and enable WAL. Idempotent."""
        try:
            with self._connect() as conn:
                conn.executescript(SCHEMA_SQL)
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.commit()
        except sqlite3.DatabaseError as exc:
            log.error("Corrupt SQLite detected at %s: %s — rebuilding.", self.db_path, exc)
            self._rebuild()

    def _rebuild(self) -> None:
        """Move corrupt DB aside and recreate empty."""
        backup = self.db_path.with_suffix(f".corrupt.{int(datetime.now().timestamp())}.db")
        try:
            self.db_path.rename(backup)
            log.warning("Moved corrupt DB to %s", backup)
        except OSError:
            pass
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # --- event operations -------------------------------------------------

    def record_event(
        self,
        session_id: str,
        event_type: str,
        entity_type: str | None = None,
        entity_key: str | None = None,
        summary: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> int:
        """Insert a single event row. Returns the new row id."""
        detail_json = json.dumps(detail, default=str) if detail else None
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO events
                   (session_id, event_type, entity_type, entity_key, summary, detail_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (session_id, event_type, entity_type, entity_key, summary, detail_json, _utc_now_iso()),
            )
            return int(cur.lastrowid or 0)

    def get_events_since(self, timestamp: str | datetime, limit: int = 50) -> list[dict[str, Any]]:
        """Return events strictly newer than `timestamp`, oldest first."""
        if isinstance(timestamp, datetime):
            ts = timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts = timestamp
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE created_at > ?
                   ORDER BY created_at ASC, id ASC
                   LIMIT ?""",
                (ts, limit),
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_events_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_decision_drift(self, entity_key: str) -> list[dict[str, Any]]:
        """Return all `decision` events for an entity, newest first.

        Drift = >1 decision rows for the same entity_key. Caller compares the
        latest detail_json to whatever the live system currently asserts and
        flags the mismatch.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM events
                   WHERE event_type = 'decision' AND entity_key = ?
                   ORDER BY created_at DESC, id DESC""",
                (entity_key,),
            ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def prune_older_than(self, days: int = 30) -> int:
        """Delete non-decision events older than `days`. Returns rows removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM events WHERE created_at < ? AND event_type != 'decision'",
                (cutoff,),
            )
            conn.commit()
            return cur.rowcount or 0

    # --- session operations -----------------------------------------------

    def open_session(self, model: str | None = None) -> str:
        """Create a new session row and return its UUID."""
        sid = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO sessions (id, started_at, model, task_count, open_issues)
                   VALUES (?, ?, ?, 0, '[]')""",
                (sid, _utc_now_iso(), model),
            )
        return sid

    def close_session(self, session_id: str, issues: list[str] | None = None) -> None:
        """Mark a session ended and persist any unfinished issues."""
        issues_json = json.dumps(issues or [])
        with self._connect() as conn:
            conn.execute(
                """UPDATE sessions
                   SET ended_at = ?, open_issues = ?
                   WHERE id = ?""",
                (_utc_now_iso(), issues_json, session_id),
            )

    def get_latest_session(self, exclude_id: str | None = None) -> dict[str, Any] | None:
        """Return the most recent session row, optionally excluding the current one."""
        with self._connect() as conn:
            if exclude_id:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE id != ? ORDER BY started_at DESC LIMIT 1",
                    (exclude_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM sessions ORDER BY started_at DESC LIMIT 1"
                ).fetchone()
        return self._row_to_session(row) if row else None

    def get_session_chain(self, last_n: int = 5) -> list[dict[str, Any]]:
        """Return the last N sessions (newest first) with event counts."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT s.*, COUNT(e.id) AS event_count
                   FROM sessions s
                   LEFT JOIN events e ON e.session_id = s.id
                   GROUP BY s.id
                   ORDER BY s.started_at DESC
                   LIMIT ?""",
                (last_n,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            sess = self._row_to_session(r)
            if sess is not None:
                sess["event_count"] = r["event_count"]
                out.append(sess)
        return out

    def increment_task_count(self, session_id: str, delta: int = 1) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET task_count = task_count + ? WHERE id = ?",
                (delta, session_id),
            )

    # --- helpers ----------------------------------------------------------

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        if d.get("detail_json"):
            try:
                parsed = json.loads(d["detail_json"])
                d["detail"] = parsed if isinstance(parsed, dict) else None
            except (json.JSONDecodeError, TypeError):
                d["detail"] = None
        else:
            d["detail"] = None
        return d

    @staticmethod
    def _row_to_session(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        d = dict(row)
        if d.get("open_issues"):
            try:
                d["open_issues_list"] = json.loads(d["open_issues"])
            except (json.JSONDecodeError, TypeError):
                d["open_issues_list"] = []
        else:
            d["open_issues_list"] = []
        return d


if __name__ == "__main__":  # smoke test
    logging.basicConfig(level=logging.INFO)
    store = EventStore()
    sid = store.open_session(model="test")
    store.record_event(sid, "checkpoint", "test", "smoke", "smoke test ok", {"k": 1})
    print("session:", sid)
    print("events:", store.get_events_for_session(sid))
    store.close_session(sid, ["nothing pending"])
    print("chain:", store.get_session_chain(3))
