import logging
import sqlite3
import threading
import time
from pathlib import Path

from core.ai_infra.adapters.base import HealthState

log = logging.getLogger("router_health")

DATA_DIR = Path(__file__).resolve().parent / "data"
HEALTH_DB = DATA_DIR / "router_health.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS health_state (
    adapter_name TEXT PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'GREEN',
    failures INTEGER NOT NULL DEFAULT 0,
    consecutive_successes INTEGER NOT NULL DEFAULT 0,
    last_probe_ts REAL,
    last_error TEXT
);
CREATE TABLE IF NOT EXISTS health_probes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adapter_name TEXT NOT NULL,
    ts REAL NOT NULL,
    state TEXT NOT NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_probes_adapter ON health_probes(adapter_name);
CREATE INDEX IF NOT EXISTS idx_probes_ts ON health_probes(ts);
"""


class HealthTracker:
    """Per-adapter health state backed by SQLite."""

    MAX_FAILURES_FOR_RED = 3
    SUCCESSES_FOR_RECOVERY = 2

    def __init__(self, db_path: str | Path | None = None):
        self._path = Path(db_path or HEALTH_DB)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._cache: dict[str, tuple[HealthState, int]] = {}
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
        return self._conn

    def _init_db(self):
        try:
            self._get_conn().commit()
            # Seed cache from DB
            rows = self._conn.execute(
                "SELECT adapter_name, state, failures FROM health_state"
            ).fetchall()
            for name, state, failures in rows:
                self._cache[name] = (state, failures)
        except Exception as e:
            log.warning("Health DB init: %s", e)

    def _upsert(self, name: str, state: HealthState, failures: int, successes: int, error: str = ""):
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO health_state
                (adapter_name, state, failures, consecutive_successes, last_probe_ts, last_error)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (name, state, failures, successes, time.time(), error or None),
            )
            conn.commit()
        except Exception as e:
            log.error("Health DB upsert failed: %s", e)

    def get(self, name: str) -> HealthState:
        with self._lock:
            cached = self._cache.get(name)
            if cached:
                return cached[0]
        return "GREEN"

    def record_failure(self, name: str):
        with self._lock:
            _, failures = self._cache.get(name, ("GREEN", 0))
            failures += 1
            state: HealthState = "RED" if failures >= self.MAX_FAILURES_FOR_RED else "YELLOW"
            self._cache[name] = (state, failures)
            self._upsert(name, state, failures, 0)
            if state == "RED":
                log.warning("Health: %s → RED (%d failures)", name, failures)

    def record_success(self, name: str):
        with self._lock:
            state, failures = self._cache.get(name, ("GREEN", 0))
            successes = 0
            if state == "RED":
                cached_ok = self._get_ok(name)
                successes = cached_ok + 1
            else:
                successes = 1

            if successes >= self.SUCCESSES_FOR_RECOVERY and state != "GREEN":
                log.info("Health: %s recovered → GREEN (%d successes)", name, successes)
                self._cache[name] = ("GREEN", 0)
                self._upsert(name, "GREEN", 0, successes)
            elif state == "YELLOW" and failures > 0:
                self._cache[name] = ("YELLOW", max(0, failures - 1))
                self._upsert(name, "YELLOW", max(0, failures - 1), successes)
            else:
                if state == "GREEN":
                    self._upsert(name, "GREEN", 0, successes)

    def _get_ok(self, name: str) -> int:
        try:
            row = self._get_conn().execute(
                "SELECT consecutive_successes FROM health_state WHERE adapter_name = ?",
                (name,),
            ).fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def set_state(self, name: str, state: HealthState):
        with self._lock:
            self._cache[name] = (state, 0)
            self._upsert(name, state, 0, 0)

    def record_probe(self, name: str, state: HealthState, latency_ms: int, error: str = ""):
        """Record a health probe result (from daemon). Does NOT change health state."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO health_probes (adapter_name, ts, state, latency_ms, error) VALUES (?, ?, ?, ?, ?)",
                (name, time.time(), state, latency_ms, error or None),
            )
            conn.commit()
        except Exception as e:
            log.error("Health probe record failed: %s", e)

    def all_states(self) -> dict[str, tuple[HealthState, int]]:
        with self._lock:
            return {k: v for k, v in self._cache.items()}

    def probe_history(self, name: str, limit: int = 20) -> list[dict]:
        try:
            rows = self._get_conn().execute(
                "SELECT ts, state, latency_ms, error FROM health_probes "
                "WHERE adapter_name = ? ORDER BY ts DESC LIMIT ?",
                (name, limit),
            ).fetchall()
            return [
                {"ts": r[0], "state": r[1], "latency_ms": r[2], "error": r[3]}
                for r in rows
            ]
        except Exception as e:
            log.error("Probe history failed: %s", e)
            return []


health = HealthTracker()
