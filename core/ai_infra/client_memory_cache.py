#!/usr/bin/env python3
"""Dossier-Level Memory Cache — MISSION-043.
Per-client reasoning cache in SQLite.
Key: client_short_name. Value: structured travel DNA.
Both OC and CC read/write same cache.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(ROOT, "storage", "client_memory.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS client_memory (
    client_key TEXT PRIMARY KEY,
    travel_dna TEXT NOT NULL,
    preferences TEXT DEFAULT '{}',
    comm_style TEXT DEFAULT '{}',
    decision_patterns TEXT DEFAULT '{}',
    red_flags TEXT DEFAULT '[]',
    last_updated TEXT NOT NULL,
    source_dossier TEXT DEFAULT ''
);
"""

def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn

def get_client(client_key):
    conn = _get_db()
    row = conn.execute("SELECT * FROM client_memory WHERE client_key = ?", (client_key,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def set_client(client_key, travel_dna, preferences=None, comm_style=None, decision_patterns=None, red_flags=None, source_dossier=""):
    conn = _get_db()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("""
        INSERT OR REPLACE INTO client_memory
        (client_key, travel_dna, preferences, comm_style, decision_patterns, red_flags, last_updated, source_dossier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        client_key,
        json.dumps(travel_dna) if isinstance(travel_dna, dict) else travel_dna,
        json.dumps(preferences or {}),
        json.dumps(comm_style or {}),
        json.dumps(decision_patterns or {}),
        json.dumps(red_flags or []),
        ts,
        source_dossier
    ))
    conn.commit()
    conn.close()
    return ts

def list_clients():
    conn = _get_db()
    rows = conn.execute("SELECT client_key, last_updated, source_dossier FROM client_memory ORDER BY last_updated DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_client(client_key):
    conn = _get_db()
    conn.execute("DELETE FROM client_memory WHERE client_key = ?", (client_key,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for c in list_clients():
            print(f"{c['client_key']:20s} last: {c['last_updated']:25s} source: {c['source_dossier']}")
    elif len(sys.argv) > 2 and sys.argv[1] == "get":
        c = get_client(sys.argv[2])
        if c:
            print(f"Client: {c['client_key']}")
            print(f"DNA: {c['travel_dna'][:200]}...")
            print(f"Updated: {c['last_updated']}")
        else:
            print(f"No cache for: {sys.argv[2]}")
    else:
        print("Usage: python3 client_memory_cache.py [list|get <key>]")
