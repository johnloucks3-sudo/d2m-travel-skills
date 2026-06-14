#!/usr/bin/env python3
"""
thunderbird-lessons-implementation-tracker — Compute lessons_implementation_rate_pct.

Per WING EXERCISE doctrine: track what fraction of AAR lessons have been
implemented. Surfaces the metric weekly for Commander review.

Reads:
  - OpsCenter/collaboration/blackboard.md (lessons learned entries)
  - hale_decisions.md (implemented decisions)
  - Any AAR files in OpsCenter/

Schedule: Weekly Sunday 17:00 MDT via systemd timer
Output:   OpsCenter/logs/lessons_tracker.log
          OpsCenter/data/lessons_tracker.json
          hale_decisions.md entry with metric
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
BLACKBOARD = ROOT / "OpsCenter/collaboration/blackboard.md"
HALE_DECISIONS = ROOT / "hale_decisions.md"
AAR_DIR = ROOT / "OpsCenter"
LOG_PATH = ROOT / "OpsCenter/logs/lessons_tracker.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/lessons_tracker.jsonl"
TRACKER_STATE = ROOT / "OpsCenter/data/lessons_tracker.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LESSONS-TRACKER] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)


def scan_lessons(text: str) -> list[dict]:
    """Extract lessons learned from markdown text."""
    lessons = []
    # Pattern: "Lesson:" or "Lessons Learned:" or AAR items
    patterns = [
        r"(?:^|\n)(?:Lesson|Lesson Learned|AAR|Action Item)[:\s]+(.+?)(?=\n(?:Lesson|AAR|Action Item|$)|\Z)",
        r"\*\*Lesson\*\*:?\s*(.+?)(?=\n|\Z)",
        r"- Lesson: (.+?)(?=\n|\Z)",
        r"L\d+: (.+?)(?=\n|\Z)",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
            lesson_text = m.group(1).strip()[:200]
            if lesson_text and len(lesson_text) > 10:
                # Check if marked as implemented
                implemented = bool(re.search(
                    r"(?:implemented|completed|done|resolved|fixed|closed)",
                    lesson_text + text[m.end():m.end()+100],
                    re.IGNORECASE,
                ))
                lessons.append({
                    "text": lesson_text,
                    "implemented": implemented,
                })
    return lessons


def scan_wing_exercise_files() -> list[dict]:
    """Scan all relevant files for lesson tracking."""
    all_lessons = []

    sources = [BLACKBOARD, HALE_DECISIONS]
    # Also scan any AAR files
    for fp in AAR_DIR.glob("*AAR*"):
        sources.append(fp)
    for fp in AAR_DIR.glob("*lessons*"):
        sources.append(fp)

    for fp in sources:
        if not fp.exists():
            continue
        try:
            text = fp.read_text(errors="ignore")
            lessons = scan_lessons(text)
            for l in lessons:
                l["source"] = fp.name
            all_lessons.extend(lessons)
        except Exception as e:
            log.debug(f"Could not read {fp}: {e}")

    # Deduplicate by first 50 chars of text
    seen = set()
    deduped = []
    for l in all_lessons:
        key = l["text"][:50]
        if key not in seen:
            seen.add(key)
            deduped.append(l)

    return deduped


def compute_metric(lessons: list[dict]) -> dict:
    total = len(lessons)
    implemented = sum(1 for l in lessons if l["implemented"])
    rate_pct = round(implemented / total * 100, 1) if total > 0 else 0.0

    return {
        "total_lessons": total,
        "implemented": implemented,
        "pending": total - implemented,
        "lessons_implementation_rate_pct": rate_pct,
    }


def load_history() -> list[dict]:
    try:
        if TRACKER_STATE.exists():
            data = json.loads(TRACKER_STATE.read_text())
            return data.get("history", [])
    except Exception:
        pass
    return []


def write_hale_decision(metric: dict, run_dt: datetime) -> None:
    rate = metric["lessons_implementation_rate_pct"]
    health = "GOOD" if rate >= 70 else ("NEEDS_ATTENTION" if rate >= 40 else "POOR")

    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Weekly lessons implementation rate computed\n",
        f"**Metric:** `lessons_implementation_rate_pct` = {rate}% [{health}]\n",
        f"  Total lessons: {metric['total_lessons']} | Implemented: {metric['implemented']} | Pending: {metric['pending']}\n",
        "**Domain:** WING EXERCISE doctrine\n**Type:** weekly metric\n**Outcome:** surfaced to Commander\n",
    ]
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)
    log.info(f"lessons_implementation_rate_pct = {rate}% ({health})")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Lessons implementation tracker — {run_dt.date()}")

    lessons = scan_wing_exercise_files()
    log.info(f"Found {len(lessons)} lessons across all sources")

    metric = compute_metric(lessons)
    metric["ts"] = run_dt.isoformat()
    metric["lessons_sample"] = [
        {"text": l["text"][:100], "implemented": l["implemented"], "source": l.get("source", "?")}
        for l in lessons[:20]
    ]

    # Save history
    history = load_history()
    history.append({k: v for k, v in metric.items() if k != "lessons_sample"})
    history = history[-52:]  # Keep 52 weeks

    TRACKER_STATE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_STATE.write_text(json.dumps({"history": history, "latest": metric}, indent=2))

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(metric) + "\n")

    write_hale_decision(metric, run_dt)

    print(f"\nlessons_implementation_rate_pct = {metric['lessons_implementation_rate_pct']}%")
    print(f"  Total: {metric['total_lessons']} | Implemented: {metric['implemented']} | Pending: {metric['pending']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
