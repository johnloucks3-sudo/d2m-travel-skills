"""Poe Usage Collector — reads local API call logs into SQLite.

Logs are written by thunderbird_telegram_webhook.py:call_poe_engine() to:
  /home/john/Thunderbird/logs/poe_api_calls.jsonl

Each line: {"ts": "2026-05-19T20:00:00Z", "model": "Gemini-2.5-Flash", "points": 100}
"""
import json, sqlite3, os, time
from pathlib import Path
from datetime import datetime, timezone

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
LOG = Path.home() / "Thunderbird" / "logs" / "poe_api_calls.jsonl"


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS poe_snapshots (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,
          points_balance INTEGER,
          points_used_today INTEGER,
          points_used_week INTEGER,
          points_used_month INTEGER,
          model_gemini_flash INTEGER DEFAULT 0,
          model_kimi_k2 INTEGER DEFAULT 0,
          estimated_cost_usd REAL,
          source TEXT DEFAULT 'log',
          UNIQUE(ts)
        )
    """)
    conn.commit()


def _read_log():
    if not LOG.exists():
        return []
    rows = []
    with open(LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _aggregate_since(cutoff: str):
    rows = _read_log()
    agg = {"gemini_flash": 0, "kimi_k2": 0, "total": 0}
    for r in rows:
        ts = r.get("ts", "")
        if ts < cutoff:
            continue
        model = r.get("model", "")
        points = r.get("points", 0)
        if "gemini" in model.lower():
            agg["gemini_flash"] += points
        elif "kimi" in model.lower():
            agg["kimi_k2"] += points
        agg["total"] += points
    return agg


def collect():
    conn = sqlite3.connect(str(DB), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    _ensure_table(conn)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = now.split("T")[0]
    week_ago = f"{datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp() - 7*86400:.0f}"
    month_ago = f"{datetime.fromisoformat(now.replace('Z', '+00:00')).timestamp() - 30*86400:.0f}"

    used_today = _aggregate_since(today + "T00:00:00Z")["total"]
    used_week = _aggregate_since(week_ago)["total"]
    used_month = _aggregate_since(month_ago)["total"]

    # For now, balance is unknown — we track consumption only. Future: scrape poe.com if needed.
    balance = None

    conn.execute("""
        INSERT OR IGNORE INTO poe_snapshots
        (ts, points_balance, points_used_today, points_used_week, points_used_month,
         model_gemini_flash, model_kimi_k2, estimated_cost_usd, source)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        now,
        balance,
        used_today,
        used_week,
        used_month,
        0,  # placeholder
        0,  # placeholder
        0.0,  # placeholder
        "log"
    ))
    conn.commit()
    conn.close()
    return {
        "snapshot_stored": True,
        "points_used_today": used_today,
        "points_used_week": used_week,
        "points_used_month": used_month,
        "balance": balance
    }


if __name__ == "__main__":
    result = collect()
    result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(json.dumps(result))
