#!/usr/bin/env python3
"""
thunderbird-anti-theater-audit — Weekly 10% sample of autonomous actions for mission alignment.

Per WING EXERCISE doctrine / DOTMLPF-P anti-theater rule:
"Did this action move the mission? Or was it theater?"

Randomly samples 10% of hale_decisions.md entries from the past 7 days.
For each sampled decision, evaluates whether it was:
  - MISSION-LINKED: directly tied to a P0/P1 mission or client deliverable
  - OPERATIONAL: necessary ops (token refresh, health check) — acceptable overhead
  - THEATER: activity that looks productive but moves nothing

Outputs summary to Commander.

Schedule: Weekly Friday 18:00 MDT via systemd timer
Output:   OpsCenter/logs/anti_theater_audit.log
          OpsCenter/data/anti_theater_results.json
          Gmail draft (d2mconcierge) with findings
"""

import json
import logging
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
HALE_DECISIONS = ROOT / "hale_decisions.md"
LOG_PATH = ROOT / "OpsCenter/logs/anti_theater_audit.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/anti_theater_audit.jsonl"
RESULTS_FILE = ROOT / "OpsCenter/data/anti_theater_results.json"
HALE_DECISIONS_OUT = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ANTI-THEATER] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

SAMPLE_PCT = 0.10  # 10% sample

# Keywords that indicate mission-linked action
MISSION_KEYWORDS = [
    "client", "email", "draft", "booking", "dossier", "commission", "payment",
    "fare", "itinerary", "flight", "hotel", "transfer", "testimonial",
    "mission", "p0", "p1", "deliverable", "commander",
]

# Keywords that indicate theater (activity without output)
THEATER_KEYWORDS = [
    "check", "scan", "monitor", "poll", "verify", "audit", "review",
    "status", "health", "ping", "keepalive", "refresh",
]

# Operational overhead (acceptable)
OPERATIONAL_KEYWORDS = [
    "token", "oauth", "credential", "keepalive", "cache", "warm",
    "backup", "sync", "log", "checkpoint",
]


def classify_decision(text: str) -> str:
    text_lower = text.lower()
    mission_score = sum(1 for k in MISSION_KEYWORDS if k in text_lower)
    theater_score = sum(1 for k in THEATER_KEYWORDS if k in text_lower)
    ops_score = sum(1 for k in OPERATIONAL_KEYWORDS if k in text_lower)

    if mission_score >= 2:
        return "MISSION-LINKED"
    if ops_score >= 2:
        return "OPERATIONAL"
    if theater_score >= 3 and mission_score == 0:
        return "THEATER"
    if mission_score >= 1:
        return "MISSION-LINKED"
    return "OPERATIONAL"


def extract_decisions_last_7d() -> list[dict]:
    if not HALE_DECISIONS.exists():
        return []

    text = HALE_DECISIONS.read_text(errors="ignore")
    decisions = []
    cutoff = datetime.now() - timedelta(days=7)

    pattern = r"###\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+—\s+(.+?)\n(.*?)(?=\n###|\Z)"
    for m in re.finditer(pattern, text, re.DOTALL):
        try:
            ts = datetime.strptime(m.group(1).strip(), "%Y-%m-%d %H:%M:%S")
            if ts >= cutoff:
                full_text = m.group(2).strip() + " " + m.group(3).strip()
                decisions.append({
                    "ts": m.group(1).strip(),
                    "title": m.group(2).strip(),
                    "full_text": full_text[:300],
                    "classification": classify_decision(full_text),
                })
        except ValueError:
            continue

    return decisions


def draft_anti_theater_report(sample: list[dict], all_decisions: list[dict], run_dt: datetime) -> None:
    total = len(all_decisions)
    sampled = len(sample)
    theater = [d for d in sample if d["classification"] == "THEATER"]
    mission = [d for d in sample if d["classification"] == "MISSION-LINKED"]
    ops = [d for d in sample if d["classification"] == "OPERATIONAL"]

    theater_pct = round(len(theater) / sampled * 100, 1) if sampled > 0 else 0
    health = "GOOD" if theater_pct < 20 else ("NEEDS_ATTENTION" if theater_pct < 40 else "POOR")

    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        def rows(items):
            return "".join(
                f"<li style='font-size:12px;'>{d['ts'][5:16]} — {d['title'][:70]}</li>"
                for d in items
            )

        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>WEEKLY ANTI-THEATER AUDIT — {run_dt.strftime('%B %d, %Y')}</strong></p>
<p>Sampled {sampled} of {total} decisions from the past 7 days ({SAMPLE_PCT*100:.0f}% sample).</p>
<table border='1' cellpadding='6' style='border-collapse:collapse;color:#0000ff;'>
<tr><th>Category</th><th>Count</th><th>%</th></tr>
<tr><td>Mission-Linked</td><td>{len(mission)}</td><td>{round(len(mission)/sampled*100,1) if sampled else 0}%</td></tr>
<tr><td>Operational</td><td>{len(ops)}</td><td>{round(len(ops)/sampled*100,1) if sampled else 0}%</td></tr>
<tr style='color:{"red" if theater_pct >= 40 else "inherit"};'><td><b>Theater</b></td><td><b>{len(theater)}</b></td><td><b>{theater_pct}%</b></td></tr>
</table>
<p><strong>Health: {health}</strong> (theater rate {theater_pct}%)</p>
{"<p><strong>Theater items to review:</strong></p><ul>" + rows(theater) + "</ul>" if theater else "<p>No theater items detected in sample.</p>"}
<p>— Hale (Anti-Theater Auditor)</p>
</div>"""

        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[ANTI-THEATER] Weekly Audit — {health} ({theater_pct}% theater)",
            body=body,
        )
        log.info(f"Anti-theater audit: {health} — {theater_pct}% theater in {sampled} sampled decisions")
    except Exception as e:
        log.warning(f"Could not draft report: {e}")
        print(f"Anti-Theater Audit: {health} — {theater_pct}% theater rate")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Anti-theater audit — {run_dt.date()}")

    all_decisions = extract_decisions_last_7d()
    log.info(f"Found {len(all_decisions)} decisions in last 7 days")

    if not all_decisions:
        log.info("No decisions to audit")
        return 0

    n_sample = max(1, int(len(all_decisions) * SAMPLE_PCT))
    sample = random.sample(all_decisions, min(n_sample, len(all_decisions)))
    log.info(f"Sampling {len(sample)} decisions")

    draft_anti_theater_report(sample, all_decisions, run_dt)

    result = {
        "ts": run_dt.isoformat(),
        "total_decisions": len(all_decisions),
        "sampled": len(sample),
        "theater": len([d for d in sample if d["classification"] == "THEATER"]),
        "mission_linked": len([d for d in sample if d["classification"] == "MISSION-LINKED"]),
        "operational": len([d for d in sample if d["classification"] == "OPERATIONAL"]),
        "sample": sample,
    }

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(result) + "\n")

    # Save latest results
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
