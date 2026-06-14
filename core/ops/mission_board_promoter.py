#!/usr/bin/env python3
"""
thunderbird-mission-board-promoter — Auto-promote stale P2 missions to P1.

P2 missions older than AGE_THRESHOLD_DAYS are promoted to P1
so they don't silently rot in the backlog.

Schedule: Every 6 hours via systemd timer
Output:   OpsCenter/logs/mission_board_promoter.log
          hale_decisions.md on promotions
"""

import json
import logging
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LOG_PATH = ROOT / "OpsCenter/logs/mission_board_promoter.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/mission_board_promoter.jsonl"
MISSION_BOARD = ROOT / "OpsCenter/mission_board.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MISSION-PROMOTER] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

AGE_THRESHOLD_DAYS = 21  # Promote P2→P1 after this many days
SYNC_SCRIPT = ROOT / "OpsCenter/mission_board_sync.py"


def load_missions() -> list[dict]:
    try:
        data = json.loads(MISSION_BOARD.read_text())
        return data.get("missions", [])
    except Exception as e:
        log.error(f"Could not load mission board: {e}")
        return []


def parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def find_stale_p2(missions: list[dict]) -> list[dict]:
    today = date.today()
    stale = []

    for m in missions:
        if m.get("priority") not in ("P2", 2, "2"):
            continue
        if m.get("status") in ("completed", "closed", "done", "cancelled"):
            continue

        created_str = m.get("created_at") or m.get("created") or m.get("date_created")
        if not created_str:
            continue

        created_date = parse_date(str(created_str))
        if not created_date:
            continue

        age_days = (today - created_date).days
        if age_days >= AGE_THRESHOLD_DAYS:
            stale.append({**m, "_age_days": age_days})
            log.info(f"PROMOTE: {m.get('id','?')} '{m.get('title','?')[:50]}' — {age_days}d old")

    return stale


def promote_mission(mission_id: str, title: str) -> bool:
    try:
        result = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "update", mission_id, "priority:P1"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
        )
        if result.returncode == 0:
            log.info(f"Promoted {mission_id}: {title[:40]}")
            return True
        else:
            log.warning(f"Failed to promote {mission_id}: {result.stderr[:200]}")
            return False
    except Exception as e:
        log.warning(f"Error promoting {mission_id}: {e}")
        return False


def write_hale_decision(promoted: list[dict], run_dt: datetime) -> None:
    if not promoted:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T1)\n",
        f"**Decision:** Mission board promoter — {len(promoted)} P2 mission(s) promoted to P1 (age ≥{AGE_THRESHOLD_DAYS}d)\n",
    ]
    for m in promoted:
        lines.append(f"  - {m.get('id','?')}: {str(m.get('title',''))[:60]} ({m['_age_days']}d old)\n")
    lines.append("**Domain:** Mission board / Backlog management\n**Type:** autonomous maintenance\n**Outcome:** missions promoted\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Mission board promoter — {run_dt.isoformat()}")

    missions = load_missions()
    if not missions:
        log.info("No missions loaded — done")
        return 0

    stale_p2 = find_stale_p2(missions)
    log.info(f"Found {len(stale_p2)} stale P2 mission(s) of {len(missions)} total")

    promoted = []
    for m in stale_p2:
        mission_id = str(m.get("id", ""))
        if not mission_id:
            continue
        if promote_mission(mission_id, str(m.get("title", ""))):
            promoted.append(m)

    entry = {
        "ts": run_dt.isoformat(),
        "missions_checked": len(missions),
        "stale_p2": len(stale_p2),
        "promoted": len(promoted),
        "detail": [{"id": m.get("id"), "title": str(m.get("title", ""))[:60], "age_days": m["_age_days"]} for m in promoted],
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if promoted:
        write_hale_decision(promoted, run_dt)
        log.info(f"{len(promoted)} mission(s) promoted P2→P1")
    else:
        log.info("No promotions needed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
