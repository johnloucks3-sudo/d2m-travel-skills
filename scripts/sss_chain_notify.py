#!/usr/bin/env python3
"""SSS chain notify scanner — read-only.

Scans OpsCenter/mission_board.json for SSS-shaped missions (those carrying an
`ocr_chain` field) that are actively waiting on offices. Emits a JSON report of
which SSS sheets still need a coordination notification.

Read-only against the board: this script never writes to mission_board.json.
Actually resolving a pending state (who "resolves" it) is a separate design
question, out of scope here.

Usage:
    python3 scripts/sss_chain_notify.py           # dry-run (default): prints report JSON only
    python3 scripts/sss_chain_notify.py --live    # also pages Commander once for the whole batch
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BOARD_PATH = Path(__file__).resolve().parent.parent / "OpsCenter" / "mission_board.json"

IN_COORDINATION = "in_coordination"
STATUS_PENDING = "pending"


def scan_board(board_path: Path = BOARD_PATH) -> dict:
    """Return {"needs_notify": [...], "scan_time": "..."} from the real board."""
    if not board_path.exists():
        raise FileNotFoundError(f"mission board not found: {board_path}")

    data = json.loads(board_path.read_text())
    missions = data.get("missions", [])
    if not isinstance(missions, list):
        raise ValueError(f"expected 'missions' to be a list, got {type(missions).__name__}")

    needs_notify = []
    for mission in missions:
        if not isinstance(mission, dict):
            continue
        if "ocr_chain" not in mission:
            continue
        if mission.get("status") != IN_COORDINATION:
            # Only actively-waiting sheets are notify candidates. Closed missions
            # are DONE even if stale pending entries linger in their chain.
            continue
        for entry in mission.get("ocr_chain", []):
            if not isinstance(entry, dict):
                continue
            if entry.get("status") == STATUS_PENDING:
                needs_notify.append({
                    "sss_id": mission.get("id", ""),
                    "title": mission.get("title", ""),
                    "office": entry.get("office", ""),
                })

    return {
        "needs_notify": needs_notify,
        "scan_time": datetime.now(timezone.utc).isoformat(),
    }


def format_report(report: dict) -> str:
    """Single-line-ish JSON for terminal + a readable body for the notify call."""
    return json.dumps(report, indent=2, ensure_ascii=False)


def notify_live_body(report: dict) -> str:
    parser = argparse.ArgumentParser(
        description="Report SSS sheets awaiting coordination (read-only scan of the mission board)."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="(default) Print the report JSON only — do not notify.",
    )
    mode.add_argument(
        "--live",
        action="store_true",
        help="Also queue one WINDOW notification to the Commander for the whole batch.",
    )
    args = parser.parse_args(argv)

    report = scan_board()
    print(format_report(report))

    needs_notify = report["needs_notify"]
    if args.live and needs_notify:
        from core.comms.commander_channel import notify

        notify(
            kind="ops",
            title=f"SSS chain — {len(needs_notify)} sheet(s) awaiting coordination",
            body_md=notify_live_body(report),
            urgency="WINDOW",
            dedup_key="sss-chain-notify-scan",
            source="sss_chain_notify",
        )
        print(
            f"[live] queued one WINDOW notification for {len(needs_notify)} "
            "pending office/sheet pair(s).",
            file=sys.stderr,
        )

    return 0


def notify_live_body(report: dict) -> str:
    lines = [
        "Coordination still pending on these staff summary sheets:",
        "",
    ]
    for item in report["needs_notify"]:
        lines.append(
            f"- **{item['sss_id']}** ({item['office']} pending): "
            f"{item['title'] or '(no title)'}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())