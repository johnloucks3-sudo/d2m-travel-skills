import logging
import sqlite3
import threading
import time
from pathlib import Path

log = logging.getLogger("router_cost_gates")

DATA_DIR = Path(__file__).resolve().parent / "data"
COST_DB = DATA_DIR / "router_cost.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pools (
    name TEXT PRIMARY KEY,
    consumed REAL NOT NULL DEFAULT 0,
    soft_limit REAL NOT NULL DEFAULT 0,
    hard_limit REAL NOT NULL DEFAULT 0,
    updated_ts REAL
);
"""


class CostGateTracker:
    """Pool-based cost ceilings backed by SQLite."""

    def __init__(self, db_path: str | Path | None = None):
        self._path = Path(db_path or COST_DB)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
        self._cache: dict[str, dict] = {}
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
            rows = self._conn.execute("SELECT name, consumed, soft_limit, hard_limit FROM pools").fetchall()
            for name, consumed, soft_limit, hard_limit in rows:
                self._cache[name] = {
                    "consumed": consumed,
                    "soft_limit": soft_limit,
                    "hard_limit": hard_limit,
                }
        except Exception as e:
            log.warning("Cost DB init: %s", e)

    def _upsert(self, name: str, consumed: float, soft_limit: float, hard_limit: float):
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pools (name, consumed, soft_limit, hard_limit, updated_ts)
                VALUES (?, ?, ?, ?, ?)""",
                (name, consumed, soft_limit, hard_limit, time.time()),
            )
            conn.commit()
        except Exception as e:
            log.error("Cost DB upsert failed: %s", e)

    def configure_pool(self, name: str, soft_limit: float, hard_limit: float):
        if hard_limit < 0:
            hard_limit = float("inf")
        with self._lock:
            self._cache[name] = {
                "consumed": 0.0,
                "soft_limit": soft_limit,
                "hard_limit": hard_limit,
            }
            self._upsert(name, 0.0, soft_limit, hard_limit)
            log.info("Cost pool configured: %s (soft=%.2f, hard=%.2f)", name, soft_limit, hard_limit)

    def has_headroom(self, pool_name: str) -> bool:
        with self._lock:
            pool = self._cache.get(pool_name)
            if pool is None:
                return True
            return pool["consumed"] < pool["hard_limit"]

    def consume(self, pool_name: str, amount: float):
        if amount <= 0:
            return
        with self._lock:
            pool = self._cache.get(pool_name)
            if pool is None:
                return
            pool["consumed"] += amount
            hard = pool["hard_limit"]
            pct = (pool["consumed"] / hard) * 100 if hard not in (0, float("inf")) else 0
            if pct >= 95:
                log.warning("Cost pool %s at %.1f%% — HARD CEILING NEAR", pool_name, pct)
            elif pct >= 80:
                log.warning("Cost pool %s at %.1f%% — soft limit exceeded", pool_name, pct)
            self._upsert(pool_name, pool["consumed"], pool["soft_limit"], hard)

    def usage_pct(self, pool_name: str) -> float:
        with self._lock:
            pool = self._cache.get(pool_name)
            if pool is None or pool["hard_limit"] in (0, float("inf")):
                return 0.0
            return (pool["consumed"] / pool["hard_limit"]) * 100

    def get_all(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._cache.items()}


cost_gates = CostGateTracker()
