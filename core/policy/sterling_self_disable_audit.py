#!/usr/bin/env python3
"""
Sterling A7 — SELF-DISABLE-001 Audit Report Generator
======================================================
core/policy/sterling_self_disable_audit.py

Called by A7 Sterling's Sunday sweep. Analyzes SELF-DISABLE-001 block events
and produces a detailed audit report. Updates metrics dashboard.

Usage:
    python3 core/policy/sterling_self_disable_audit.py
    python3 core/policy/sterling_self_disable_audit.py --json  # for dashboard
    python3 core/policy/sterling_self_disable_audit.py --flag-critical  # flag if RED

Output:
    Metrics written to: OpsCenter/a7_metrics_dashboard.json
    Report written to: logs/a7_self_disable_audit_report_latest.txt
"""

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


REPO_ROOT = Path("/home/john/Thunderbird")
SELF_DISABLE_AUDIT_LOG = REPO_ROOT / "logs" / "policy_audit_self_disable_001.jsonl"
METRICS_DASHBOARD = REPO_ROOT / "OpsCenter" / "a7_metrics_dashboard.json"
REPORT_FILE = REPO_ROOT / "logs" / "a7_self_disable_audit_report_latest.txt"


def read_audit_events() -> List[Dict]:
    """Read SELF-DISABLE-001 audit events."""
    if not SELF_DISABLE_AUDIT_LOG.exists():
        return []

    events = []
    try:
        with open(SELF_DISABLE_AUDIT_LOG, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"WARNING: Error reading audit log: {e}", file=sys.stderr)

    return events


def analyze_events(events: List[Dict]) -> Dict:
    """Analyze block events and return metrics."""
    if not events:
        return {
            "status": "GREEN",
            "total_blocks": 0,
            "by_tool": {},
            "by_file": {},
            "critical_files": [],
            "patterns": [],
        }

    # Group by tool
    by_tool = defaultdict(int)
    by_file = defaultdict(int)
    critical_files = set()

    # Protected files that are most critical
    critical_protected = {
        "wing_policy.py",
        "rules_registry.py",
        "run_commander_directive_sweep.py",
        "relay_send.py",
    }

    for event in events:
        ctx = event.get("ctx", {})
        tool = ctx.get("tool", "unknown")
        by_tool[tool] += 1

        # Extract file path
        file_path = ctx.get("file_path") or ""
        command = ctx.get("command") or ""
        file_ref = file_path or command

        if file_ref:
            by_file[file_ref] += 1

            # Check if critical file
            for critical in critical_protected:
                if critical in file_ref:
                    critical_files.add(file_ref)

    status = "RED" if critical_files else ("YELLOW" if by_tool else "GREEN")

    return {
        "status": status,
        "total_blocks": len(events),
        "by_tool": dict(by_tool),
        "by_file": dict(sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:10]),
        "critical_files": sorted(list(critical_files)),
        "patterns": list(by_tool.keys()),
    }


def update_dashboard(metrics: Dict) -> None:
    """Update the A7 metrics dashboard with audit results."""
    try:
        if METRICS_DASHBOARD.exists():
            data = json.loads(METRICS_DASHBOARD.read_text())
        else:
            data = {}

        # Ensure nested structure
        if "policy_audit" not in data:
            data["policy_audit"] = {}

        data["policy_audit"]["self_disable_001"] = {
            "status": metrics["status"],
            "total_blocks": metrics["total_blocks"],
            "by_tool": metrics["by_tool"],
            "critical_files_count": len(metrics["critical_files"]),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        METRICS_DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
        METRICS_DASHBOARD.write_text(json.dumps(data, indent=2))
        print(f"✓ Updated metrics dashboard: {METRICS_DASHBOARD}")
    except Exception as e:
        print(f"ERROR: Failed to update dashboard: {e}", file=sys.stderr)


def write_report(metrics: Dict, events: List[Dict]) -> None:
    """Write human-readable audit report."""
    try:
        lines = [
            "=" * 70,
            "A7 STERLING — SELF-DISABLE-001 BLOCK AUDIT REPORT",
            "=" * 70,
            f"Generated: {datetime.now(timezone.utc).isoformat()}",
            "",
            f"STATUS: {metrics['status']}",
            f"Total Block Events: {metrics['total_blocks']}",
            "",
        ]

        if metrics["status"] == "RED":
            lines.extend([
                "🔴 CRITICAL FILES TARGETED:",
                "",
            ])
            for f in metrics["critical_files"]:
                lines.append(f"  • {f}")
            lines.append("")

        if metrics["by_tool"]:
            lines.extend([
                "BLOCKS BY TOOL:",
                "",
            ])
            for tool, count in sorted(
                metrics["by_tool"].items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  {tool:20s}: {count:3d} blocks")
            lines.append("")

        if metrics["by_file"]:
            lines.extend([
                "TOP 10 TARGETED FILES/COMMANDS:",
                "",
            ])
            for file_ref, count in metrics["by_file"].items():
                short_ref = file_ref[-50:] if len(file_ref) > 50 else file_ref
                lines.append(f"  {count:2d}x  {short_ref}")
            lines.append("")

        lines.extend([
            "AUDIT FILE:",
            f"  {SELF_DISABLE_AUDIT_LOG}",
            "",
            "POLICY RULE:",
            "  SELF-DISABLE-001 — Wing policy engine is self-protecting.",
            "  No unauthorized modifications to policy engine or protected email/relay files.",
            "",
            "ACTION ITEMS:",
        ])

        if metrics["status"] == "RED":
            lines.extend([
                "  1. IMMEDIATE: Review critical file access attempts",
                "  2. Contact system administrator",
                "  3. Verify no policy engine corruption",
                "  4. Document and investigate source of attempts",
            ])
        elif metrics["status"] == "YELLOW":
            lines.extend([
                "  1. Monitor for patterns in block events",
                "  2. Ensure authorized users understand the restrictions",
                "  3. Keep audit log for forensic analysis",
            ])
        else:
            lines.append("  ✓ No action required — system clean")

        report_text = "\n".join(lines)
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(report_text)
        print(f"✓ Report written: {REPORT_FILE}")
    except Exception as e:
        print(f"ERROR: Failed to write report: {e}", file=sys.stderr)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A7 Sterling — SELF-DISABLE-001 Audit")
    parser.add_argument(
        "--json", action="store_true", help="Output metrics as JSON (for dashboard)"
    )
    parser.add_argument(
        "--flag-critical",
        action="store_true",
        help="Exit with code 1 if RED status (for automation)",
    )

    args = parser.parse_args()

    # Read and analyze
    events = read_audit_events()
    metrics = analyze_events(events)

    # Output
    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        # Write report and update dashboard
        write_report(metrics, events)
        update_dashboard(metrics)

    # Flag if critical
    if args.flag_critical and metrics["status"] == "RED":
        print("ERROR: RED status — critical files targeted", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
