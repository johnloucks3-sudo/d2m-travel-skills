#!/usr/bin/env python3
"""
hale-decision-log — Daily roll-up of all autonomous decisions for Commander.

Reads hale_decisions.md, extracts all decisions from the past 24 hours,
formats a clean summary and creates a Gmail draft for Commander review.

Schedule: Daily 17:30 MDT via systemd timer
Output:   OpsCenter/logs/hale_decision_log.log
          Gmail draft (d2mconcierge) with daily decision summary
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
HALE_DECISIONS = ROOT / "hale_decisions.md"
LOG_PATH = ROOT / "OpsCenter/logs/hale_decision_log.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/hale_decision_log.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DECISION-LOG] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)


def parse_decisions_last_24h() -> list[dict]:
    """Extract decisions from hale_decisions.md in the last 24 hours."""
    if not HALE_DECISIONS.exists():
        return []

    text = HALE_DECISIONS.read_text(errors="ignore")
    decisions = []
    now = datetime.now()
    cutoff = now - timedelta(hours=24)

    # Match decision blocks: ### YYYY-MM-DD HH:MM:SS — ...
    pattern = r"###\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+—\s+(.+?)\n(.*?)(?=\n###|\Z)"
    for m in re.finditer(pattern, text, re.DOTALL):
        ts_str = m.group(1).strip()
        title = m.group(2).strip()
        body = m.group(3).strip()

        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

        if ts < cutoff:
            continue

        # Extract key fields from body
        decision_text = ""
        domain = ""
        d_type = ""
        outcome = ""
        tier = ""

        for line in body.splitlines():
            if line.startswith("**Decision:**"):
                decision_text = line.replace("**Decision:**", "").strip()
            elif line.startswith("**Domain:**"):
                domain = line.replace("**Domain:**", "").strip()
            elif line.startswith("**Type:**"):
                d_type = line.replace("**Type:**", "").strip()
            elif line.startswith("**Outcome:**"):
                outcome = line.replace("**Outcome:**", "").strip()
            elif "Tier T" in line:
                t_match = re.search(r"Tier (T\d)", line)
                if t_match:
                    tier = t_match.group(1)

        decisions.append({
            "ts": ts_str,
            "title": title,
            "decision": decision_text or title,
            "domain": domain,
            "type": d_type,
            "outcome": outcome,
            "tier": tier,
        })

    return sorted(decisions, key=lambda x: x["ts"])


def draft_daily_summary(decisions: list[dict], run_dt: datetime) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        if not decisions:
            body_content = "<p>No autonomous decisions in the past 24 hours.</p>"
        else:
            rows = ""
            for d in decisions:
                rows += (
                    f"<tr><td style='padding:4px;font-size:12px;'>{d['ts'][11:16]}</td>"
                    f"<td style='padding:4px;'>{d.get('tier','?')}</td>"
                    f"<td style='padding:4px;'>{d['decision'][:80]}</td>"
                    f"<td style='padding:4px;'>{d.get('domain','')}</td>"
                    f"<td style='padding:4px;'>{d.get('outcome','')}</td></tr>\n"
                )
            body_content = f"""
<p>{len(decisions)} autonomous decision(s) logged in the past 24 hours:</p>
<table border='1' cellpadding='4' style='border-collapse:collapse;color:#0000ff;font-family:Georgia;font-size:13px;'>
<tr style='background:#e8e0d4;'><th>Time</th><th>Tier</th><th>Decision</th><th>Domain</th><th>Outcome</th></tr>
{rows}
</table>"""

        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>HALE DAILY DECISION LOG — {run_dt.strftime('%B %d, %Y')}</strong></p>
{body_content}
<p>Full log: <code>hale_decisions.md</code></p>
<p>— Hale</p>
</div>"""

        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[HALE DECISIONS] Daily Log — {run_dt.strftime('%b %d, %Y')} ({len(decisions)} decisions)",
            body=body,
        )
        log.info(f"Daily decision log draft created: {len(decisions)} decisions")
    except Exception as e:
        log.warning(f"Could not create Gmail draft: {e}")
        # Still print to stdout
        print(f"\nHale Decision Log — {run_dt.date()}")
        for d in decisions:
            print(f"  [{d['ts']}] {d['tier']} — {d['decision'][:60]}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Hale decision log — {run_dt.date()}")

    decisions = parse_decisions_last_24h()
    log.info(f"Found {len(decisions)} decision(s) in last 24h")

    draft_daily_summary(decisions, run_dt)

    entry = {
        "ts": run_dt.isoformat(),
        "decisions_found": len(decisions),
        "decision_ids": [d["ts"] for d in decisions],
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
