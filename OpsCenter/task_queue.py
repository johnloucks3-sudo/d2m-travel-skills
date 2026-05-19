"""
task_queue.py — Centralized SQLite task queue for Thunderbird OS
================================================================
Single source of truth for all task submission and retrieval.
WAL mode ensures safe concurrent writes from C2 bot, OpenCode, Claude, cron.

Usage:
    from OpsCenter.task_queue import submit_task, get_pending_tasks, ...
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("/home/john/Thunderbird/OpsCenter/task_queue.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id           TEXT PRIMARY KEY,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    priority     INTEGER NOT NULL DEFAULT 5,
    task_type    TEXT NOT NULL DEFAULT 'general',
    content      TEXT NOT NULL,
    assigned_to  TEXT NOT NULL DEFAULT 'auto',
    status       TEXT NOT NULL DEFAULT 'pending',
    source       TEXT DEFAULT 'unknown',
    chat_id      TEXT,
    session_id   TEXT,
    result       TEXT,
    error        TEXT,
    retries      INTEGER NOT NULL DEFAULT 0,
    max_retries  INTEGER NOT NULL DEFAULT 3,
    timeout_sec  INTEGER NOT NULL DEFAULT 300,
    api_target   TEXT,
    api_method   TEXT,
    api_params   TEXT
);
CREATE INDEX IF NOT EXISTS idx_status_priority
    ON tasks(status, priority ASC, created_at ASC);
"""

# Migrations: columns added after initial release
_MIGRATIONS = [
    "ALTER TABLE tasks ADD COLUMN api_target  TEXT",
    "ALTER TABLE tasks ADD COLUMN api_method  TEXT",
    "ALTER TABLE tasks ADD COLUMN api_params  TEXT",
]

# ── Connection ──────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create DB and tables if they don't exist. Run column migrations."""
    with get_db() as conn:
        conn.executescript(SCHEMA)
        # Safe idempotent migrations — silently skip if column already exists
        for stmt in _MIGRATIONS:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already exists


# ── Write ops ───────────────────────────────────────────────────────────────

def submit_task(
    content: str,
    assigned_to: str = "auto",
    task_type: str = "general",
    priority: int = 5,
    source: str = "unknown",
    chat_id: str = None,
    timeout_sec: int = 300,
    max_retries: int = 3,
    api_target: str = None,
    api_method: str = None,
    api_params: str = None,
) -> str:
    """Submit a task. Returns the task ID."""
    task_id = uuid.uuid4().hex[:8]
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, created_at, updated_at, priority, task_type, content,
                assigned_to, status, source, chat_id, timeout_sec, max_retries,
                api_target, api_method, api_params)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, now, now, priority, task_type, content,
             assigned_to, "pending", source, chat_id, timeout_sec, max_retries,
             api_target, api_method, api_params),
        )
    return task_id


def mark_running(task_id: str):
    _update(task_id, status="running")


def complete_task(task_id: str, result: str = ""):
    _update(task_id, status="done", result=result[:8192] if result else "")


def fail_task(task_id: str, error: str, retry: bool = True):
    now = _now()
    with get_db() as conn:
        row = conn.execute(
            "SELECT retries, max_retries FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        if row and retry and row["retries"] < row["max_retries"]:
            conn.execute(
                "UPDATE tasks SET status='pending', retries=retries+1, updated_at=?, error=? WHERE id=?",
                (now, error[:2048], task_id),
            )
        else:
            conn.execute(
                "UPDATE tasks SET status='failed', updated_at=?, error=? WHERE id=?",
                (now, error[:2048], task_id),
            )


# ── Read ops ─────────────────────────────────────────────────────────────────

def get_pending_tasks(limit: int = 10) -> list[dict]:
    """Return pending tasks ordered by priority then age."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM tasks
               WHERE status = 'pending'
               ORDER BY priority ASC, created_at ASC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def has_pending() -> bool:
    """Fast check: any pending tasks?"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM tasks WHERE status='pending' LIMIT 1"
        ).fetchone()
    return row is not None


def get_queue_stats() -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as n FROM tasks GROUP BY status"
        ).fetchall()
    return {r["status"]: r["n"] for r in rows}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _update(task_id: str, **fields):
    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [task_id]
    with get_db() as conn:
        conn.execute(f"UPDATE tasks SET {set_clause} WHERE id=?", values)
