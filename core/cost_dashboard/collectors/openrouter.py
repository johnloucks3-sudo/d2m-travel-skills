"""OpenRouter Usage Collector — pulls aggregate usage from /auth/key endpoint into SQLite.
Uses the auth/key endpoint (always available) instead of /activity (management-key-only)."""
import json, sqlite3, os, time, requests
from pathlib import Path
from datetime import datetime, timezone

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
STATE = Path.home() / "Thunderbird" / "storage" / ".collector_state.json"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE = "https://openrouter.ai/api/v1"


def _ensure_snapshot_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS openrouter_snapshots (
            id INTEGER PRIMARY KEY,
            ts TEXT NOT NULL,
            total_usage REAL,
            usage_daily REAL,
            usage_weekly REAL,
            usage_monthly REAL,
            limit_amount REAL,
            limit_remaining REAL,
            total_credits REAL,
            is_free_tier BOOLEAN,
            UNIQUE(ts)
        )
    """)
    conn.commit()


def _fetch_key_info():
    r = requests.get(f"{BASE}/auth/key", headers={"Authorization": f"Bearer {API_KEY}"}, timeout=15)
    r.raise_for_status()
    return r.json()["data"]


def _fetch_credits():
    r = requests.get(f"{BASE}/credits", headers={"Authorization": f"Bearer {API_KEY}"}, timeout=15)
    r.raise_for_status()
    return r.json()["data"]


def collect():
    conn = sqlite3.connect(str(DB), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    _ensure_snapshot_table(conn)
    try:
        key_info = _fetch_key_info()
        credits = _fetch_credits()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("""
            INSERT OR IGNORE INTO openrouter_snapshots
            (ts, total_usage, usage_daily, usage_weekly, usage_monthly,
             limit_amount, limit_remaining, total_credits, is_free_tier)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            now,
            key_info.get("usage", 0),
            key_info.get("usage_daily", 0),
            key_info.get("usage_weekly", 0),
            key_info.get("usage_monthly", 0),
            key_info.get("limit", 0),
            key_info.get("limit_remaining", 0),
            credits.get("total_credits", 0),
            1 if key_info.get("is_free_tier") else 0,
        ))
        conn.commit()
        return {
            "snapshot_stored": True,
            "total_usage": key_info.get("usage", 0),
            "usage_daily": key_info.get("usage_daily", 0),
            "usage_weekly": key_info.get("usage_weekly", 0),
            "usage_monthly": key_info.get("usage_monthly", 0),
            "limit_remaining": key_info.get("limit_remaining", 0),
            "total_credits": credits.get("total_credits", 0),
        }
    except requests.RequestException as e:
        return {"error": str(e)}
    finally:
        conn.close()


if __name__ == "__main__":
    result = collect()
    result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(json.dumps(result))
