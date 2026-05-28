#!/usr/bin/env python3
"""
Bryana Dashboard Generator — M-000
Reads dossiers + hale_state.json, writes bryana/data.json for the static dashboard.
Run directly or via systemd timer (every 5 min).
"""
import json
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
DOSSIER_DIR = THUNDERBIRD / "dossiers"
STATE_FILE = THUNDERBIRD / "hale_state.json"
SPSA_FILE = THUNDERBIRD / "logs" / "build_supervisor.spsa"
OUTPUT_FILE = THUNDERBIRD / "bryana" / "data.json"


def parse_dossier_frontmatter(path: Path) -> dict | None:
    """Extract YAML frontmatter from a dossier .md file."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---"):
            return None
        end = text.find("---", 3)
        if end == -1:
            return None
        fm = text[3:end].strip()
        data = {}
        for line in fm.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                data[k.strip()] = v.strip()
        return data
    except Exception:
        return None


def days_until(date_str: str) -> int | None:
    """Return days until a date string (YYYY-MM-DD). Negative = past."""
    try:
        d = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        return (d - date.today()).days
    except Exception:
        return None


def build_clients() -> list[dict]:
    """Read all active dossiers and extract client travel status."""
    clients = []
    for md_file in sorted(DOSSIER_DIR.glob("*.md")):
        if md_file.name == "CLAUDE.md":
            continue
        fm = parse_dossier_frontmatter(md_file)
        if not fm:
            continue
        if fm.get("status", "").lower() not in ("active", "booked", "planning"):
            continue

        departure = fm.get("departure", "")
        fpd = fm.get("fpd", "")
        departure_days = days_until(departure) if departure else None
        fpd_days = days_until(fpd) if fpd else None

        # Skip departures more than 3 years out or already 30+ days past
        if departure_days is not None and (departure_days < -30 or departure_days > 1100):
            continue

        clients.append({
            "client": fm.get("full_name") or fm.get("client", md_file.stem),
            "ship": fm.get("ship", ""),
            "voyage": fm.get("voyage", ""),
            "departure": departure,
            "departure_days": departure_days,
            "fpd": fpd,
            "fpd_days": fpd_days,
            "fpd_amount": fm.get("fpd_amount", ""),
            "status": fm.get("status", ""),
            "relationship": fm.get("relationship", "client"),
            "file": md_file.name,
        })

    # Sort: soonest departure first
    clients.sort(key=lambda c: c.get("departure_days") or 9999)
    return clients


def build_payment_events(clients: list[dict]) -> list[dict]:
    """Flag payment events: FPD within 30 days or overdue."""
    events = []
    for c in clients:
        fd = c.get("fpd_days")
        if fd is None:
            continue
        if fd < 0:
            label = f"OVERDUE by {abs(fd)} days"
            urgency = "overdue"
        elif fd == 0:
            label = "DUE TODAY"
            urgency = "today"
        elif fd <= 7:
            label = f"Due in {fd} days"
            urgency = "urgent"
        elif fd <= 30:
            label = f"Due in {fd} days"
            urgency = "upcoming"
        else:
            continue  # Not a near-term event

        amt = c.get("fpd_amount", "")
        try:
            amt_fmt = f"${int(float(str(amt).replace(',', ''))):,}"
        except Exception:
            amt_fmt = str(amt) if amt else "amount TBD"

        events.append({
            "client": c["client"],
            "ship": c["ship"],
            "fpd_date": c["fpd"],
            "fpd_days": fd,
            "amount": amt_fmt,
            "label": label,
            "urgency": urgency,
        })
    return events


def build_system_health() -> dict:
    """Read hale_state.json and SPSA for system status."""
    health = {
        "tess": "UNKNOWN",
        "telegram": "UNKNOWN",
        "mcp_server": "UNKNOWN",
        "last_updated": "unknown",
        "spsa_last": "",
        "pipeline_total": 0,
        "bookings_count": 0,
    }
    try:
        state = json.loads(STATE_FILE.read_text())
        wh = state.get("wing_health", {})
        fp = state.get("financial_pulse", {})

        health["tess"] = "ONLINE" if fp.get("tess_auth_status") == "ONLINE" else "OFFLINE"
        health["mcp_server"] = wh.get("mcp_server", "UNKNOWN")

        tg = wh.get("telegram_bots", {})
        d2mc = tg.get("D2MC2C", {}).get("status", "UNKNOWN")
        health["telegram"] = d2mc

        health["last_updated"] = state.get("_meta", {}).get("last_updated", "unknown")
        health["pipeline_total"] = fp.get("total_d2m_pipeline", 0)
        health["bookings_count"] = fp.get("sheet_bookings", 0)
    except Exception as e:
        health["error"] = str(e)

    # Last SPSA line
    try:
        if SPSA_FILE.exists():
            lines = [l.strip() for l in SPSA_FILE.read_text().splitlines() if l.strip()]
            health["spsa_last"] = lines[-1] if lines else ""
    except Exception:
        pass

    return health


def main():
    generated_at = datetime.now().isoformat()
    clients = build_clients()
    payment_events = build_payment_events(clients)
    system_health = build_system_health()

    data = {
        "generated_at": generated_at,
        "clients": clients,
        "payment_events": payment_events,
        "system_health": system_health,
        "summary": {
            "active_clients": len(clients),
            "payment_events": len(payment_events),
            "urgent_payments": sum(1 for e in payment_events if e["urgency"] in ("overdue", "today", "urgent")),
        },
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, indent=2))
    print(f"[{generated_at}] Bryana dashboard data written → {OUTPUT_FILE}")
    print(f"  Clients: {len(clients)} | Payment events: {len(payment_events)} | Health: TESS={system_health['tess']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
