#!/usr/bin/env python3
"""
thunderbird-commander-context-restore — Session-open context delivery.

Triggered on Commander login/session start.
Delivers a concise brief to d2mconcierge:
  - Last 24h autonomous decisions (count + highlights)
  - Open P0/P1 nags from nag queue
  - Any stale overdue items (WF-17 > 24h)
  - Disk / credential alerts if any
  - Mission board P0 open items

This script is designed to be run once per Commander session,
not on a recurring schedule. Called by session_startup_hook.py
or can be added as a systemd path unit triggered on login.

Schedule: At session start OR daily 06:00 MDT (fallback)
Output:   Gmail draft (d2mconcierge) THUNDERBIRD-Commander-Review
          OpsCenter/logs/context_restore.log
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
HALE_DECISIONS = ROOT / "hale_decisions.md"
MISSION_BOARD = ROOT / "OpsCenter/mission_board.json"
NAG_FILE = ROOT / "OpsCenter/data/nag_queue.json"
BLACKBOARD = ROOT / "OpsCenter/collaboration/blackboard.md"
LOG_PATH = ROOT / "OpsCenter/logs/context_restore.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONTEXT-RESTORE] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)


def get_recent_decisions(hours: int = 24) -> list[dict]:
    if not HALE_DECISIONS.exists():
        return []
    text = HALE_DECISIONS.read_text(errors="ignore")
    decisions = []
    cutoff = datetime.now() - timedelta(hours=hours)
    pattern = r"###\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+—\s+(.+?)\n"
    for m in re.finditer(pattern, text):
        try:
            ts = datetime.strptime(m.group(1).strip(), "%Y-%m-%d %H:%M:%S")
            if ts >= cutoff:
                decisions.append({"ts": m.group(1).strip(), "title": m.group(2).strip()})
        except ValueError:
            continue
    return decisions


def get_open_p0p1_missions() -> list[dict]:
    try:
        data = json.loads(MISSION_BOARD.read_text())
        missions = data.get("missions", [])
        return [
            m for m in missions
            if m.get("priority") in ("P0", "P1", 0, 1, "0", "1")
            and m.get("status") not in ("completed", "closed", "done", "cancelled")
        ][:10]
    except Exception:
        return []


def get_nags() -> list[dict]:
    try:
        if NAG_FILE.exists():
            data = json.loads(NAG_FILE.read_text())
            nags = data if isinstance(data, list) else data.get("nags", [])
            today = date.today()
            active = []
            for nag in nags:
                due_str = nag.get("due") or nag.get("date")
                if due_str:
                    try:
                        due = date.fromisoformat(str(due_str))
                        if due <= today:
                            active.append(nag)
                    except Exception:
                        active.append(nag)
                else:
                    active.append(nag)
            return active[:10]
    except Exception:
        pass
    return []


def get_blackboard_alerts() -> list[str]:
    """Pull last 10 ALERT lines from blackboard."""
    if not BLACKBOARD.exists():
        return []
    text = BLACKBOARD.read_text(errors="ignore")
    alerts = []
    for line in text.splitlines():
        if "ALERT" in line.upper() or "CRITICAL" in line.upper():
            alerts.append(line.strip()[:120])
    return alerts[-10:]


def draft_context_brief(run_dt: datetime) -> None:
    decisions = get_recent_decisions(24)
    missions = get_open_p0p1_missions()
    nags = get_nags()
    alerts = get_blackboard_alerts()

    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        # Decisions section
        if decisions:
            dec_rows = "".join(
                f"<li style='font-size:12px;'>{d['ts'][5:16]} — {d['title'][:80]}</li>"
                for d in decisions[-10:]
            )
            dec_section = f"<p><strong>Last 24h Autonomous Decisions ({len(decisions)}):</strong></p><ul>{dec_rows}</ul>"
        else:
            dec_section = "<p>No autonomous decisions in last 24h.</p>"

        # Missions section
        if missions:
            mission_rows = "".join(
                f"<li><b>[{m.get('priority','?')}]</b> {str(m.get('title',''))[:70]}</li>"
                for m in missions
            )
            mission_section = f"<p><strong>Open P0/P1 Missions ({len(missions)}):</strong></p><ul>{mission_rows}</ul>"
        else:
            mission_section = "<p>No open P0/P1 missions.</p>"

        # Nags section
        if nags:
            nag_rows = "".join(
                f"<li>{nag.get('text', nag.get('message', str(nag)))[:80]}</li>"
                for nag in nags
            )
            nag_section = f"<p><strong>Active Nags ({len(nags)}):</strong></p><ul>{nag_rows}</ul>"
        else:
            nag_section = ""

        # Alerts section
        if alerts:
            alert_rows = "".join(f"<li style='color:red;'>{a}</li>" for a in alerts)
            alert_section = f"<p><strong>Blackboard Alerts:</strong></p><ul>{alert_rows}</ul>"
        else:
            alert_section = ""

        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>🦅 Commander — session context brief as of {run_dt.strftime('%H:%M MDT, %B %d, %Y')}.</p>
{dec_section}
{mission_section}
{nag_section}
{alert_section}
<p>Standing by.</p>
<p>— Hale</p>
</div>"""

        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[CONTEXT BRIEF] Session Open — {run_dt.strftime('%b %d %H:%M')}",
            body=body,
        )
        log.info("Context restore draft created")
    except Exception as e:
        log.warning(f"Could not create Gmail draft: {e}")
        # Print to stdout instead
        print(f"\n🦅 CONTEXT BRIEF — {run_dt.strftime('%Y-%m-%d %H:%M')}")
        print(f"Decisions (24h): {len(decisions)}")
        print(f"Open P0/P1: {len(missions)}")
        print(f"Active nags: {len(nags)}")
        if alerts:
            print(f"Alerts: {len(alerts)}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Commander context restore — {run_dt.isoformat()}")
    draft_context_brief(run_dt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
