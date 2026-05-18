"""
Hale Autonomous Decision Logger — Cross-Context Persistence Layer
Resolves: 2026-05-04 CRITICAL BLOCKER — Autonomy Persistence Gap

Usage (OpenCode, headless Claude, or any context):
    from core.ai_infra.hale_decision_logger import log_decision
    log_decision("Routed task to Sonnet — complexity exceeded DeepSeek threshold", tier="T1", outcome="correct")

CLI usage (from OpenCode bash):
    python3 core/ai_infra/hale_decision_logger.py --decision "..." --tier T1 --domain "Task Execution"
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_DECISIONS_FILE = Path("/home/john/Thunderbird/hale_decisions.md")
_TIMEZONE = ZoneInfo("America/Denver")
_TIER_POINTS = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}


def log_decision(
    decision: str,
    *,
    tier: str = "T1",
    domain: str = "Task Execution",
    outcome: str = "correct",
    brain: str = "Self (Hale — COS autonomy governance)",
    context: str = "",
) -> str:
    """
    Append an autonomous decision entry to hale_decisions.md.

    Returns the formatted entry string.
    """
    if not _DECISIONS_FILE.exists():
        raise FileNotFoundError(f"hale_decisions.md not found at {_DECISIONS_FILE}")

    tier_upper = tier.upper()
    points = _TIER_POINTS.get(tier_upper, 1)
    ts = datetime.now(_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

    entry_lines = [
        f"\n### {ts} — Autonomous Decision ({tier_upper})\n",
        f"**Decision:** {decision}\n",
    ]
    if context:
        entry_lines.append(f"**Context:** {context}\n")
    entry_lines += [
        f"\n**Domain:** {domain}\n",
        f"**Type:** routine\n",
        f"**Outcome:** {outcome}\n",
        f"**Trust Points:** +{points}\n",
    ]

    entry = "".join(entry_lines)

    with open(_DECISIONS_FILE, "a") as f:
        f.write(entry)

    return entry


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log an autonomous Hale decision to hale_decisions.md"
    )
    parser.add_argument("--decision", required=True, help="Decision text")
    parser.add_argument("--tier", default="T1", choices=["T0", "T1", "T2", "T3"])
    parser.add_argument("--domain", default="Task Execution")
    parser.add_argument("--outcome", default="correct")
    parser.add_argument("--brain", default="Self (Hale — COS autonomy governance)")
    parser.add_argument("--context", default="")
    args = parser.parse_args()

    entry = log_decision(
        args.decision,
        tier=args.tier,
        domain=args.domain,
        outcome=args.outcome,
        brain=args.brain,
        context=args.context,
    )
    print(f"Logged to hale_decisions.md:\n{entry}")


if __name__ == "__main__":
    main()
