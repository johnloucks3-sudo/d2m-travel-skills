import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

from core.ai_infra.adapters.base import AdapterResult

log = logging.getLogger("router_telemetry")

DATA_DIR = Path(__file__).resolve().parent / "data"
TELEMETRY_DB = DATA_DIR / "router_telemetry.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    persona TEXT NOT NULL,
    tier TEXT NOT NULL,
    adapter TEXT NOT NULL,
    model TEXT NOT NULL,
    cost_pool TEXT NOT NULL,
    cost_consumed REAL NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    ok INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    chains_tried TEXT,
    task_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_dispatches_ts ON dispatches(ts);
CREATE INDEX IF NOT EXISTS idx_dispatches_persona ON dispatches(persona);
CREATE INDEX IF NOT EXISTS idx_dispatches_tier ON dispatches(tier);
"""


class TelemetryTracker:
    """Dispatch log backed by SQLite. Creates data/ directory if missing."""

    def __init__(self, db_path: str | Path | None = None):
        self._path = Path(db_path or TELEMETRY_DB)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None
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
        except Exception as e:
            log.warning("Telemetry DB init: %s", e)

    def log(
        self,
        persona: str,
        tier: str,
        result: AdapterResult,
        chains_tried: list[str] | None = None,
        task_id: str = "",
    ):
        conn = self._get_conn()
        try:
            with self._lock:
                conn.execute(
                    """INSERT INTO dispatches
                    (ts, persona, tier, adapter, model, cost_pool, cost_consumed,
                     latency_ms, ok, error, chains_tried, task_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        time.time(),
                        persona,
                        tier,
                        result.model_used,
                        result.model_used,
                        result.cost_pool,
                        result.cost_consumed,
                        result.latency_ms,
                        1 if result.ok else 0,
                        result.error,
                        json.dumps(chains_tried or []),
                        task_id,
                    ),
                )
                conn.commit()
        except Exception as e:
            log.error("Telemetry write failed: %s", e)

        log.info(
            "[TELEM] persona=%s tier=%s adapter=%s ok=%s cost=%.4f lat=%dms",
            persona, tier, result.model_used, result.ok, result.cost_consumed, result.latency_ms,
        )

    def summary(self, since_ts: float | None = None) -> dict:
        conn = self._get_conn()
        try:
            where = "WHERE ts > ?" if since_ts else ""
            params = (since_ts,) if since_ts else ()

            row = conn.execute(
                f"SELECT COUNT(*), SUM(ok), SUM(CASE WHEN ok=0 THEN 1 ELSE 0 END) "
                f"FROM dispatches {where}",
                params,
            ).fetchone()
            total, ok_count, fail_count = (row or (0, 0, 0))
            ok_count = ok_count or 0
            fail_count = fail_count or 0

            rows = conn.execute(
                f"SELECT tier, COUNT(*), SUM(ok) FROM dispatches {where} GROUP BY tier",
                params,
            ).fetchall()
            by_tier = {}
            for tier, cnt, oks in rows:
                by_tier[tier] = {"total": cnt, "ok": oks or 0}

            return {
                "total_calls": int(total),
                "ok": int(ok_count),
                "fail": int(fail_count),
                "by_tier": by_tier,
            }
        except Exception as e:
            log.error("Telemetry summary failed: %s", e)
            return {"total_calls": 0, "ok": 0, "fail": 0, "by_tier": {}}

    def recent(self, limit: int = 20) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT ts, persona, tier, adapter, model, cost_consumed, latency_ms, ok, error "
                "FROM dispatches ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
            return [
                {
                    "ts": r[0], "persona": r[1], "tier": r[2],
                    "adapter": r[3], "model": r[4], "cost_consumed": r[5],
                    "latency_ms": r[6], "ok": bool(r[7]), "error": r[8],
                }
                for r in rows
            ]
        except Exception as e:
            log.error("Telemetry recent failed: %s", e)
            return []


telemetry = TelemetryTracker()
