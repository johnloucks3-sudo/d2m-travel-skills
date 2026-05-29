#!/usr/bin/env python3
"""Usage status chyron — one-line display for terminal.
   python3 core/ops/usage_chyron.py"""
import sqlite3, json
from pathlib import Path

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"

conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

c = conn.execute("SELECT * FROM claude_usage_reports ORDER BY ts DESC LIMIT 1").fetchone()
p = conn.execute("SELECT * FROM poe_activity_reports ORDER BY ts DESC LIMIT 1").fetchone()
z = conn.execute("SELECT * FROM zen_usage ORDER BY ts DESC LIMIT 1").fetchone()
conn.close()

parts = []

# Claude
if c:
    s = c["sonnet_weekly_pct"]
    m = c["monthly_spent_usd"]
    l = c["monthly_limit_usd"]
    al = c["all_models_weekly_pct"]
    parts.append(f"Claude: Sonnet {s:.0f}% | All {al:.0f}% | ${m:.0f}/${l:.0f}")

# Poe
if p:
    bal = p["points_balance"]
    used = p["points_used_today"]
    if bal is not None:
        parts.append(f"Poe: {bal:,}pts (today {used or 0})")
    elif used:
        parts.append(f"Poe: {used}pts today")

# ZEN
if z:
    ch = z["calls_per_hour"]
    cd = z["calls_per_day"]
    parts.append(f"ZEN: {ch}/hr {cd}/day")

if not parts:
    print("📡 no data yet")
else:
    print(" │ ".join(parts))
