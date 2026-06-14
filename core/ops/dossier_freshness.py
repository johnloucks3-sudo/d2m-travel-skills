#!/usr/bin/env python3
"""
d2m-dossier-freshness — Alert on stale dossiers for active trips in 60-day window.

A dossier is "stale" if:
  - Client departs within 60 days AND
  - Dossier file last modified > 14 days ago

Schedule: Daily 05:30 MDT via systemd timer
Output:   OpsCenter/logs/dossier_freshness.log
          hale_decisions.md on stale dossiers
          Blackboard alert
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
DOSSIERS_DIR = ROOT / "dossiers"
BLACKBOARD_DIR = ROOT / "Blackboard/clients"
LOG_PATH = ROOT / "OpsCenter/logs/dossier_freshness.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/dossier_freshness.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"
BLACKBOARD = ROOT / "OpsCenter/collaboration/blackboard.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DOSSIER-FRESHNESS] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

WINDOW_DAYS = 60
STALE_DAYS = 14


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def check_dossier_freshness() -> list[dict]:
    today = date.today()
    horizon = today + timedelta(days=WINDOW_DAYS)
    stale = []

    for fp in DOSSIERS_DIR.glob("DOSSIER_*.md"):
        text = fp.read_text(errors="ignore")
        client_name = fp.stem.replace("DOSSIER_", "")

        # Extract departure date
        dep_date = None
        for pattern in [
            r"(?:Departure|Embark|Depart|Start\s+Date)[:\s]+(\d{4}-\d{2}-\d{2})",
            r"(?:Departure|Embark|Depart|Start\s+Date)[:\s]+(\w+ \d+, \d{4})",
            r"(?:Departure|Embark)[:\s]+(\w+ \d+, \d{4})",
        ]:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                dep_date = parse_date(m.group(1))
                break

        if not dep_date:
            continue

        # Skip already departed (allow 1 day buffer)
        if dep_date < today - timedelta(days=1):
            continue

        # In window?
        if dep_date > horizon:
            continue

        # Check freshness
        mtime = datetime.fromtimestamp(fp.stat().st_mtime).date()
        days_since_update = (today - mtime).days
        days_until_dep = (dep_date - today).days

        if days_since_update > STALE_DAYS:
            stale.append({
                "client": client_name,
                "file": str(fp),
                "departure_date": str(dep_date),
                "days_until_departure": days_until_dep,
                "last_updated": str(mtime),
                "days_stale": days_since_update,
                "urgency": "HIGH" if days_until_dep <= 14 else "MEDIUM",
            })
            log.warning(
                f"STALE: {client_name} — departs {dep_date} ({days_until_dep}d), "
                f"last updated {days_since_update}d ago"
            )
        else:
            log.info(f"OK: {client_name} — departs {dep_date}, updated {days_since_update}d ago")

    return sorted(stale, key=lambda x: x["days_until_departure"])


def write_hale_decision(stale: list[dict], run_dt: datetime) -> None:
    if not stale:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Dossier freshness check — {len(stale)} stale dossier(s) for upcoming travel\n",
    ]
    for s in stale:
        lines.append(
            f"  - [{s['urgency']}] {s['client']}: departs {s['departure_date']} "
            f"({s['days_until_departure']}d), dossier {s['days_stale']}d stale\n"
        )
    lines.append("**Domain:** Client prep / Dossier management\n**Type:** proactive alert\n**Outcome:** surfaced to Commander\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def write_blackboard_alert(stale: list[dict], run_dt: datetime) -> None:
    if not stale:
        return
    high = [s for s in stale if s["urgency"] == "HIGH"]
    alert = (
        f"\n## DOSSIER FRESHNESS ALERT — {run_dt.strftime('%Y-%m-%d %H:%M')} MDT\n"
        f"{len(stale)} stale dossier(s): {len(high)} HIGH urgency (departs ≤14d)\n"
    )
    for s in stale:
        alert += f"  - [{s['urgency']}] {s['client']}: departs {s['departure_date']}, {s['days_stale']}d stale\n"
    try:
        with open(BLACKBOARD, "a") as f:
            f.write(alert)
    except Exception as e:
        log.warning(f"Could not write blackboard: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Dossier freshness check — {run_dt.date()}")

    stale = check_dossier_freshness()

    entry = {
        "ts": run_dt.isoformat(),
        "stale_count": len(stale),
        "stale": stale,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if stale:
        write_hale_decision(stale, run_dt)
        write_blackboard_alert(stale, run_dt)
        log.warning(f"{len(stale)} stale dossier(s) flagged")
    else:
        log.info("All dossiers current")

    return 0


if __name__ == "__main__":
    sys.exit(main())
