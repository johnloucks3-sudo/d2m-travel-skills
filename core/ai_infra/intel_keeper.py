"""
Intel Keeper — freshness daemon for intel_index.db.

Each source registers a TTL. Keeper wakes every 15 minutes (via cron/systemd),
checks for stale rows, refreshes them, and logs outcomes to keeper_log.

Run:   python3 core/ai_infra/intel_keeper.py
Cron:  */15 * * * * python3 /home/john/Thunderbird/core/ai_infra/intel_keeper.py

Sources in Phase 1:
  tess        — trips, bookings, clients (4h TTL)
  icruise     — cruise pricing rows (8h TTL)
  cruisebound — cruise pricing rows (8h TTL)
  regent      — agent portal inventory (24h TTL)
  viking      — agent portal inventory (24h TTL)
  vtg         — promo email intel (on-receive / 24h sweep)

Sources in Phase 2:
  centrav     — B2B flight session health + featured deals (4h TTL)
  bedsonline  — hotel rates for cruise port cities (24h TTL)
"""
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/home/john/Thunderbird/logs/intel_keeper.log"),
    ],
)
logger = logging.getLogger("intel_keeper")

DB_PATH = Path("/home/john/Thunderbird/core/ai_infra/data/intel_index.db")

# TTL in seconds per source
TTL = {
    "tess":        4 * 3600,
    "icruise":     8 * 3600,
    "cruisebound": 8 * 3600,
    "regent":     24 * 3600,
    "viking":     24 * 3600,
    "vtg":        24 * 3600,
    "centrav":     4 * 3600,
    "bedsonline": 24 * 3600,
}

# M-061 eval results (2026-05-28):
#   regent — Akamai Bot Manager (edgesuite.net). Defeats vanilla + playwright-stealth + nodriver.
#             Not bypassable at YOGA IP without residential proxy service. Stays blocked.
#   viking — Azure B2C OAuth login. NOT bot-blocked — login form loads fine.
#             Blocked here: TA account registration required (current creds = consumer account).
#             Remove from skip list once Commander registers at viking.com/travel-advisor.
BOT_BLOCKED: set[str] = {"regent"}
TA_CREDS_MISSING: set[str] = {"viking"}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_con() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def upsert_rows(con: sqlite3.Connection, source: str, category: str,
                rows: list[dict], ttl: int, provenance: str = "") -> int:
    """Insert or replace rows for a source+category. Returns count inserted."""
    now = datetime.now(timezone.utc).isoformat()
    cur = con.cursor()
    # Mark existing rows stale
    cur.execute(
        "UPDATE intel_index SET stale=1 WHERE source=? AND category=?",
        (source, category),
    )
    inserted = 0
    for row in rows:
        cur.execute(
            """INSERT INTO intel_index
               (source, category, record_id, data_json, scraped_at, ttl_seconds, provenance, stale)
               VALUES (?,?,?,?,?,?,?,0)""",
            (source, category,
             str(row.get("id") or row.get("record_id") or ""),
             json.dumps(row, default=str),
             now, ttl, provenance),
        )
        inserted += 1
    con.commit()
    return inserted


def log_run(con: sqlite3.Connection, source: str, action: str,
            rows_in: int = 0, rows_out: int = 0,
            elapsed: float = 0.0, error: str = "") -> None:
    con.execute(
        """INSERT INTO keeper_log (source, action, rows_in, rows_out, elapsed_s, error)
           VALUES (?,?,?,?,?,?)""",
        (source, action, rows_in, rows_out, elapsed, error),
    )
    con.commit()


def is_stale(con: sqlite3.Connection, source: str, category: str) -> bool:
    """Return True if source+category has no rows or oldest row is past TTL."""
    ttl = TTL.get(source, 86400)
    row = con.execute(
        """SELECT MAX(scraped_at) as last_scraped FROM intel_index
           WHERE source=? AND category=? AND stale=0""",
        (source, category),
    ).fetchone()
    if not row or not row["last_scraped"]:
        return True
    last = datetime.fromisoformat(row["last_scraped"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - last).total_seconds()
    return age > ttl


# ---------------------------------------------------------------------------
# Connectors — lazy imports so failures don't block the daemon
# ---------------------------------------------------------------------------

def refresh_tess(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.tess_connector import ingest_tess
    ingest_tess(con, upsert_rows, log_run, TTL["tess"])


def refresh_icruise(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.icruise_connector import ingest_icruise
    ingest_icruise(con, upsert_rows, log_run, TTL["icruise"])


def refresh_cruisebound(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.cruisebound_connector import ingest_cruisebound
    ingest_cruisebound(con, upsert_rows, log_run, TTL["cruisebound"])


def refresh_regent(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.regent_connector import ingest_regent
    ingest_regent(con, upsert_rows, log_run, TTL["regent"])


def refresh_viking(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.viking_connector import ingest_viking
    ingest_viking(con, upsert_rows, log_run, TTL["viking"])


def refresh_vtg(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.vtg_connector import ingest_vtg
    ingest_vtg(con, upsert_rows, log_run, TTL["vtg"])


def refresh_centrav(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.centrav_connector import ingest_centrav
    ingest_centrav(con, upsert_rows, log_run, TTL["centrav"])


def refresh_bedsonline(con: sqlite3.Connection) -> None:
    from core.ai_infra.intel_connectors.bedsonline_connector import ingest_bedsonline
    ingest_bedsonline(con, upsert_rows, log_run, TTL["bedsonline"])


# consumer: who reads this data and for what purpose
SOURCES: list[tuple[str, list[str], Callable]] = [
    # consumer: TESS auth → Bryana dashboard FPD sync, bryana_dashboard.py
    ("tess",        ["trips", "bookings", "clients"],     refresh_tess),
    # consumer: cruise pricing lookups, A2 Dembe fare watch
    ("icruise",     ["cruise_pricing"],                   refresh_icruise),
    # consumer: cruise pricing comparison, fare watch cross-check
    ("cruisebound", ["cruise_pricing"],                   refresh_cruisebound),
    # consumer: Regent agent portal inventory — BOT_BLOCKED, skipped until M-061
    ("regent",      ["agent_inventory"],                  refresh_regent),
    # consumer: Viking agent portal inventory — BOT_BLOCKED, skipped until M-061
    ("viking",      ["agent_inventory"],                  refresh_viking),
    # consumer: VTG promo emails → A2 Dembe promo digest
    ("vtg",         ["promo_email"],                      refresh_vtg),
    # consumer: Centrav B2B session health → M-038 flight scraper (Wave 2, needs re-auth)
    ("centrav",     ["session_health", "featured_deals"], refresh_centrav),
    # consumer: Bedsonline hotel rates → post-cruise hotel quotes (Wave 2, needs credentials)
    ("bedsonline",  ["session_health", "hotel_rates"],    refresh_bedsonline),
]


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_once(force: bool = False) -> None:
    con = get_con()
    for source, categories, refresh_fn in SOURCES:
        if source in BOT_BLOCKED:
            logger.info("%s — SKIPPED (akamai_blocked — residential proxy required)", source)
            continue
        if source in TA_CREDS_MISSING:
            logger.info("%s — SKIPPED (ta_account_registration_required — register at viking.com/travel-advisor)", source)
            continue
        needs_refresh = force or any(is_stale(con, source, cat) for cat in categories)
        if not needs_refresh:
            logger.debug("%s — fresh, skipping", source)
            continue
        logger.info("%s — refreshing", source)
        t0 = time.monotonic()
        try:
            refresh_fn(con)
            elapsed = time.monotonic() - t0
            logger.info("%s — done (%.1fs)", source, elapsed)
        except Exception as exc:
            elapsed = time.monotonic() - t0
            logger.error("%s — FAILED (%.1fs): %s", source, elapsed, exc)
            log_run(con, source, "refresh_error", error=str(exc), elapsed=elapsed)
    con.close()


if __name__ == "__main__":
    force = "--force" in sys.argv
    logger.info("Intel Keeper starting (force=%s)", force)
    run_once(force=force)
    logger.info("Intel Keeper done")
