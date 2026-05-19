"""Seed initial Claude Max plan snapshot into ai_costs.db.
Data sourced from Claude web UI (Commander-provided, 2026-05-16 ~09:00 MDT).
Run manually after plan changes or monthly reset."""
import sqlite3, json, time
from pathlib import Path
from datetime import datetime, timezone

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"

SNAPSHOT = {
    "plan_name": "Max",
    "monthly_spent": 50.24,
    "monthly_limit": 100.0,
    "session_pct": 13.0,
    "weekly_all_pct": 22.0,
    "weekly_sonnet_pct": 29.0,
    "balance": 3.15,
    "auto_reload": False,
    "month_resets": "2026-06-01",
}

def seed():
    conn = sqlite3.connect(str(DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plan_snapshots (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,
          plan_name TEXT DEFAULT 'Max',
          monthly_spent REAL,
          monthly_limit REAL,
          monthly_pct REAL,
          session_pct REAL,
          weekly_all_pct REAL,
          weekly_sonnet_pct REAL,
          balance REAL,
          auto_reload BOOLEAN DEFAULT 0,
          month_resets TEXT,
          UNIQUE(ts)
        )
    """)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pct = round(SNAPSHOT["monthly_spent"] / SNAPSHOT["monthly_limit"] * 100, 1)
    conn.execute("""
        INSERT OR IGNORE INTO plan_snapshots
        (ts, plan_name, monthly_spent, monthly_limit, monthly_pct,
         session_pct, weekly_all_pct, weekly_sonnet_pct,
         balance, auto_reload, month_resets)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        now, SNAPSHOT["plan_name"],
        SNAPSHOT["monthly_spent"], SNAPSHOT["monthly_limit"], pct,
        SNAPSHOT["session_pct"], SNAPSHOT["weekly_all_pct"], SNAPSHOT["weekly_sonnet_pct"],
        SNAPSHOT["balance"], 1 if SNAPSHOT["auto_reload"] else 0,
        SNAPSHOT["month_resets"],
    ))
    conn.commit()
    conn.close()
    result = {**SNAPSHOT, "monthly_pct": pct, "timestamp": now}
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    seed()
