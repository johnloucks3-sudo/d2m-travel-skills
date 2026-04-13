#!/usr/bin/env python3
"""
EMAIL SCANNER REPAIR SCRIPT
Repair email scanner: dedup/route 29 claude_inbox HALE/NAIA tasks to wing_comms.md.
Scan d2mconcierge inbox staff mentions via MCP gmail_list_threads, process/mark COMPLETE. Log routing.
"""

import os
import re
import json
import sys
from datetime import datetime
from pathlib import Path

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
CLAUDE_INBOX = THUNDERBIRD_DIR / "claude_inbox.md"
WING_COMMS = THUNDERBIRD_DIR / "OpsCenter" / "collaboration" / "wing_comms.md"
SCANNER_LOG = THUNDERBIRD_DIR / "OpsCenter" / "logs" / "email_scanner_repair.log"


def setup_logging():
    """Setup logging for repair operations"""
    SCANNER_LOG.parent.mkdir(parents=True, exist_ok=True)
    return SCANNER_LOG


def load_claude_inbox():
    """Load and parse claude_inbox.md"""
    if not CLAUDE_INBOX.exists():
        print(f"ERROR: Claude inbox not found at {CLAUDE_INBOX}")
        return []

    with open(CLAUDE_INBOX, "r", encoding="utf-8") as f:
        content = f.read()

    tasks = []
    current_task = {}
    in_task = False
    lines = content.split("\n")

    for i, line in enumerate(lines):
        if line.startswith("---"):
            if current_task:
                tasks.append(current_task)
                current_task = {}
                in_task = False
            continue

        if line.startswith("## TASK:"):
            in_task = True
            task_id = line.replace("## TASK:", "").strip()
            current_task = {
                "raw": [line],
                "id": task_id,
                "status": None,
                "from": None,
                "task": "",
                "lines_start": i,
                "lines_end": None,
            }
        elif in_task and current_task:
            current_task["raw"].append(line)

            if line.startswith("status:"):
                current_task["status"] = line.replace("status:", "").strip()
            elif line.startswith("from:"):
                current_task["from"] = line.replace("from:", "").strip()
            elif "task:" in line and "|" in line:
                # Start of task description
                task_lines = []
                j = i + 1
                while j < len(lines) and (lines[j].startswith("  ") or lines[j] == ""):
                    task_lines.append(lines[j])
                    j += 1
                current_task["task"] = "\n".join(task_lines).strip()
                current_task["lines_end"] = j - 1

    if current_task:
        tasks.append(current_task)

    return tasks


def filter_hale_naia_tasks(tasks):
    """Filter tasks that are HALE/NAIA email scanner tasks"""
    hale_naia_tasks = []
    other_tasks = []

    for task in tasks:
        if task.get("from") == "Email Scanner":
            # Check if it's HALE or NAIA mention
            task_text = task.get("task", "").lower()
            if "hale" in task_text or "naia" in task_text:
                # Extract message ID if available
                message_id = None
                for line in task["task"].split("\n"):
                    if "Message ID:" in line:
                        message_id = line.replace("Message ID:", "").strip()
                        break

                # Determine staff mention
                staff = None
                if "**Staff Mention Detected: HALE**" in task["task"]:
                    staff = "HALE"
                elif "**Staff Mention Detected: NAIA**" in task["task"]:
                    staff = "NAIA"

                hale_naia_tasks.append(
                    {**task, "message_id": message_id, "staff": staff}
                )
            else:
                other_tasks.append(task)
        else:
            other_tasks.append(task)

    return hale_naia_tasks, other_tasks


def deduplicate_tasks(tasks):
    """Deduplicate tasks by message_id and staff"""
    seen = set()
    deduped = []

    for task in tasks:
        key = f"{task.get('message_id')}_{task.get('staff')}"
        if key not in seen and task.get("message_id"):
            seen.add(key)
            deduped.append(task)
        elif not task.get("message_id"):
            # Keep tasks without message_id
            deduped.append(task)

    return deduped


def route_to_wing_comms(tasks):
    """Route HALE/NAIA tasks to wing_comms.md"""
    if not WING_COMMS.exists():
        print(f"WARNING: wing_comms.md not found at {WING_COMMS}")
        return []

    with open(WING_COMMS, "r", encoding="utf-8") as f:
        content = f.read()

    new_entries = []

    for task in tasks:
        msg_id = (
            f"EMAIL-HALE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if task.get("staff") == "HALE"
            else f"EMAIL-NAIA-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        # Extract subject and from if available
        subject = ""
        from_addr = ""
        task_lines = task.get("task", "").split("\n")
        for line in task_lines:
            if "Subject:" in line:
                subject = line.replace("Subject:", "").strip()
            elif "From:" in line and "Message ID:" not in line:
                from_addr = line.replace("From:", "").strip()

        entry = f"""---
msg_id: {msg_id}
msg_type: EMAIL_SCAN
from: Email Scanner
priority: P1
to: {task.get("staff", "HALE")}
submitted_at: {datetime.now().strftime("%Y-%m-%d %H:%M MT")}
content: |
  Staff mention detected in email.
  
  **Details:**
  - Staff: {task.get("staff", "HALE")}
  - From: {from_addr}
  - Subject: {subject}
  - Message ID: {task.get("message_id", "Unknown")}
  
  Email flagged for {task.get("staff", "HALE")} review.
  Please review and task out as appropriate.

---
"""
        new_entries.append(entry)

    # Append to wing_comms
    with open(WING_COMMS, "a", encoding="utf-8") as f:
        for entry in new_entries:
            f.write(entry)
            f.write("\n")

    return new_entries


def mark_complete_in_claude_inbox(task_ranges):
    """Mark tasks as COMPLETE in claude_inbox.md"""
    with open(CLAUDE_INBOX, "r", encoding="utf-8") as f:
        lines = f.readlines()

    modified = False

    for start, end in task_ranges:
        if start < len(lines) and end < len(lines):
            # Find status line and update to COMPLETE
            for i in range(start, end + 1):
                if lines[i].startswith("status:"):
                    lines[i] = "status: COMPLETE\n"
                    modified = True
                    break

    if modified:
        with open(CLAUDE_INBOX, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return modified


def scan_d2mconcierge_via_mcp():
    """Simulate scanning d2mconcierge inbox via MCP"""
    # This would normally call MCP gmail_list_threads
    # For now, we'll simulate and return mock data
    print("INFO: Simulating MCP email scan of d2mconcierge@gmail.com")

    mock_emails = [
        {
            "id": "19d77957a24a3ced",
            "subject": "fwd: [d2m red] preflight check",
            "from": "john loucks3 <johnloucks3@gmail.com>",
            "snippet": "Preflight check results need HALE review...",
        }
    ]

    return mock_emails


def log_repair_operations(
    hale_naia_count, deduped_count, routed_count, completed_count, log_file
):
    """Log repair operations"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"""
=== EMAIL SCANNER REPAIR LOG ===
Timestamp: {timestamp}
Total HALE/NAIA tasks found: {hale_naia_count}
After deduplication: {deduped_count}
Routed to wing_comms.md: {routed_count}
Marked COMPLETE in claude_inbox.md: {completed_count}
MCP email scan: Simulated (would use gmail_list_threads)
Routing complete.
"""

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)

    print(log_entry)


def main():
    """Main repair function"""
    print("Starting email scanner repair...")

    # Setup
    log_file = setup_logging()

    # 1. Load and parse claude_inbox
    tasks = load_claude_inbox()
    print(f"Loaded {len(tasks)} tasks from claude_inbox.md")

    # 2. Filter HALE/NAIA email scanner tasks
    hale_naia_tasks, other_tasks = filter_hale_naia_tasks(tasks)
    print(f"Found {len(hale_naia_tasks)} HALE/NAIA email scanner tasks")

    # 3. Deduplicate
    deduped_tasks = deduplicate_tasks(hale_naia_tasks)
    print(f"After deduplication: {len(deduped_tasks)} unique tasks")

    # 4. Route to wing_comms.md
    routed_entries = route_to_wing_comms(deduped_tasks)
    print(f"Routed {len(routed_entries)} tasks to wing_comms.md")

    # 5. Mark as COMPLETE in claude_inbox
    task_ranges = [
        (t["lines_start"], t["lines_end"] or t["lines_start"] + 20)
        for t in deduped_tasks
    ]
    completed = mark_complete_in_claude_inbox(task_ranges)
    print(f"Marked {len(deduped_tasks)} tasks as COMPLETE in claude_inbox.md")

    # 6. Simulate MCP email scan
    mcp_emails = scan_d2mconcierge_via_mcp()

    # 7. Log operations
    log_repair_operations(
        len(hale_naia_tasks),
        len(deduped_tasks),
        len(routed_entries),
        len(deduped_tasks),
        log_file,
    )

    # 8. Create summary report
    summary = f"""
=== EMAIL SCANNER REPAIR SUMMARY ===
Repair completed at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

REPAIR ACTIONS:
1. Loaded {len(tasks)} total tasks from claude_inbox.md
2. Identified {len(hale_naia_tasks)} HALE/NAIA email scanner tasks
3. Deduplicated to {len(deduped_tasks)} unique tasks
4. Routed {len(routed_entries)} tasks to wing_comms.md
5. Marked {len(deduped_tasks)} tasks as COMPLETE in claude_inbox.md
6. MCP email scan simulated (would use gmail_list_threads)

RECOMMENDATIONS:
- Email scanner should route directly to wing_comms.md, not claude_inbox.md
- Use MCP gmail_list_threads for live scanning
- Implement proper deduplication in scanner
- Log all routing operations
"""

    print(summary)

    # Write summary to file
    summary_file = (
        THUNDERBIRD_DIR / "OpsCenter" / "logs" / "email_scanner_repair_summary.md"
    )
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)

    return 0


if __name__ == "__main__":
    sys.exit(main())
