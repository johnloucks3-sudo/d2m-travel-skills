import logging
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

log = logging.getLogger("router_cost_gates")

DATA_DIR = Path(__file__).resolve().parent / "data"
COST_DB = DATA_DIR / "router_cost.db"

# Approximate USD per 1M tokens, paid-tier list pricing (2026-07). Deliberately
# rounded UP for safety margin — this gates a hard stop, not an invoice.
GEMINI_PRICING_PER_1M = {
    "gemini-2.5-flash":      {"input": 0.35, "output": 3.00},
    "gemini-2.5-flash-lite": {"input": 0.15, "output": 0.60},
    "gemini-2.5-pro":        {"input": 2.00, "output": 15.00},
}
_DEFAULT_PRICING = {"input": 2.00, "output": 15.00}  # unknown model → worst case


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Conservative USD estimate for a single Gemini call — used to gate BEFORE
    the call happens, not to reconcile an invoice."""
    rates = GEMINI_PRICING_PER_1M.get(model, _DEFAULT_PRICING)
    return (input_tokens / 1_000_000) * rates["input"] + (output_tokens / 1_000_000) * rates["output"]


class HardLimitExceeded(RuntimeError):
    pass


def disable_api(project_id: str, api_name: str) -> bool:
    """Real cutoff: disable a single API on a single GCP project via the
    already-enabled Service Usage surface (same one `gcloud` itself uses —
    not a new/unusual API). This is the actual enforcement action, not just
    an alert. Never raises — logs and returns False on failure so a gate
    check that triggers this can't itself crash the caller."""
    try:
        log.critical(
            "COST GATE HARD LIMIT — disabling %s on project %s", api_name, project_id
        )
        result = subprocess.run(
            ["gcloud", "services", "disable", api_name,
             f"--project={project_id}", "--force", "--quiet"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            log.error("disable_api failed: %s", result.stderr.strip())
            return False
        log.critical("disable_api SUCCESS: %s disabled on %s", api_name, project_id)
        return True
    except Exception as e:
        log.error("disable_api exception: %s", e)
        return False

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

    def check_and_consume(self, pool_name: str, amount: float, *,
                           on_hard_limit=None) -> None:
        """Pre-flight gate: raises HardLimitExceeded BEFORE the spend happens
        if this amount would cross the pool's hard_limit — stopping the call,
        not reacting to it after Google's own billing pipeline catches up.

        on_hard_limit: optional zero-arg callback fired exactly once when the
        limit is first crossed (e.g. disable_api(...)). Exceptions from the
        callback are logged, never propagated — the raise itself is the gate.
        """
        with self._lock:
            pool = self._cache.get(pool_name)
            if pool is None:
                return
            hard = pool["hard_limit"]
            if hard in (0, float("inf")):
                return
            would_be = pool["consumed"] + amount
            if would_be >= hard:
                log.critical(
                    "Cost pool %s HARD LIMIT: consumed=%.4f + amount=%.4f >= hard=%.4f — BLOCKING call",
                    pool_name, pool["consumed"], amount, hard,
                )
                if on_hard_limit is not None:
                    try:
                        on_hard_limit()
                    except Exception as e:
                        log.error("on_hard_limit callback failed: %s", e)
                raise HardLimitExceeded(
                    f"Cost pool '{pool_name}' hard limit ${hard:.2f} would be exceeded "
                    f"(consumed ${pool['consumed']:.4f} + this call ~${amount:.4f})"
                )
            pool["consumed"] = would_be
            self._upsert(pool_name, would_be, pool["soft_limit"], hard)

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
