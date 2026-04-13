#!/usr/bin/env python3
"""
Hale Scan Wirer — Output Integrator
Runs proactive scan, parses results, updates hale_brief.md with SCAN SUMMARY.
Sends HIGH priority findings to Telegram.

Author: Hale — 2026-04-12
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paths
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
SCRIPTS_DIR = THUNDERBIRD_ROOT / "scripts"
SCAN_RESULTS_PATH = THUNDERBIRD_ROOT / "hale_scan_results.json"
HALE_BRIEF_PATH = THUNDERBIRD_ROOT / "hale_brief.md"
TELEGRAM_GATEWAY = THUNDERBIRD_ROOT / "OpsCenter" / "thunderbird_telegram_gw.py"

# Telegram
COMMANDER_ID = 7554895206
MT = timezone(timedelta(hours=-6))


def run_scan():
    """Execute the proactive scan."""
    print("[wirer] Running proactive scan...")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "hale_proactive_scan.py")],
            cwd=THUNDERBIRD_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[wirer] Scan failed: {result.stderr}")
            return None
        print(f"[wirer] Scan output:\n{result.stdout}")
        return True
    except Exception as e:
        print(f"[wirer] Scan execution error: {e}")
        return None


def load_scan_results():
    """Load the JSON scan results."""
    try:
        with open(SCAN_RESULTS_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[wirer] Scan results file not found: {SCAN_RESULTS_PATH}")
        return None
    except json.JSONDecodeError as e:
        print(f"[wirer] Failed to parse scan results: {e}")
        return None


def format_scan_summary(scan_results):
    """Format scan results as markdown for hale_brief.md."""
    if not scan_results:
        return None

    lines = []
    lines.append("## SCAN SUMMARY")
    timestamp = scan_results.get("timestamp", datetime.now(MT).isoformat())
    lines.append(f"*Timestamp: {timestamp}*\n")

    high_priority = []
    medium_priority = []
    all_findings = []

    scans = scan_results.get("scans", {})

    # Deadline Radar
    deadlines = scans.get("deadline_radar", [])
    if deadlines:
        lines.append("### 📅 Deadline Radar")
        for item in deadlines:
            priority = item.get("priority", "MEDIUM")
            status = item.get("status", "UNKNOWN")
            client = item.get("client", "Unknown")
            days = item.get("days_out", "?")
            deadline_type = item.get("type", "Deadline")
            lines.append(
                f"- **{status}** | {client} ({deadline_type}) | {days}d out [**{priority}**]"
            )
            all_findings.append(
                {"type": "deadline", "priority": priority, "client": client, "days": days}
            )
            if priority == "HIGH":
                high_priority.append(f"📅 {client} {deadline_type} in {days} days")
            else:
                medium_priority.append(f"📅 {client} {deadline_type} in {days}d")
        lines.append("")

    # Stale Tasks
    stale_tasks = scans.get("stale_tasks", [])
    if stale_tasks:
        lines.append("### ⏱️ Stale Tasks (>48h)")
        for item in stale_tasks:
            priority = item.get("priority", "MEDIUM")
            mission_id = item.get("mission_id", "unknown")
            title = item.get("title", "Unknown")
            age = item.get("age_hours", "?")
            lines.append(f"- {mission_id}: {title} ({age}h old) [**{priority}**]")
            all_findings.append(
                {"type": "stale_task", "priority": priority, "title": title, "age": age}
            )
            if priority == "HIGH":
                high_priority.append(f"⏱️ Stale task: {title} ({age}h old)")
            else:
                medium_priority.append(f"⏱️ {title} ({age}h)")
        lines.append("")

    # Staff Gaps
    staff_gaps = scans.get("staff_gaps", [])
    if staff_gaps:
        lines.append("### 👥 Staff Gaps (7+ days idle)")
        for item in staff_gaps:
            priority = item.get("priority", "MEDIUM")
            staff_id = item.get("staff_id", "unknown")
            days_idle = item.get("days_idle", "?")
            lines.append(f"- {staff_id}: {days_idle} days idle [**{priority}**]")
            all_findings.append(
                {"type": "staff_gap", "priority": priority, "staff": staff_id, "days": days_idle}
            )
            if priority == "HIGH":
                high_priority.append(f"👥 {staff_id} idle {days_idle}d")
        lines.append("")

    # Data Consistency
    consistency = scans.get("data_consistency", [])
    if consistency:
        lines.append("### ⚖️ Data Consistency Issues")
        for item in consistency:
            priority = item.get("priority", "MEDIUM")
            issue = item.get("issue", "Unknown issue")
            lines.append(f"- {issue} [**{priority}**]")
            all_findings.append({"type": "consistency", "priority": priority, "issue": issue})
            if priority == "HIGH":
                high_priority.append(f"⚖️ {issue}")
        lines.append("")

    # Conflict Detection
    conflicts = scans.get("conflict_detection", [])
    if conflicts:
        lines.append("### ⚠️ Priority Conflicts")
        for item in conflicts:
            priority = item.get("priority", "MEDIUM")
            issue = item.get("issue", "Unknown conflict")
            lines.append(f"- {issue} [**{priority}**]")
            all_findings.append({"type": "conflict", "priority": priority, "issue": issue})
            if priority == "HIGH":
                high_priority.append(f"⚠️ {issue}")
        lines.append("")

    # Summary footer
    total = len(all_findings)
    high_count = len(high_priority)
    medium_count = len(medium_priority)
    lines.append(
        f"**Summary:** {total} total findings | **{high_count} HIGH** | {medium_count} MEDIUM\n"
    )

    return "\n".join(lines), high_priority, medium_priority


def update_hale_brief(scan_summary):
    """Update hale_brief.md with SCAN SUMMARY section."""
    if not scan_summary:
        return False

    try:
        # Read current brief
        if HALE_BRIEF_PATH.exists():
            current = HALE_BRIEF_PATH.read_text()
        else:
            current = ""

        # Remove old SCAN SUMMARY section if it exists
        if "## SCAN SUMMARY" in current:
            # Find the section and remove it (keep everything after it)
            lines = current.split("\n")
            new_lines = []
            in_scan_section = False
            for line in lines:
                if line.startswith("## SCAN SUMMARY"):
                    in_scan_section = True
                    continue
                if in_scan_section and line.startswith("## "):
                    # Found next section header, stop skipping
                    in_scan_section = False
                if not in_scan_section:
                    new_lines.append(line)
            current = "\n".join(new_lines).strip()

        # Prepend new SCAN SUMMARY at the top
        updated = scan_summary + "\n\n" + current

        HALE_BRIEF_PATH.write_text(updated)
        print(f"[wirer] Updated hale_brief.md with SCAN SUMMARY")
        return True
    except Exception as e:
        print(f"[wirer] Failed to update hale_brief.md: {e}")
        return False


def send_telegram_alert(high_priority_items):
    """Send HIGH priority findings to Commander via Telegram."""
    if not high_priority_items:
        return

    if not TELEGRAM_GATEWAY.exists():
        print("[wirer] Telegram gateway not found, skipping alert")
        return

    try:
        message = "🦅 **HALE PROACTIVE SCAN — HIGH PRIORITY ITEMS**\n\n"
        for i, item in enumerate(high_priority_items, 1):
            message += f"{i}. {item}\n"

        message += f"\n*See hale_brief.md for full SCAN SUMMARY*"

        # Call telegram gateway
        result = subprocess.run(
            [sys.executable, str(TELEGRAM_GATEWAY)],
            input=f"send {COMMANDER_ID}\n{message}",
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(f"[wirer] Telegram alert sent ({len(high_priority_items)} items)")
        else:
            print(f"[wirer] Telegram alert failed: {result.stderr}")
    except Exception as e:
        print(f"[wirer] Telegram alert error: {e}")


def main():
    """Orchestrate the complete wiring flow."""
    print("\n" + "=" * 60)
    print("HALE SCAN WIRER — Integration Engine")
    print("=" * 60)

    # 1. Run scan
    if not run_scan():
        print("[wirer] Scan execution failed, aborting")
        return False

    # 2. Load results
    scan_results = load_scan_results()
    if not scan_results:
        print("[wirer] No scan results to process")
        return False

    # 3. Format summary
    scan_summary, high_priority, medium_priority = format_scan_summary(scan_results)
    if not scan_summary:
        print("[wirer] Failed to format scan summary")
        return False

    # 4. Update hale_brief.md
    if not update_hale_brief(scan_summary):
        print("[wirer] Failed to update hale_brief.md")
        return False

    # 5. Send Telegram alert for HIGH priority
    if high_priority:
        send_telegram_alert(high_priority)

    # 6. Summary
    print("[wirer] ✅ Scan wiring complete")
    print(f"[wirer] HIGH priority: {len(high_priority)}")
    print(f"[wirer] MEDIUM priority: {len(medium_priority)}")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
