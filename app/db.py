"""
D2M Cruise Intel Database — app layer
Reads from T2_MASTER_CRUISE CSV and cruise_content.db intel articles.
"""
import csv
import sqlite3
from pathlib import Path
from typing import Optional

APP_DB = Path(__file__).parent / "d2m_app.db"
CRUISE_CSV = Path("/home/john/Thunderbird/output/T2_MASTER_CRUISE_OCTOBER_NOVEMBER_2026.csv")
INTEL_DB = Path("/home/john/Thunderbird/state/cruise_content.db")
INTAKE_QUEUE = Path("/home/john/Thunderbird/app/intake_queue.jsonl")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(APP_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sailings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cruise_line TEXT,
            ship_name TEXT,
            departure_date TEXT,
            month TEXT,
            days INTEGER,
            route TEXT,
            voyage_code TEXT,
            price_usd TEXT,
            on_deluxecruises TEXT,
            on_perx TEXT,
            on_ponant TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS intake (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submitted_at TEXT DEFAULT (datetime('now')),
            name TEXT,
            email TEXT,
            phone TEXT,
            destination TEXT,
            travel_window TEXT,
            budget TEXT,
            party_size TEXT,
            comments TEXT,
            consent INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new'
        )
    """)

    conn.commit()

    # Import CSV if sailings table is empty
    c.execute("SELECT COUNT(*) FROM sailings")
    if c.fetchone()[0] == 0:
        _import_csv(c)
        conn.commit()

    conn.close()


def _import_csv(cursor):
    if not CRUISE_CSV.exists():
        return
    with open(CRUISE_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO sailings
                (cruise_line, ship_name, departure_date, month, days, route,
                 voyage_code, price_usd, on_deluxecruises, on_perx, on_ponant)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                row.get("cruise_line", ""),
                row.get("ship_name", ""),
                row.get("departure_date", ""),
                row.get("month", ""),
                int(row.get("days", 0) or 0),
                row.get("route", ""),
                row.get("voyage_code", ""),
                row.get("price_usd", ""),
                row.get("on_deluxecruises", ""),
                row.get("on_perx", ""),
                row.get("on_ponant", ""),
            ))


def search_sailings(
    cruise_line: Optional[str] = None,
    destination: Optional[str] = None,
    month: Optional[str] = None,
    min_days: Optional[int] = None,
    max_days: Optional[int] = None,
    limit: int = 50,
) -> list:
    conn = get_db()
    c = conn.cursor()
    query = "SELECT * FROM sailings WHERE 1=1"
    params = []
    if cruise_line and cruise_line != "all":
        query += " AND LOWER(cruise_line) = LOWER(?)"
        params.append(cruise_line)
    if destination:
        query += " AND (LOWER(route) LIKE ? OR LOWER(ship_name) LIKE ?)"
        kw = f"%{destination.lower()}%"
        params.extend([kw, kw])
    if month and month != "all":
        query += " AND LOWER(month) = LOWER(?)"
        params.append(month)
    if min_days:
        query += " AND days >= ?"
        params.append(min_days)
    if max_days:
        query += " AND days <= ?"
        params.append(max_days)
    query += " ORDER BY departure_date ASC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_featured_sailings(limit: int = 6) -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM sailings
        WHERE cruise_line IN ('Regent Seven Seas', 'Silversea', 'Seabourn', 'Viking')
        ORDER BY departure_date ASC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_cruise_lines() -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT cruise_line FROM sailings ORDER BY cruise_line")
    rows = [r[0] for r in c.fetchall() if r[0]]
    conn.close()
    return rows


def get_months() -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT month FROM sailings WHERE month != '' ORDER BY departure_date ASC")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return list(dict.fromkeys(rows))


def get_stats() -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM sailings")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT cruise_line) FROM sailings")
    lines = c.fetchone()[0]
    conn.close()
    return {"total_sailings": total, "cruise_lines": lines}


def save_intake(data: dict) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO intake (name, email, phone, destination, travel_window, budget, party_size, comments, consent)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        data.get("name", ""),
        data.get("email", ""),
        data.get("phone", ""),
        data.get("destination", ""),
        data.get("travel_window", ""),
        data.get("budget", ""),
        data.get("party_size", ""),
        data.get("comments", ""),
        1 if data.get("consent") else 0,
    ))
    row_id = c.lastrowid
    conn.commit()
    conn.close()
    return row_id
