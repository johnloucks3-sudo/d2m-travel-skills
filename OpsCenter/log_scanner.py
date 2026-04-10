#!/usr/bin/env python3
"""
Thunderbird Log Scanner — Comprehensive operational monitoring
Dreams2Memories Travel, LLC

Scans all logs, JSON state files, and inboxes for operational issues.
"""

import json
import logging
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/scan_report.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("log_scanner")

# Config
THUNDERBIRD = Path("/home/john/Thunderbird")
OPS = THUNDERBIRD / "OpsCenter"
LOG_DIR = THUNDERBIRD / "logs"
STATE_DIR = THUNDERBIRD / "state"

# Critical patterns to monitor
CRITICAL_PATTERNS = [
    r"error",
    r"failed",
    r"timeout",
    r"rc=[1-9]",
    r"UNREAD",
    r"stuck",
    r"conflict",
    r"401",
    r"409",
    r"rate limit",
    r"quota",
    r"invalid.*api",
    r"api.*key",
    r"oauth",
    r"authentication",
]


def scan_inboxes() -> dict:
    """Scan all inboxes for UNREAD tasks and issues."""
    results = {}

    # Claude inbox
    claude_inbox = THUNDERBIRD / "claude_inbox.md"
    if claude_inbox.exists():
        with open(claude_inbox, "r") as f:
            content = f.read()
        results["claude_inbox"] = {
            "unread_tasks": content.count("status: UNREAD"),
            "total_tasks": content.count("## TASK:"),
            "recent_tasks": content.count(datetime.now().strftime("%Y-%m-%d")),
        }

    # OpenCode inbox
    opencode_inbox = OPS / "collaboration" / "opencode_inbox.md"
    if opencode_inbox.exists():
        with open(opencode_inbox, "r") as f:
            content = f.read()
        results["opencode_inbox"] = {
            "unread_tasks": content.count("status: UNREAD"),
            "total_tasks": content.count("## TASK:"),
            "recent_tasks": content.count(datetime.now().strftime("%Y-%m-%d")),
        }

    return results


def scan_logs() -> dict:
    """Scan all log files for errors and issues."""
    results = {}

    # Scan all .log files in logs directory
    for log_file in LOG_DIR.rglob("*.log"):
        try:
            with open(log_file, "r") as f:
                content = f.read().lower()

            issues = []
            for pattern in CRITICAL_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(pattern)

            if issues:
                results[str(log_file)] = {
                    "issues_found": len(issues),
                    "issues": issues[:5],  # Top 5 issues
                    "size_kb": os.path.getsize(log_file) / 1024,
                }

        except Exception as e:
            results[str(log_file)] = {"error": str(e)}

    return results


def scan_state_files() -> dict:
    """Scan state JSON files for operational issues."""
    results = {}

    # Scan all .json files in state directory
    for state_file in STATE_DIR.rglob("*.json"):
        try:
            with open(state_file, "r") as f:
                data = json.load(f)

            # Check for stale data (older than 24 hours)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(state_file))
            stale = (datetime.now() - file_mtime) > timedelta(hours=24)

            # Check for error indicators
            error_indicators = []
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, str) and any(
                        p in value.lower() for p in ["error", "fail", "invalid"]
                    ):
                        error_indicators.append(key)

            if stale or error_indicators:
                results[str(state_file)] = {
                    "stale_hours": (datetime.now() - file_mtime).total_seconds() / 3600,
                    "error_indicators": error_indicators,
                    "size_kb": os.path.getsize(state_file) / 1024,
                }

        except Exception as e:
            results[str(state_file)] = {"error": str(e)}

    return results


def generate_report() -> dict:
    """Generate comprehensive scan report."""
    log.info("🔍 Starting comprehensive log scan")

    report = {
        "timestamp": datetime.now().isoformat(),
        "inboxes": scan_inboxes(),
        "logs": scan_logs(),
        "state_files": scan_state_files(),
        "summary": {},
        "healthy": True,
    }

    # Generate summary
    total_unread = report["inboxes"].get("claude_inbox", {}).get(
        "unread_tasks", 0
    ) + report["inboxes"].get("opencode_inbox", {}).get("unread_tasks", 0)

    total_log_issues = sum(
        len(log_issues.get("issues", [])) for log_issues in report["logs"].values()
    )
    total_state_issues = len(report["state_files"])

    report["summary"] = {
        "total_unread_tasks": total_unread,
        "total_log_issues": total_log_issues,
        "total_state_issues": total_state_issues,
        "overall_issues": total_unread + total_log_issues + total_state_issues,
    }

    # Determine overall health
    if total_unread > 5 or total_log_issues > 10 or total_state_issues > 5:
        report["healthy"] = False

    log.info(
        f"Scan complete: {'✅ HEALTHY' if report['healthy'] else '❌ UNHEALTHY'} — {report['summary']['overall_issues']} issues"
    )

    # Save report
    report_file = LOG_DIR / "comprehensive_scan_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    try:
        report = generate_report()

        # Print quick summary
        print(f"\n📊 SCAN SUMMARY:")
        print(f"Unread tasks: {report['summary']['total_unread_tasks']}")
        print(f"Log issues: {report['summary']['total_log_issues']}")
        print(f"State issues: {report['summary']['total_state_issues']}")
        print(f"Overall: {'✅ HEALTHY' if report['healthy'] else '❌ UNHEALTHY'}")

        # Exit code for monitoring
        exit(0 if report["healthy"] else 1)

    except Exception as e:
        log.error(f"Scan failed: {e}")
        exit(1)
