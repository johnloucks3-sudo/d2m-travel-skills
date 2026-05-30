"""
fare_watch_db.py — SQLite backing store for Thunderbird Fare Watch
==================================================================
Replaces flat JSON files (data/fare_watches.json, core/travel/data/fare_watches.json)
with a proper indexed, atomic SQLite database.

DB path: /home/john/Thunderbird/core/fare_watch/fare_watch.db

Tables:
  fare_watches   — one row per watch (upsert-safe, full schema parity with JSON)
  fare_history   — append-only price event log

Public API (matches thunderbird_fare_watch.py function signatures):
  add_watch()    — insert or replace a watch
  update_fare()  — record a new price reading + update current_price_pp
  get_alerts()   — watches where current_price_pp crossed alert thresholds
  list_active()  — all active watches, ordered by travel_date
  get_watch()    — single watch by ID
  get_history()  — history entries for a watch_id
  close_watch()  — set status=closed
  migrate_from_json() — one-shot import from legacy JSON files

Migration note (2026-05-30 — A12 ELON):
  Both legacy JSON files are imported into this DB on first run.
  thunderbird_fare_watch.py _load_watches() / _save_watches() are NOT wired here yet —
  that rewire is Sterling's call. See fare_watch_daemon.py for standalone use.
"""

import json
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "fare_watch.db"
THUNDERBIRD = Path.home() / "Thunderbird"

# Legacy JSON paths — migration sources
LEGACY_JSON_PRIMARY = THUNDERBIRD / "core" / "travel" / "data" / "fare_watches.json"
LEGACY_JSON_SECONDARY = THUNDERBIRD / "data" / "fare_watches.json"
LEGACY_HISTORY_PRIMARY = THUNDERBIRD / "core" / "travel" / "data" / "fare_history.json"


# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

@contextmanager
def _db(path: Path = DB_PATH):
    """Context manager: WAL-mode connection with row_factory."""
    con = sqlite3.connect(str(path), isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
    finally:
        con.close()


# ============================================================================
# SCHEMA
# ============================================================================

_DDL = """
CREATE TABLE IF NOT EXISTS fare_watches (
    id                  TEXT PRIMARY KEY,
    client              TEXT NOT NULL DEFAULT '',
    booking_ref         TEXT NOT NULL DEFAULT '',
    watch_type          TEXT NOT NULL DEFAULT 'flight',
    label               TEXT NOT NULL DEFAULT '',
    provider            TEXT NOT NULL DEFAULT '',
    route               TEXT NOT NULL DEFAULT '',
    travel_date         TEXT NOT NULL,
    passengers          INTEGER NOT NULL DEFAULT 2,
    current_price_pp    REAL NOT NULL,
    baseline_price_pp   REAL NOT NULL,
    alert_below         REAL,
    alert_above         REAL,
    alert_threshold_pct REAL,
    last_checked        TEXT,
    status              TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active', 'triggered', 'closed')),
    notes               TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fare_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id    TEXT NOT NULL REFERENCES fare_watches(id) ON DELETE CASCADE,
    fare        REAL NOT NULL,
    total       REAL,
    change_pct  REAL,
    checked_at  TEXT NOT NULL DEFAULT (datetime('now')),
    source      TEXT NOT NULL DEFAULT 'manual'
                CHECK(source IN ('centrav', 'inferred', 'manual', 'sweep', 'kayak', 'skiplagged')),
    alert_triggered TEXT,
    notes       TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_fare_history_watch_id ON fare_history(watch_id);
CREATE INDEX IF NOT EXISTS idx_fare_watches_status ON fare_watches(status);
CREATE INDEX IF NOT EXISTS idx_fare_watches_travel_date ON fare_watches(travel_date);
"""


def init_db(path: Path = DB_PATH) -> None:
    """Create tables and indexes if they don't exist."""
    with _db(path) as con:
        con.executescript(_DDL)
    logger.info(f"fare_watch DB initialized: {path}")


# ============================================================================
# WRITE OPERATIONS
# ============================================================================

def add_watch(
    id: str,
    travel_date: str,
    current_price_pp: float,
    baseline_price_pp: Optional[float] = None,
    client: str = "",
    booking_ref: str = "",
    watch_type: str = "flight",
    label: str = "",
    provider: str = "",
    route: str = "",
    passengers: int = 2,
    alert_below: Optional[float] = None,
    alert_above: Optional[float] = None,
    alert_threshold_pct: Optional[float] = None,
    notes: str = "",
    status: str = "active",
    created_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert or replace a fare watch. Returns the stored record."""
    if baseline_price_pp is None:
        baseline_price_pp = current_price_pp
    ts = created_at or datetime.now().isoformat()

    with _db() as con:
        con.execute(
            """
            INSERT INTO fare_watches
                (id, client, booking_ref, watch_type, label, provider, route,
                 travel_date, passengers, current_price_pp, baseline_price_pp,
                 alert_below, alert_above, alert_threshold_pct, notes, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                client              = excluded.client,
                booking_ref         = excluded.booking_ref,
                watch_type          = excluded.watch_type,
                label               = excluded.label,
                provider            = excluded.provider,
                route               = excluded.route,
                travel_date         = excluded.travel_date,
                passengers          = excluded.passengers,
                current_price_pp    = excluded.current_price_pp,
                baseline_price_pp   = excluded.baseline_price_pp,
                alert_below         = excluded.alert_below,
                alert_above         = excluded.alert_above,
                alert_threshold_pct = excluded.alert_threshold_pct,
                notes               = excluded.notes,
                status              = excluded.status
            """,
            (id, client, booking_ref, watch_type, label, provider, route,
             travel_date, passengers, current_price_pp, baseline_price_pp,
             alert_below, alert_above, alert_threshold_pct, notes, status, ts),
        )
    return get_watch(id)


def update_fare(
    watch_id: str,
    fare: float,
    source: str = "manual",
    notes: str = "",
    checked_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record a new price in fare_history and update current_price_pp.
    Returns the updated watch row + alert info.
    """
    ts = checked_at or datetime.now().isoformat()
    watch = get_watch(watch_id)
    if not watch:
        raise ValueError(f"Watch '{watch_id}' not found")

    baseline = watch["baseline_price_pp"]
    passengers = watch["passengers"]
    change_pct = ((fare - baseline) / baseline * 100) if baseline else 0.0
    total = fare * passengers

    # Determine alert
    alert = None
    alert_below = watch.get("alert_below")
    alert_above = watch.get("alert_above")
    if alert_below and fare < alert_below:
        alert = f"PRICE DROP: ${fare:,.0f}/pp below threshold ${alert_below:,.0f}"
    elif alert_above and fare > alert_above:
        alert = f"PRICE SPIKE: ${fare:,.0f}/pp exceeds threshold ${alert_above:,.0f}"

    new_status = "triggered" if alert else watch.get("status", "active")
    if new_status == "closed":
        new_status = "closed"  # closed stays closed

    with _db() as con:
        con.execute(
            """
            INSERT INTO fare_history (watch_id, fare, total, change_pct, checked_at, source, alert_triggered, notes)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (watch_id, fare, total, round(change_pct, 2), ts, source, alert, notes),
        )
        con.execute(
            """
            UPDATE fare_watches
               SET current_price_pp = ?, last_checked = ?, status = ?
             WHERE id = ?
            """,
            (fare, ts, new_status, watch_id),
        )

    updated = get_watch(watch_id)
    updated["alert"] = alert
    updated["change_pct"] = round(change_pct, 2)
    return updated


def close_watch(watch_id: str) -> None:
    """Mark a watch as closed (e.g. voyage departed)."""
    with _db() as con:
        con.execute("UPDATE fare_watches SET status='closed' WHERE id=?", (watch_id,))


# ============================================================================
# READ OPERATIONS
# ============================================================================

def get_watch(watch_id: str) -> Optional[Dict[str, Any]]:
    """Fetch one watch by ID. Returns None if not found."""
    with _db() as con:
        row = con.execute("SELECT * FROM fare_watches WHERE id=?", (watch_id,)).fetchone()
    return dict(row) if row else None


def list_active(include_triggered: bool = True) -> List[Dict[str, Any]]:
    """Return all active (and optionally triggered) watches, sorted by travel_date."""
    statuses = ("active", "triggered") if include_triggered else ("active",)
    placeholders = ",".join("?" * len(statuses))
    with _db() as con:
        rows = con.execute(
            f"SELECT * FROM fare_watches WHERE status IN ({placeholders}) ORDER BY travel_date",
            statuses,
        ).fetchall()
    return [dict(r) for r in rows]


def get_alerts() -> List[Dict[str, Any]]:
    """
    Return watches where current_price_pp has crossed an alert threshold.
    Specifically: status='triggered' OR (alert_below IS NOT NULL AND current < alert_below)
                                     OR (alert_above IS NOT NULL AND current > alert_above)
    """
    with _db() as con:
        rows = con.execute(
            """
            SELECT * FROM fare_watches
            WHERE status IN ('active','triggered')
              AND (
                (alert_below IS NOT NULL AND current_price_pp < alert_below)
                OR
                (alert_above IS NOT NULL AND current_price_pp > alert_above)
              )
            ORDER BY travel_date
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_history(watch_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return fare_history for a watch, most recent first."""
    with _db() as con:
        rows = con.execute(
            """
            SELECT * FROM fare_history
            WHERE watch_id=?
            ORDER BY checked_at DESC
            LIMIT ?
            """,
            (watch_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def summary_stats() -> Dict[str, Any]:
    """Return counts and total portfolio value for the Commander brief."""
    with _db() as con:
        totals = con.execute(
            """
            SELECT
                COUNT(*) AS total_watches,
                SUM(CASE WHEN status='active'    THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN status='triggered' THEN 1 ELSE 0 END) AS triggered,
                SUM(CASE WHEN status='closed'    THEN 1 ELSE 0 END) AS closed,
                SUM(current_price_pp * passengers)                   AS portfolio_value
            FROM fare_watches
            """
        ).fetchone()
        alert_count = con.execute(
            """
            SELECT COUNT(*) FROM fare_watches
            WHERE status IN ('active','triggered')
              AND (
                (alert_below IS NOT NULL AND current_price_pp < alert_below)
                OR
                (alert_above IS NOT NULL AND current_price_pp > alert_above)
              )
            """
        ).fetchone()[0]
    return {
        "total_watches": totals["total_watches"],
        "active": totals["active"],
        "triggered": totals["triggered"],
        "closed": totals["closed"],
        "portfolio_value_usd": totals["portfolio_value"] or 0.0,
        "current_alerts": alert_count,
    }


# ============================================================================
# MIGRATION
# ============================================================================

def _infer_client(watch_id: str, label: str) -> str:
    """Best-effort client extraction from watch_id / label."""
    id_lower = watch_id.lower()
    if "westbrook" in id_lower:
        return "Westbrook"
    if "loucks" in id_lower:
        return "Loucks"
    if "mcleod" in id_lower:
        return "McLeod/McGlasson"
    if "furlow" in id_lower:
        return "Furlow"
    if "nichols" in id_lower:
        return "Nichols"
    if "ely" in id_lower or "darrow" in id_lower:
        return "Ely/Darrow"
    if "lyons" in id_lower:
        return "Lyons"
    if "kuklinski" in id_lower:
        return "Kuklinski"
    if "morton" in id_lower or "dodge" in id_lower:
        return "Morton/Dodge"
    if "viking" in id_lower:
        return "Kuklinski"
    if "flight" in id_lower and "kuklinski" not in id_lower:
        return "Unknown"
    return "Unknown"


def _infer_booking_ref(notes: str) -> str:
    """Pull first booking-ref-shaped token from notes."""
    import re
    m = re.search(r"\b(\d{7}(?:-\d{2})?)\b", notes)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z]{6,8})\b", notes)
    if m:
        return m.group(1)
    return ""


def _import_watch_dict(watch_dict: Dict, source_label: str, seen_ids: set) -> int:
    """Import a single watch record. Returns 1 if inserted/updated, 0 if skipped."""
    wid = watch_dict.get("id", "").strip()
    if not wid:
        return 0
    if wid in seen_ids:
        logger.debug(f"  skip duplicate: {wid}")
        return 0
    seen_ids.add(wid)

    travel_date = watch_dict.get("travel_date", "")
    if not travel_date:
        # Try travel_window_start for prospect watches
        travel_date = watch_dict.get("travel_window_start", "2099-01-01")

    current = watch_dict.get("current_price_pp", watch_dict.get("baseline_price_pp", 0.0))
    baseline = watch_dict.get("baseline_price_pp", current)

    active_flag = watch_dict.get("active", True)
    status = "active" if active_flag else "closed"

    notes = watch_dict.get("notes", "")
    client = _infer_client(wid, watch_dict.get("label", ""))
    booking_ref = _infer_booking_ref(notes)

    add_watch(
        id=wid,
        client=client,
        booking_ref=booking_ref,
        watch_type=watch_dict.get("watch_type", "flight"),
        label=watch_dict.get("label", wid),
        provider=watch_dict.get("provider", ""),
        route=watch_dict.get("route", ""),
        travel_date=travel_date,
        passengers=watch_dict.get("passengers", 2),
        current_price_pp=float(current),
        baseline_price_pp=float(baseline),
        alert_below=watch_dict.get("alert_below"),
        alert_above=watch_dict.get("alert_above"),
        notes=notes,
        status=status,
        created_at=watch_dict.get("created"),
    )
    logger.info(f"  migrated [{source_label}]: {wid}")
    return 1


def migrate_from_json(
    primary_json: Path = LEGACY_JSON_PRIMARY,
    secondary_json: Path = LEGACY_JSON_SECONDARY,
    history_json: Path = LEGACY_HISTORY_PRIMARY,
) -> Dict[str, int]:
    """
    One-shot migration from both legacy JSON files.
    Safe to run multiple times — uses INSERT OR REPLACE.

    Returns: {"watches_migrated": N, "history_migrated": M}
    """
    init_db()
    seen_ids: set = set()
    watches_count = 0
    history_count = 0

    # --- Watches: primary (dict-of-dicts format) ---
    if primary_json.exists():
        data = json.loads(primary_json.read_text(encoding="utf-8"))
        logger.info(f"Migrating watches from primary JSON: {primary_json}")
        for wid, w in data.items():
            if "id" not in w:
                w["id"] = wid
            watches_count += _import_watch_dict(w, "primary", seen_ids)
    else:
        logger.warning(f"Primary JSON not found: {primary_json}")

    # --- Watches: secondary (list or dict-of-dicts) ---
    if secondary_json.exists():
        raw = json.loads(secondary_json.read_text(encoding="utf-8"))
        logger.info(f"Migrating watches from secondary JSON: {secondary_json}")
        # Secondary may be {"watches": [...]} or a plain dict
        if isinstance(raw, dict) and "watches" in raw:
            items = raw["watches"]
            for w in items:
                watches_count += _import_watch_dict(w, "secondary", seen_ids)
        elif isinstance(raw, dict):
            for wid, w in raw.items():
                if isinstance(w, dict):
                    if "id" not in w:
                        w["id"] = wid
                    watches_count += _import_watch_dict(w, "secondary", seen_ids)
    else:
        logger.warning(f"Secondary JSON not found: {secondary_json}")

    # --- History ---
    if history_json.exists():
        history = json.loads(history_json.read_text(encoding="utf-8"))
        logger.info(f"Migrating {len(history)} history entries from {history_json}")
        with _db() as con:
            for entry in history:
                wid = entry.get("watch_id", "")
                # Only import history for watches that exist in DB
                exists = con.execute(
                    "SELECT 1 FROM fare_watches WHERE id=?", (wid,)
                ).fetchone()
                if not exists:
                    logger.debug(f"  history skip (no parent watch): {wid}")
                    continue
                # Avoid re-inserting if already present (match on watch_id+checked_at)
                ts = entry.get("timestamp", "")
                dup = con.execute(
                    "SELECT 1 FROM fare_history WHERE watch_id=? AND checked_at=?",
                    (wid, ts),
                ).fetchone()
                if dup:
                    continue
                con.execute(
                    """
                    INSERT INTO fare_history
                        (watch_id, fare, total, change_pct, checked_at, source, alert_triggered, notes)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        wid,
                        entry.get("price_pp", 0.0),
                        entry.get("total", 0.0),
                        entry.get("price_change_pct", 0.0),
                        ts,
                        "manual",
                        entry.get("alert_triggered"),
                        entry.get("notes", ""),
                    ),
                )
                history_count += 1
    else:
        logger.warning(f"History JSON not found: {history_json}")

    logger.info(f"Migration complete: {watches_count} watches, {history_count} history entries")
    return {"watches_migrated": watches_count, "history_migrated": history_count}


# ============================================================================
# SELF-INIT
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = migrate_from_json()
    print(f"\nMigration result: {result}")
    stats = summary_stats()
    print(f"DB summary: {json.dumps(stats, indent=2)}")
