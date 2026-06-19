#!/usr/bin/env python3
"""
dead_code_scan.py — Vulture-based dead code scanner for Thunderbird codebase.
Runs weekly via audit_bot. Output to OpsCenter/state/dead_code_report.txt.
Exit 0 always (vulture exits 1 when findings exist — that's informational, not failure).
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
VULTURE = ROOT / ".venv/bin/vulture"
REPORT = ROOT / "OpsCenter/state/dead_code_report.txt"

SCAN_PATHS = [
    str(ROOT / "core"),
    str(ROOT / "scripts"),
    str(ROOT / "supertimer"),
    str(ROOT / "agents"),
    str(ROOT / "api"),
]

EXCLUDE_PATTERNS = ",".join([
    "*/storage/*",
    "*/__pycache__/*",
    "*/.venv/*",
    "*/node_modules/*",
    "*/email.soak*",
    "*_updated.py",
])


def run() -> int:
    if not VULTURE.exists():
        print("vulture not found at", VULTURE, file=sys.stderr)
        return 1

    result = subprocess.run(
        [str(VULTURE), "--min-confidence", "80", "--exclude", EXCLUDE_PATTERNS]
        + SCAN_PATHS,
        capture_output=True,
        text=True,
    )

    findings = result.stdout.strip()
    line_count = len(findings.splitlines()) if findings else 0

    report_lines = [
        f"# Dead Code Report — {datetime.now().strftime('%Y-%m-%d %H:%M')} MT",
        f"# Files scanned: core/ scripts/ supertimer/ agents/ api/",
        f"# Min confidence: 80%  |  Findings: {line_count}",
        "",
        findings if findings else "(none — codebase clean)",
        "",
        f"# Run: {' '.join([str(VULTURE), '--min-confidence', '80'] + SCAN_PATHS)}",
    ]

    REPORT.write_text("\n".join(report_lines))
    print(f"dead_code_scan: {line_count} findings → {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
