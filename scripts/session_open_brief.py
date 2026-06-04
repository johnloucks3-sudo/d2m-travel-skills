#!/usr/bin/env python3
"""
Session Continuity Protocol — Session-Open Brief
=================================================
Dreams2Memories Travel, LLC | scripts/session_open_brief.py

Computes a 10-15 line delta brief for session opening. Sources:

    session_autosave_latest.md     — last session checkpoint (commits, changes)
    hale_state.json                — wing health, WF-17 queue, financial pulse
    hale_brief.md                  — last compressed brief
    OpsCenter/collaboration/blackboard.md — inter-agent state

Outputs to stdout. Invoke at session start via:

    python3 /home/john/Thunderbird/scripts/session_open_brief.py

Document this as the /session-open skill or explicit Read on session start.
Do NOT add as @-auto-load in CLAUDE.md (burns tokens every turn).

Usage:
    python3 scripts/session_open_brief.py
    python3 scripts/session_open_brief.py --json       # JSON output for scripting
    python3 scripts/session_open_brief.py --verbose    # Extended detail
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

THUNDERBIRD = Path.home() / "Thunderbird"
AUTOSAVE = THUNDERBIRD / "session_autosave_latest.md"
HALE_STATE = THUNDERBIRD / "hale_state.json"
HALE_BRIEF = THUNDERBIRD / "hale_brief.md"
BLACKBOARD = THUNDERBIRD / "OpsCenter" / "collaboration" / "blackboard.md"
WF17_QUEUE = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"
FPD_STATE = THUNDERBIRD / "OpsCenter" / "state" / "fpd_state.json"
BRIEF_DELTA = THUNDERBIRD / "OpsCenter" / "state" / "brief_delta.json"


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _read_text(path: Path, limit: int = 2000) -> str:
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")[:limit]
        except Exception:
            return ""
    return ""


def _parse_autosave(text: str) -> dict:
    """Extract key fields from session_autosave_latest.md."""
    lines = text.splitlines()
    generated = ""
    recent_commits: list[str] = []
    uncommitted: list[str] = []

    in_commits = False
    in_uncommitted = False

    for line in lines:
        if "Generated:" in line:
            generated = line.replace("## Generated:", "").strip()
        elif "### Recent Commits" in line:
            in_commits = True
            in_uncommitted = False
        elif "### Uncommitted Changes" in line:
            in_uncommitted = True
            in_commits = False
        elif line.startswith("- ") and in_commits and len(recent_commits) < 3:
            recent_commits.append(line[2:].strip())
        elif line.startswith("- ") and in_uncommitted and len(uncommitted) < 5:
            uncommitted.append(line[2:].strip())
        elif line.startswith("###") and in_uncommitted:
            in_uncommitted = False

    return {
        "generated": generated,
        "recent_commits": recent_commits,
        "uncommitted_count": len(uncommitted),
        "uncommitted_sample": uncommitted,
    }


def _parse_wf17_queue(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if e.get("status") in ("queued", "voice_drafted"):
                items.append(e)
        except Exception:
            pass
    return items


def _parse_fpd_state(state: dict) -> dict:
    overdue = [k for k, v in state.items() if v.get("status") == "OVERDUE"]
    received = [k for k, v in state.items() if v.get("status") == "RECEIVED"]
    watch = [k for k, v in state.items() if v.get("status") == "OPEN"]
    return {"overdue": overdue, "received": received, "open": watch}


def _parse_blackboard(text: str) -> str:
    """Extract the Active tasks and Open items lines from blackboard."""
    lines = []
    for line in text.splitlines():
        if any(kw in line for kw in ("Active tasks:", "Open items:", "Next priority:", "Budget:")):
            lines.append(line.strip())
        if len(lines) >= 4:
            break
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main brief computation
# ---------------------------------------------------------------------------

def compute_session_brief(verbose: bool = False) -> dict:
    today = date.today()
    now = datetime.now().strftime("%H:%M MT")

    # Load all sources
    autosave_text = _read_text(AUTOSAVE, 4000)
    autosave = _parse_autosave(autosave_text)

    hale_state = _load_json(HALE_STATE)
    wf17 = _parse_wf17_queue(WF17_QUEUE)
    fpd_raw = _load_json(FPD_STATE)
    fpd = _parse_fpd_state(fpd_raw)
    brief_delta = _load_json(BRIEF_DELTA)
    blackboard_text = _read_text(BLACKBOARD, 800)
    blackboard_summary = _parse_blackboard(blackboard_text)

    # Wing health
    health = hale_state.get("wing_health", {})
    health_flags: list[str] = []
    for k, v in health.items():
        if isinstance(v, dict):
            continue
        v_str = str(v).upper()
        if "OFFLINE" in v_str or "ERROR" in v_str or "FAIL" in v_str:
            health_flags.append(f"{k}=OFFLINE")

    # Financial
    fin = hale_state.get("financial_pulse", {})
    pipeline = fin.get("total_d2m_pipeline", 0)

    # Assemble
    lines: list[str] = [
        f"🦅 SESSION OPEN — {today.isoformat()} {now}",
        "=" * 50,
    ]

    # Last session checkpoint
    if autosave.get("generated"):
        lines.append(f"Last checkpoint: {autosave['generated']}")
    if autosave.get("recent_commits"):
        lines.append(f"Recent commits ({len(autosave['recent_commits'])}):")
        for c in autosave["recent_commits"][:2]:
            lines.append(f"  {c[:70]}")

    uncommitted = autosave.get("uncommitted_count", 0)
    if uncommitted:
        lines.append(f"Uncommitted changes: {uncommitted} files")

    lines.append("")

    # WF-17 queue
    if wf17:
        lines.append(f"WF-17 queue: {len(wf17)} drafts awaiting Commander send")
        for e in wf17[:3]:
            deadline = e.get("deadline", "?")
            lines.append(f"  - {e.get('client')} TP {e.get('tp_id')} [{e.get('status')}] due {deadline}")
    else:
        lines.append("WF-17 queue: empty")

    lines.append("")

    # FPD state
    if fpd["overdue"]:
        lines.append(f"FPD OVERDUE ({len(fpd['overdue'])}): {', '.join(fpd['overdue'][:4])}")
    if fpd["received"]:
        lines.append(f"FPD RECEIVED (suppressed): {', '.join(fpd['received'][:4])}")

    # Financial snapshot
    if pipeline:
        lines.append(f"Pipeline: ${pipeline:,.0f}")

    lines.append("")

    # Health flags
    if health_flags:
        lines.append(f"HEALTH ALERTS: {', '.join(health_flags)}")
    else:
        lines.append("Wing health: all systems nominal")

    # Blackboard
    if blackboard_summary:
        lines.append("")
        lines.append("Blackboard:")
        for bl in blackboard_summary.splitlines():
            lines.append(f"  {bl}")

    # Brief delta
    delta_date = brief_delta.get("date", "")
    if delta_date and delta_date != today.isoformat():
        lines.append(f"(Last brief: {delta_date})")

    lines.append("")
    lines.append("Ready. Type your first task or ask for the full brief.")

    return {
        "text": "\n".join(lines),
        "line_count": len(lines),
        "wf17_count": len(wf17),
        "fpd_overdue_count": len(fpd["overdue"]),
        "health_flags": health_flags,
        "pipeline": pipeline,
        "generated_at": datetime.now().isoformat(),
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Session-open delta brief")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--verbose", action="store_true", help="Extended detail")
    args = p.parse_args()

    result = compute_session_brief(verbose=args.verbose)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["text"])


if __name__ == "__main__":
    main()
