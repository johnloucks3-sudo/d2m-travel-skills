#!/usr/bin/env python3
"""
Simple Email Scanner Fix
Add deduplication for wing_comms and safety checks.
Apply directly to the file.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

THUNDERBIRD_DIR = Path("/home/john/Thunderbird")
SCANNER_FILE = THUNDERBIRD_DIR / "core" / "email" / "thunderbird_email_scanner_fixed.py"
BACKUP_FILE = SCANNER_FILE.with_suffix(
    f".py.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
)


def read_file():
    with open(SCANNER_FILE, "r", encoding="utf-8") as f:
        return f.read()


def write_file(content):
    with open(SCANNER_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def fix_dedup():
    """Fix deduplication to include wing_comms"""
    content = read_file()

    # First, find the existing check_duplicate_task function
    # and add a new check for wing_comms

    # Look for the check_duplicate_task function
    pattern = r"(def check_duplicate_task\(sender: str, subject: str, staff: str\) -> bool:.*?)(?=\n\ndef|\n\nclass|\Z)"

    match = re.search(pattern, content, re.DOTALL)
    if not match:
        print("Could not find check_duplicate_task function")
        return False

    duplicate_func = match.group(0)

    # Add new function after it
    new_function = '''
def check_wing_comms_duplicate(sender: str, subject: str, staff: str, message_id: str) -> bool:
    """Check if a similar task already exists in wing_comms.md"""
    try:
        if not WING_COMMS.exists():
            return False

        with open(WING_COMMS, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for duplicate by message ID
        if message_id and f"Message ID: {message_id}" in content:
            logger.info(f"Duplicate wing_comms task detected: {message_id}")
            return True

        # Check by subject and staff
        search_patterns = [
            f"Subject: {subject[:100]}",
            f"to: {staff}",
        ]

        for pattern in search_patterns:
            if pattern in content:
                logger.info(f"Duplicate wing_comms task: {pattern[:50]}...")
                return True

        return False
    except Exception as e:
        logger.error(f"wing_comms deduplication failed: {e}")
        return False
'''

    # Replace the duplicate function with itself + new function
    new_content = content.replace(duplicate_func, duplicate_func + new_function)

    # Now update write_wing_comms_task to use deduplication
    # Find the write_wing_comms_task function
    write_pattern = r"(def write_wing_comms_task\(classification: Dict\[str, Any\]\) -> tuple\[bool, str\]:.*?)(?=\n\ndef|\n\nclass|\Z)"

    write_match = re.search(write_pattern, new_content, re.DOTALL)
    if not write_match:
        print("Could not find write_wing_comms_task function")
        return False

    write_func = write_match.group(0)

    # Add deduplication check at beginning of function
    dedup_code = '''    # Deduplication check for wing_comms
    if check_wing_comms_duplicate(
        classification["sender"], 
        classification["subject"], 
        classification["staff"],
        classification.get("message_id", "")
    ):
        logger.info(
            f"Duplicate wing_comms task skipped: {classification['staff']} - {classification['subject'][:50]}..."
        )
        return False, ""'''

    # Find the try block and insert dedup code before it
    lines = write_func.split("\n")
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if line.strip() == "try:":
            # Insert dedup code above this line
            new_lines.insert(-1, dedup_code)
            break

    new_write_func = "\n".join(new_lines)

    # Replace in content
    new_content = new_content.replace(write_func, new_write_func)

    # Backup
    import shutil

    shutil.copy2(SCANNER_FILE, BACKUP_FILE)

    # Write
    write_file(new_content)

    print("Fixed deduplication for wing_comms")
    return True


def add_safety_warning():
    """Add safety warning for HALE/NAIA routing"""
    content = read_file()

    # Find the routing logic
    routing_section = """        if classification["action"] == "task":
            if classification["target_inbox"] == "wing_comms":
                success, task_id = write_wing_comms_task(classification)
                action = "wing_comms"
            elif classification["target_inbox"] == "claude":
                success, task_id = write_claude_task(classification)
                action = "claude"
            elif classification["target_inbox"] == "opencode":
                success, task_id = write_opencode_task(classification)
                action = "opencode"

            # Log routing decision
            log_routing_decision(classification, success, action)"""

    # Add safety check before "elif classification["target_inbox"] == "claude":"
    safety_code = '''            elif classification["target_inbox"] == "claude":
                # SAFETY CHECK: HALE/NAIA should never go to claude
                if classification["staff"] in ["HALE", "NAIA"]:
                    logger.warning(f"SAFETY VIOLATION: HALE/NAIA ({classification['staff']}) routed to claude! Overriding to wing_comms.")
                    success, task_id = write_wing_comms_task(classification)
                    action = "wing_comms (safety override)"
                    # Log the violation
                    with open(LOG_FILE, "a") as log_f:
                        log_f.write(f"{datetime.utcnow().isoformat()} | SAFETY_VIOLATION | {classification['staff']} | {classification['subject'][:50]}... | HALE/NAIA routed to claude\\\\n")
                else:
                    success, task_id = write_claude_task(classification)
                    action = "claude"'''

    # Replace the original elif block with safety code
    original_elif = '''            elif classification["target_inbox"] == "claude":
                success, task_id = write_claude_task(classification)
                action = "claude"'''

    if original_elif in content:
        content = content.replace(original_elif, safety_code)
        write_file(content)
        print("Added safety warning for HALE/NAIA routing")
        return True
    else:
        print("Could not find routing logic to add safety warning")
        return False


def main():
    print("=" * 60)
    print("EMAIL SCANNER FIX")
    print("=" * 60)

    if not SCANNER_FILE.exists():
        print(f"File not found: {SCANNER_FILE}")
        return 1

    print(f"File: {SCANNER_FILE}")

    # Backup first
    import shutil

    shutil.copy2(SCANNER_FILE, BACKUP_FILE)
    print(f"Backup: {BACKUP_FILE}")

    # Apply fixes
    print("\n1. Fixing deduplication...")
    fix_dedup()

    print("\n2. Adding safety warning...")
    add_safety_warning()

    print("\n" + "=" * 60)
    print("FIX APPLIED")
    print("=" * 60)
    print("""
Changes made:
1. Added check_wing_comms_duplicate() function
2. Added deduplication to write_wing_comms_task()
3. Added safety warning for HALE/NAIA routing to claude

This should prevent:
. Duplicate tasks in wing_comms.md
. HALE/NAIA tasks being routed to claude_inbox.md

Test by running:
  python scripts/test_email_scanner_routing.py

Monitor logs for duplicate detection.
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
