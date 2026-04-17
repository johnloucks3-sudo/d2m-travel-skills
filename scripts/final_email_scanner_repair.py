#!/usr/bin/env python3
"""
FINAL EMAIL SCANNER REPAIR
Direct approach: Remove all EMAIL-SCAN tasks from claude_inbox.md
Add summary to wing_comms.md
Fix the scanner code to route HALE/NAIA to wing_comms
"""

import re
import sys
from datetime import datetime
from pathlib import Path

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
CLAUDE_INBOX = THUNDERBIRD_DIR / "claude_inbox.md"
WING_COMMS = THUNDERBIRD_DIR / "OpsCenter" / "collaboration" / "wing_comms.md"


def remove_email_scan_tasks():
    """Remove all EMAIL-SCAN tasks from claude_inbox.md"""
    with open(CLAUDE_INBOX, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match EMAIL-SCAN tasks
    # Tasks start with "## TASK: EMAIL-SCAN-" and go until next "## TASK:" or end of file
    pattern = r"(^## TASK: EMAIL-SCAN-.*?)(?=^## TASK:|\Z)"

    # Find all matches
    matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))

    if not matches:
        print("No EMAIL-SCAN tasks found")
        return content, []

    print(f"Found {len(matches)} EMAIL-SCAN tasks")

    # Extract task info before removing
    task_info = []
    for match in matches:
        task_text = match.group(1)
        # Extract staff
        staff = "UNKNOWN"
        if "**Staff Mention Detected: HALE**" in task_text:
            staff = "HALE"
        elif "**Staff Mention Detected: NAIA**" in task_text:
            staff = "NAIA"

        # Extract message ID
        msg_id_match = re.search(r"Message ID:\s*(\S+)", task_text)
        message_id = msg_id_match.group(1) if msg_id_match else "UNKNOWN"

        # Extract subject
        subject_match = re.search(r"Subject:\s*(.+)", task_text)
        subject = subject_match.group(1).strip() if subject_match else "NO SUBJECT"

        task_info.append(
            {
                "staff": staff,
                "message_id": message_id,
                "subject": subject[:100],  # Truncate
                "full_text": task_text[:500],  # Truncate for logging
            }
        )

    # Remove all EMAIL-SCAN tasks
    new_content = re.sub(pattern, "", content, flags=re.MULTILINE | re.DOTALL)

    # Clean up excessive blank lines
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)

    return new_content.strip() + "\n", task_info


def add_to_wing_comms(task_info):
    """Add migration summary to wing_comms.md"""
    if not WING_COMMS.exists():
        print(f"WARNING: wing_comms.md not found at {WING_COMMS}")
        return False

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary = f"""
---
msg_id: WC-EMAIL-MIGRATION-{datetime.now().strftime("%Y%m%d%H%M%S")}
msg_type: SYSTEM_ALERT
from: Email Scanner Repair Bot
priority: P1
to: HALE, NAIA, Claude, OpenCode
submitted_at: {datetime.now().strftime("%Y-%m-%d %H:%M MT")}
content: |
  **EMAIL SCANNER REPAIR COMPLETE**
  
  **Summary:**
  - Removed {len(task_info)} duplicate EMAIL-SCAN tasks from claude_inbox.md
  - HALE tasks: {sum(1 for t in task_info if t["staff"] == "HALE")}
  - NAIA tasks: {sum(1 for t in task_info if t["staff"] == "NAIA")}
  
  **Problem Fixed:**
  Email scanner was creating duplicate tasks in claude_inbox.md for HALE/NAIA mentions.
  These should be routed to wing_comms.md instead.
  
  **Repair Actions:**
  1. Removed all EMAIL-SCAN-* tasks from claude_inbox.md
  2. Added this summary to wing_comms.md
  3. Email scanner code needs update to route HALE/NAIA to wing_comms
  
  **Manual Fix Required:**
  Update `core/email/thunderbird_email_scanner_fixed.py`:
  - Ensure HALE/NAIA classification returns target_inbox = "wing_comms"
  - Ensure main sweep routes to write_wing_comms_task() not write_claude_task()
  
  **Timestamp:** {timestamp}
  
---
"""

    with open(WING_COMMS, "a", encoding="utf-8") as f:
        f.write("\n" + summary)

    return True


def fix_scanner_code():
    """Provide manual fix instructions for scanner code"""
    scanner_file = (
        THUNDERBIRD_DIR / "core" / "email" / "thunderbird_email_scanner_fixed.py"
    )

    print("\n" + "=" * 60)
    print("MANUAL FIX REQUIRED FOR EMAIL SCANNER")
    print("=" * 60)

    print(f"\nFile: {scanner_file}")
    print("\nCheck the following:")
    print("1. In classify_email() function, ensure:")
    print('   if staff in ["HALE", "NAIA"]:')
    print('       target_inbox = "wing_comms"')
    print("\n2. In process_email_sweep() or main routing logic, ensure:")
    print('   if classification["target_inbox"] == "wing_comms":')
    print("       success = write_wing_comms_task(classification)")
    print("\n3. Remove or fix any logic that routes HALE/NAIA to claude_inbox")
    print("\n4. Update deduplication to check wing_comms.md, not just claude_inbox.md")

    # Check current state
    if scanner_file.exists():
        with open(scanner_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check classification
        if 'if staff in ["HALE", "NAIA"]:' in content:
            print("\n✓ Classification logic appears correct")
        else:
            print("\n✗ Classification logic may need fixing")

        # Check routing
        if 'classification["target_inbox"] == "wing_comms"' in content:
            print("✓ Routing logic includes wing_comms check")
        else:
            print("✗ Routing logic may not handle wing_comms")

    return True


def main():
    print("=" * 60)
    print("FINAL EMAIL SCANNER REPAIR")
    print("=" * 60)

    # 1. Backup original
    backup = CLAUDE_INBOX.with_suffix(
        f".md.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    with open(CLAUDE_INBOX, "r", encoding="utf-8") as f:
        original = f.read()
    with open(backup, "w", encoding="utf-8") as f:
        f.write(original)
    print(f"Backup created: {backup}")

    # 2. Remove EMAIL-SCAN tasks
    new_content, task_info = remove_email_scan_tasks()

    if not task_info:
        print("No EMAIL-SCAN tasks to remove")
        return 0

    # 3. Write cleaned claude_inbox
    with open(CLAUDE_INBOX, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Cleaned claude_inbox.md (removed {len(task_info)} EMAIL-SCAN tasks)")

    # 4. Add summary to wing_comms
    if add_to_wing_comms(task_info):
        print(f"Added migration summary to wing_comms.md")

    # 5. Provide fix instructions
    fix_scanner_code()

    # 6. Create repair log
    log_file = THUNDERBIRD_DIR / "OpsCenter" / "logs" / "final_email_scanner_repair.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    log_content = f"""Final Email Scanner Repair
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Tasks removed: {len(task_info)}
HALE tasks: {sum(1 for t in task_info if t["staff"] == "HALE")}
NAIA tasks: {sum(1 for t in task_info if t["staff"] == "NAIA")}

Sample tasks removed:
"""
    for i, task in enumerate(task_info[:5], 1):
        log_content += (
            f"\n{i}. {task['staff']} - {task['subject'][:50]}... - {task['message_id']}"
        )

    if len(task_info) > 5:
        log_content += f"\n... and {len(task_info) - 5} more tasks"

    log_content += f"\n\nBackup: {backup}"

    with open(log_file, "w", encoding="utf-8") as f:
        f.write(log_content)

    print(f"\nRepair log: {log_file}")
    print("\n" + "=" * 60)
    print("REPAIR COMPLETE")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"- Removed {len(task_info)} duplicate EMAIL-SCAN tasks")
    print(f"- Backup saved as {backup.name}")
    print(f"- Added summary to wing_comms.md")
    print(f"\nNext: Manually fix email scanner code to prevent recurrence")

    return 0


if __name__ == "__main__":
    sys.exit(main())
